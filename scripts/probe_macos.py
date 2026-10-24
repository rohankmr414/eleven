#!/usr/bin/env python3
"""Dependency-free, read-only macOS CoreMIDI probe for an original VOX VT20X.

Default: list endpoints. --read: identify, read current/mode and back up eight
user slots. --factory also reads 60 factory slots. Never selects or writes sounds.
"""
import argparse
import ctypes as C
import datetime as dt
import json
from pathlib import Path
import platform
import queue
import subprocess
import sys
import time

HEADER = bytes.fromhex('f0 42 30 00 01 34')
INQUIRY = bytes.fromhex('f0 7e 7f 06 01 f7')


def permitted_read(data):
    return (data == INQUIRY or data in (HEADER + b'\x12\xf7', HEADER + b'\x10\xf7')
            or (len(data) == 10 and data[:7] == HEADER + b'\x1c'
                and data[-1] == 0xf7 and data[7] in (0, 1)
                and data[8] < (8 if data[7] == 0 else 60)))


class Framer:
    """Assemble fragmented SysEx, ignoring interleaved MIDI realtime bytes."""
    def __init__(self):
        self.partial = bytearray()

    def feed(self, packet):
        frames = []
        for byte in packet:
            if byte >= 0xf8:
                continue
            if byte == 0xf0:
                self.partial = bytearray([byte])
            elif byte == 0xf7:
                if self.partial:
                    frames.append(bytes(self.partial) + b'\xf7')
                self.partial.clear()
            elif byte & 0x80:
                self.partial.clear()
            elif self.partial:
                self.partial.append(byte)
                if len(self.partial) > 4096:
                    self.partial.clear()
        return frames


class Packet(C.Structure):
    _layout_ = 'ms'  # Explicit ctypes packed layout; checked against native builders.
    _pack_ = 4  # MIDIServices.h: #pragma pack(push, 4)
    _fields_ = [('timestamp', C.c_uint64), ('length', C.c_uint16), ('data', C.c_ubyte * 256)]


class PacketList(C.Structure):
    _layout_ = 'ms'
    _pack_ = 4
    _fields_ = [('count', C.c_uint32), ('packet', Packet * 1)]


def packet_bytes(address):
    count = C.c_uint32.from_address(address).value
    ptr = address + PacketList.packet.offset
    for _ in range(count):
        timestamp = C.c_uint64.from_address(ptr).value
        length = C.c_uint16.from_address(ptr + Packet.length.offset).value
        yield timestamp, C.string_at(ptr + Packet.data.offset, length)
        ptr += Packet.data.offset + length
        if platform.machine() in ('arm64', 'aarch64', 'arm'):
            ptr = (ptr + 3) & ~3


READ_CALLBACK = C.CFUNCTYPE(None, C.c_void_p, C.c_void_p, C.c_void_p)


class CoreMIDI:
    def __init__(self):
        if sys.platform != 'darwin':
            raise RuntimeError('This transport requires macOS.')
        self.cf = C.CDLL('/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation')
        self.m = C.CDLL('/System/Library/Frameworks/CoreMIDI.framework/CoreMIDI')
        self.client, self.input, self.output = C.c_uint32(), C.c_uint32(), C.c_uint32()
        self.incoming = queue.Queue()
        self.callback = READ_CALLBACK(self.receive)
        p, u, i = C.c_void_p, C.c_uint32, C.c_int32
        signatures = {
            'MIDIClientCreate': ([p, p, p, C.POINTER(u)], i),
            'MIDIClientDispose': ([u], i),
            'MIDIGetNumberOfSources': ([], C.c_size_t),
            'MIDIGetNumberOfDestinations': ([], C.c_size_t),
            'MIDIGetSource': ([C.c_size_t], u), 'MIDIGetDestination': ([C.c_size_t], u),
            'MIDIObjectGetStringProperty': ([u, p, C.POINTER(p)], i),
            'MIDIObjectGetIntegerProperty': ([u, p, C.POINTER(i)], i),
            'MIDIEndpointGetEntity': ([u, C.POINTER(u)], i),
            'MIDIEntityGetDevice': ([u, C.POINTER(u)], i),
            'MIDIInputPortCreate': ([u, p, READ_CALLBACK, p, C.POINTER(u)], i),
            'MIDIOutputPortCreate': ([u, p, C.POINTER(u)], i),
            'MIDIPortConnectSource': ([u, u, p], i), 'MIDIPortDispose': ([u], i),
            'MIDIPacketListInit': ([p], p),
            'MIDIPacketListAdd': ([p, C.c_size_t, p, C.c_uint64, C.c_size_t, p], p),
            'MIDISend': ([u, u, p], i),
        }
        for name, (args, result) in signatures.items():
            fn = getattr(self.m, name)
            fn.argtypes, fn.restype = args, result
        self.cf.CFStringCreateWithCString.argtypes = [p, C.c_char_p, u]
        self.cf.CFStringCreateWithCString.restype = p
        self.cf.CFStringGetCString.argtypes = [p, p, C.c_long, u]
        self.cf.CFStringGetCString.restype = C.c_bool
        self.cf.CFRelease.argtypes = [p]

    @staticmethod
    def check(status, action):
        if status:
            detail = ' (kMIDINoConnection: cannot connect to the MIDI server)' if status == -10833 else ''
            raise RuntimeError(f'{action} failed: OSStatus {status}{detail}')

    def start(self):
        name = self.cf.CFStringCreateWithCString(None, b'eleven-read-only-probe', 0x08000100)
        try:
            self.check(self.m.MIDIClientCreate(name, None, None, C.byref(self.client)), 'MIDIClientCreate')
        finally:
            self.cf.CFRelease(name)

    def property(self, obj, key, integer=False):
        key = C.c_void_p.in_dll(self.m, key).value
        value = C.c_int32() if integer else C.c_void_p()
        fn = self.m.MIDIObjectGetIntegerProperty if integer else self.m.MIDIObjectGetStringProperty
        if fn(obj, key, C.byref(value)):
            return None
        if integer:
            return value.value
        try:
            buffer = C.create_string_buffer(4096)
            if self.cf.CFStringGetCString(value, buffer, len(buffer), 0x08000100):
                return buffer.value.decode('utf-8')
            return None
        finally:
            if value:
                self.cf.CFRelease(value)

    def endpoints(self, source):
        count = self.m.MIDIGetNumberOfSources() if source else self.m.MIDIGetNumberOfDestinations()
        get = self.m.MIDIGetSource if source else self.m.MIDIGetDestination
        result = []
        for index in range(count):
            endpoint = get(index)
            entity, device = C.c_uint32(), C.c_uint32()
            if self.m.MIDIEndpointGetEntity(endpoint, C.byref(entity)) == 0 and entity.value:
                self.m.MIDIEntityGetDevice(entity, C.byref(device))
            result.append({
                'ref': endpoint, 'entity_ref': entity.value, 'device_ref': device.value,
                'name': self.property(endpoint, 'kMIDIPropertyDisplayName'),
                'device_name': self.property(device.value, 'kMIDIPropertyName') if device.value else None,
                'unique_id': self.property(endpoint, 'kMIDIPropertyUniqueID', True),
                'offline': self.property(endpoint, 'kMIDIPropertyOffline', True),
            })
        return result

    def receive(self, packets, _context, _source):
        try:
            for host_time, data in packet_bytes(packets):
                self.incoming.put((time.monotonic(), host_time, data))
        except Exception as error:
            self.incoming.put((time.monotonic(), 0, error))

    def connect(self, source):
        name = self.cf.CFStringCreateWithCString(None, b'eleven-probe-port', 0x08000100)
        try:
            self.check(self.m.MIDIInputPortCreate(self.client, name, self.callback, None, C.byref(self.input)), 'MIDIInputPortCreate')
            self.check(self.m.MIDIOutputPortCreate(self.client, name, C.byref(self.output)), 'MIDIOutputPortCreate')
            self.check(self.m.MIDIPortConnectSource(self.input, source, None), 'MIDIPortConnectSource')
        finally:
            self.cf.CFRelease(name)

    def send_read(self, destination, data):
        if not permitted_read(data):
            raise ValueError('Probe refuses every message except its fixed identity/read allowlist')
        storage = C.create_string_buffer(1024)
        packet = self.m.MIDIPacketListInit(storage)
        payload = C.create_string_buffer(data)
        if not self.m.MIDIPacketListAdd(storage, len(storage), packet, 0, len(data), payload):
            raise RuntimeError('MIDIPacketListAdd failed')
        self.check(self.m.MIDISend(self.output, destination, storage), 'MIDISend')

    def close(self):
        for port in (self.input, self.output):
            if port.value:
                self.m.MIDIPortDispose(port)
                port.value = 0
        if self.client.value:
            self.m.MIDIClientDispose(self.client)
            self.client.value = 0


def select_pair(sources, destinations):
    pairs = [(s, d) for s in sources for d in destinations
             if s['device_ref'] and s['device_ref'] == d['device_ref']
             and s['offline'] != 1 and d['offline'] != 1
             and any('valvetronix' in (value or '').lower()
                     for value in (s['name'], s['device_name'], d['name'], d['device_name']))]
    if len(pairs) != 1:
        raise RuntimeError(f'Expected exactly one online Valvetronix input/output pair; found {len(pairs)}. No inquiry sent.')
    return pairs[0]


def matches(request, reply):
    if request == INQUIRY:
        return (len(reply) == 15 and reply[:10] == bytes.fromhex('f0 7e 00 06 02 42 34 01 00 00')
                and reply[11] == reply[13] == 0 and reply[-1] == 0xf7)
    if request[6] == 0x12:
        return len(reply) == 10 and reply[:7] == HEADER + b'\x42'
    if request[6] == 0x10:
        return len(reply) == 79 and reply[:7] == HEADER + b'\x40'
    return len(reply) == 81 and reply[:9] == HEADER + b'\x4c' + request[7:9]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--read', action='store_true', help='send identity and read requests; no settings are changed')
    parser.add_argument('--factory', action='store_true', help='also read all 60 factory programs (requires --read)')
    args = parser.parse_args()
    if args.factory and not args.read:
        parser.error('--factory requires --read')
    now = dt.datetime.now(dt.timezone.utc)
    folder = Path(__file__).resolve().parents[1] / 'captures' / now.strftime('%Y%m%dT%H%M%S.%fZ')
    folder.mkdir(parents=True, exist_ok=False)
    report = {'schema_version': 1, 'started_at': now.isoformat(), 'platform': platform.platform(),
              'read_only': True, 'factory_requested': args.factory, 'exchanges': [], 'status': 'starting'}
    client = None
    with (folder / 'traffic.jsonl').open('x') as log:
        def record(kind, **fields):
            log.write(json.dumps({'kind': kind, 'time': time.monotonic(), **fields}) + '\n')
            log.flush()
        try:
            client = CoreMIDI()
            client.start()
            report['sources'], report['destinations'] = client.endpoints(True), client.endpoints(False)
            print(json.dumps({'sources': report['sources'], 'destinations': report['destinations']}, indent=2))
            if args.read:
                source, destination = select_pair(report['sources'], report['destinations'])
                report['selected'] = {'source': source, 'destination': destination}
                client.connect(source['ref'])
                framer = Framer()

                def exchange(label, request):
                    # Conservative test pacing, not a measured firmware requirement.
                    time.sleep(0.075)
                    started = time.monotonic()
                    framer.partial.clear()
                    record('tx', label=label, hex=request.hex())
                    client.send_read(destination['ref'], request)
                    while True:
                        remaining = 5 - (time.monotonic() - started)
                        if remaining <= 0:
                            raise TimeoutError(f'{label}: no matching response within 5 s; stopping without retries')
                        try:
                            received_at, host_time, data = client.incoming.get(timeout=remaining)
                        except queue.Empty:
                            raise TimeoutError(f'{label}: no matching response within 5 s; stopping without retries')
                        if isinstance(data, Exception):
                            raise data
                        record('rx_packet', received_at=received_at, host_timestamp=host_time, hex=data.hex())
                        if received_at < started:
                            continue
                        matched = None
                        for reply in framer.feed(data):
                            record('rx_frame', hex=reply.hex())
                            if reply in (HEADER + b'\x24\xf7', HEADER + b'\x26\xf7'):
                                raise RuntimeError(f'{label}: amp rejected read: {reply.hex(" ")}')
                            if matches(request, reply) and matched is None:
                                matched = reply
                        if matched is not None:
                            item = {'label': label, 'tx_hex': request.hex(), 'rx_hex': matched.hex(),
                                    'elapsed_ms': round((received_at - started) * 1000, 3)}
                            report['exchanges'].append(item)
                            print(f'{label}: received {len(matched)} bytes in {item["elapsed_ms"]} ms', flush=True)
                            return

                exchange('identity', INQUIRY)
                exchange('mode', HEADER + b'\x12\xf7')
                exchange('current_before', HEADER + b'\x10\xf7')
                for slot in range(8):
                    exchange(f'user_{slot}', HEADER + bytes([0x1c, 0, slot, 0xf7]))
                if args.factory:
                    for slot in range(60):
                        exchange(f'factory_{slot}', HEADER + bytes([0x1c, 1, slot, 0xf7]))
                exchange('current_after', HEADER + b'\x10\xf7')
                exchange('mode_after', HEADER + b'\x12\xf7')
                report['status'] = 'reads_complete'
            else:
                report['status'] = 'enumerated_only'
        except (Exception, KeyboardInterrupt) as error:
            report['status'] = 'incomplete'
            report['error'] = str(error) or 'Interrupted'
            print(f'Probe stopped: {report["error"]}', file=sys.stderr)
        finally:
            if client:
                client.close()
            report['finished_at'] = dt.datetime.now(dt.timezone.utc).isoformat()
            (folder / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
            print(f'Capture: {folder}', flush=True)
    if report['exchanges']:
        analyzer = Path(__file__).with_name('analyze_capture.mjs')
        result = subprocess.run(['node', str(analyzer), str(folder)], check=False)
        if result.returncode:
            return result.returncode
    return 0 if report['status'] != 'incomplete' else 1


if __name__ == '__main__':
    sys.exit(main())
