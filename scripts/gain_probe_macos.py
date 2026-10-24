#!/usr/bin/env python3
"""Temporarily change VT20X gain by one raw step, verify, then restore it.

Only current-buffer parameter 04/00 can be written. No program-selection,
current-program upload, user-slot save or custom-data writes are supported.
"""
import argparse
import ctypes as C
import datetime as dt
import hashlib
import json
from pathlib import Path
import platform
import queue
import sys
import time

from probe_macos import CoreMIDI, Framer, HEADER, INQUIRY, matches, select_pair

ACK = HEADER + b'\x23\xf7'
ERRORS = (HEADER + b'\x24\xf7', HEADER + b'\x26\xf7')


def gain_frame(value):
    if type(value) is not int or not 0 <= value <= 100:
        raise ValueError('Gain must be an integer in 0..100')
    return HEADER + bytes([0x41, 4, 0, value, 0, 0xf7])


def decode_current(frame):
    if len(frame) != 79 or frame[:7] != HEADER + b'\x40' or frame[-1] != 0xf7:
        raise ValueError('Expected a 79-byte current-program response')
    packed = frame[7:-1]
    if any(byte > 127 for byte in packed):
        raise ValueError('Non-data byte in packed program')
    raw = bytearray()
    for offset in range(0, len(packed), 8):
        prefix, data = packed[offset], packed[offset + 1:offset + 8]
        if prefix >> len(data):
            raise ValueError('Nonzero unused packing bits')
        raw.extend(byte | (((prefix >> bit) & 1) << 7) for bit, byte in enumerate(data))
    if len(raw) != 62 or raw[19] > 100:
        raise ValueError('Invalid raw program length or gain')
    return bytes(raw)


def decode_mode(frame):
    if len(frame) != 10 or frame[:7] != HEADER + b'\x42' or frame[-1] != 0xf7:
        raise ValueError('Expected a mode response')
    mode, slot = frame[7:9]
    if mode not in (0, 1, 2) or slot >= (8, 60, 64)[mode]:
        raise ValueError('Invalid mode/slot')
    return [mode, slot]


class GainCoreMIDI(CoreMIDI):
    def start(self):
        name = self.cf.CFStringCreateWithCString(None, b'eleven-temporary-gain-test', 0x08000100)
        try:
            self.check(self.m.MIDIClientCreate(name, None, None, C.byref(self.client)), 'MIDIClientCreate')
        finally:
            self.cf.CFRelease(name)

    def send_gain(self, destination, value):
        # Construct internally: callers cannot pass arbitrary mutation bytes.
        data = gain_frame(value)
        storage = C.create_string_buffer(1024)
        packet = self.m.MIDIPacketListInit(storage)
        payload = C.create_string_buffer(data)
        if not self.m.MIDIPacketListAdd(storage, len(storage), packet, 0, len(data), payload):
            raise RuntimeError('MIDIPacketListAdd failed')
        self.check(self.m.MIDISend(self.output, destination, storage), 'MIDISend gain')


class Session:
    def __init__(self, midi, destination, report, log):
        self.midi, self.destination, self.report, self.log = midi, destination, report, log
        self.framer = Framer()

    def record(self, kind, **fields):
        self.log.write(json.dumps({'kind': kind, 'time': time.monotonic(), **fields}) + '\n')
        self.log.flush()

    def exchange(self, label, request, gain=None):
        time.sleep(0.075)
        self.framer.partial.clear()
        started = time.monotonic()
        attempt = {'label': label, 'tx_hex': request.hex(), 'outcome': 'send_attempted'}
        self.report['exchanges'].append(attempt)
        self.record('tx', label=label, hex=request.hex())
        if gain is None:
            self.midi.send_read(self.destination, request)
        else:
            self.midi.send_gain(self.destination, gain)
        while True:
            remaining = 3 - (time.monotonic() - started)
            try:
                if remaining <= 0:
                    raise queue.Empty()
                received_at, host_time, data = self.midi.incoming.get(timeout=remaining)
            except queue.Empty:
                attempt['outcome'] = 'timeout'
                if gain is not None:
                    print(f'{label}: no ACK; checking actual state by readback', flush=True)
                    return None
                raise TimeoutError(f'{label}: no matching read response in 3 seconds')
            if isinstance(data, Exception):
                raise data
            self.record('rx_packet', received_at=received_at, host_timestamp=host_time, hex=data.hex())
            if received_at < started:
                continue
            match = None
            for reply in self.framer.feed(data):
                self.record('rx_frame', hex=reply.hex())
                if reply in ERRORS or (reply == ACK if gain is not None else matches(request, reply)):
                    if match is None:
                        match = reply
            if match is not None:
                attempt.update(rx_hex=match.hex(), elapsed_ms=round((received_at - started) * 1000, 3),
                               outcome='rejected' if match in ERRORS else 'reply')
                print(f'{label}: {attempt["outcome"]} in {attempt["elapsed_ms"]} ms', flush=True)
                if match in ERRORS and gain is None:
                    raise RuntimeError(f'{label}: read rejected ({match.hex(" ")})')
                return match

    def identity(self):
        return self.exchange('identity', INQUIRY)

    def mode(self, label):
        return decode_mode(self.exchange(label, HEADER + b'\x12\xf7'))

    def current(self, label):
        return decode_current(self.exchange(label, HEADER + b'\x10\xf7'))

    def gain(self, label, value):
        reply = self.exchange(label, gain_frame(value), gain=value)
        return 'ack' if reply == ACK else 'timeout' if reply is None else 'rejected'


def run_test(session, report, persist):
    """State machine is injected for offline failure/recovery testing."""
    report['identity_hex'] = session.identity().hex()
    baseline_mode = session.mode('mode_before')
    before = session.current('current_before')
    original = before[19]
    target = original - 1 if original else 1
    expected = before[:19] + bytes([target]) + before[20:]
    report.update(mode_before=baseline_mode, original_gain=original, test_gain=target,
                  original_raw_hex=before.hex(), original_sha256=hashlib.sha256(before).hexdigest(),
                  changed_verified=False, restored_verified=False, mutation_attempted=False)
    # Save the complete original buffer before even attempting a mutation.
    persist()
    print(f'Gain test: {original / 10:.1f} -> {target / 10:.1f} -> {original / 10:.1f}', flush=True)
    failure = None
    try:
        # Catch a scene change during setup before sending any mutation.
        if session.mode('mode_preflight') != baseline_mode or session.current('current_preflight') != before:
            raise RuntimeError('Sound changed during setup; no gain edit sent')
        report['mutation_attempted'] = True
        persist()
        report['change_response'] = session.gain('gain_change', target)
        changed = session.current('current_changed')
        report['changed_raw_hex'] = changed.hex()
        report['changed_offsets'] = [i for i, (a, b) in enumerate(zip(before, changed)) if a != b]
        report['mode_changed'] = session.mode('mode_changed')
        report['changed_verified'] = changed == expected and report['mode_changed'] == baseline_mode
        if not report['changed_verified']:
            raise RuntimeError('Readback did not show exactly the intended gain-only change')
        if report['change_response'] == 'rejected':
            raise RuntimeError('Amp rejected the gain command; see captured readback')
    except (Exception, KeyboardInterrupt) as error:
        failure = str(error) or 'Interrupted'
    finally:
        if report['mutation_attempted']:
            try:
                # Do not blindly restore into a different sound or overwrite a user's new gain.
                mode = session.mode('mode_before_restore')
                current = session.current('current_before_restore')
                report['pre_restore_raw_hex'] = current.hex()
                if mode != baseline_mode or current not in (before, expected):
                    raise RuntimeError('Sound diverged from the original/test state; automatic restore stopped')
                if current == expected:
                    report['restore_response'] = session.gain('gain_restore', original)
                else:
                    report['restore_response'] = 'already_original'
                after = session.current('current_restored')
                report['restored_raw_hex'] = after.hex()
                report['mode_restored'] = session.mode('mode_restored')
                report['restored_verified'] = after == before and report['mode_restored'] == baseline_mode
                if not report['restored_verified']:
                    raise RuntimeError('Full original sound/mode restoration could not be verified')
                if report['restore_response'] == 'rejected':
                    raise RuntimeError('Restore command was rejected despite matching readback')
            except (Exception, KeyboardInterrupt) as error:
                report['restore_error'] = str(error) or 'Interrupted during restoration'
        if failure:
            report['test_error'] = failure
        report['both_gain_acknowledgements_received'] = (
            report.get('change_response') == 'ack' and report.get('restore_response') == 'ack')
        report['status'] = ('passed' if report['changed_verified'] and report['restored_verified']
                            and not failure and not report.get('restore_error') else 'incomplete')
        persist()
    return report['status'] == 'passed'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true', help='perform the temporary gain change and restoration')
    args = parser.parse_args()
    if not args.run:
        parser.print_help()
        return 0
    now = dt.datetime.now(dt.timezone.utc)
    folder = Path(__file__).resolve().parents[1] / 'captures' / ('gain-' + now.strftime('%Y%m%dT%H%M%S.%fZ'))
    folder.mkdir(parents=True, exist_ok=False)
    report = {'schema_version': 1, 'kind': 'temporary_gain_test', 'started_at': now.isoformat(),
              'platform': platform.platform(), 'status': 'starting', 'persistent_write_commands_supported': False,
              'exchanges': []}

    def persist():
        temporary = folder / 'report.json.tmp'
        temporary.write_text(json.dumps(report, indent=2) + '\n')
        temporary.replace(folder / 'report.json')
        if 'original_raw_hex' in report and not (folder / 'current-before.bin').exists():
            (folder / 'current-before.bin').write_bytes(bytes.fromhex(report['original_raw_hex']))

    midi = None
    with (folder / 'traffic.jsonl').open('x') as log:
        try:
            midi = GainCoreMIDI()
            midi.start()
            report['sources'], report['destinations'] = midi.endpoints(True), midi.endpoints(False)
            source, destination = select_pair(report['sources'], report['destinations'])
            report['selected'] = {'source': source, 'destination': destination}
            midi.connect(source['ref'])
            run_test(Session(midi, destination['ref'], report, log), report, persist)
        except (Exception, KeyboardInterrupt) as error:
            report.update(status='incomplete', error=str(error) or 'Interrupted')
        finally:
            if midi:
                midi.close()
            report['finished_at'] = dt.datetime.now(dt.timezone.utc).isoformat()
            persist()
    print(json.dumps({k: v for k, v in report.items() if k not in (
        'exchanges', 'sources', 'destinations', 'selected', 'original_raw_hex',
        'changed_raw_hex', 'pre_restore_raw_hex', 'restored_raw_hex')}, indent=2))
    print(f'Capture: {folder}', flush=True)
    if report.get('mutation_attempted') and not report.get('restored_verified'):
        print(f'ATTENTION: restoration is unverified. Original gain was {report["original_gain"] / 10:.1f}; '
              'the complete original buffer is saved in current-before.bin. Do not save the test sound.', file=sys.stderr)
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    sys.exit(main())
