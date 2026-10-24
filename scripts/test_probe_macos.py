"""Offline checks: never create a MIDI client or send to an endpoint."""
import ctypes as C
import sys
import unittest
from probe_macos import CoreMIDI, Framer, HEADER, INQUIRY, matches, packet_bytes, permitted_read, select_pair


class ProbeTests(unittest.TestCase):
    def test_transmit_allowlist_excludes_writes_and_invalid_slots(self):
        allowed = [INQUIRY, HEADER + b'\x10\xf7', HEADER + b'\x12\xf7']
        allowed += [HEADER + bytes([0x1c, bank, slot, 0xf7])
                    for bank, count in ((0, 8), (1, 60)) for slot in range(count)]
        self.assertTrue(all(map(permitted_read, allowed)))
        for command in range(128):
            if command not in (0x10, 0x12):
                self.assertFalse(permitted_read(HEADER + bytes([command, 0xf7])))
        for message in ('41 04 00 32 00 f7', '4e 00 00 f7', '11 00 00 f7',
                        '1c 00 08 f7', '1c 01 3c f7', '1c 02 00 f7', '31 00 00 f7'):
            self.assertFalse(permitted_read(HEADER + bytes.fromhex(message)))
        self.assertFalse(permitted_read(HEADER + b'\x40' + bytes(71) + b'\xf7'))
        self.assertFalse(permitted_read(HEADER + b'\x4c\x00\x00' + bytes(71) + b'\xf7'))
        self.assertFalse(permitted_read(HEADER + b'\x65\x00\x00' + bytes(71) + b'\xf7'))

    def test_stream_fragmentation_and_realtime(self):
        frame = HEADER + b'\x40' + bytes(71) + b'\xf7'
        for cut in range(len(frame) + 1):
            parser = Framer()
            self.assertEqual(parser.feed(frame[:cut]) + parser.feed(b'\xf8\xfe') + parser.feed(frame[cut:]), [frame])
        parser = Framer()
        self.assertEqual(parser.feed(b'\x90\x01\x7f' + frame + frame), [frame, frame])
        self.assertEqual(parser.feed(b'\xf0\x01\x90\x02\xf7'), [])
        self.assertEqual(parser.feed(b'\xf0\x01' + frame), [frame])

    def test_reply_matching_and_wrong_family(self):
        reply = bytes.fromhex('f0 7e 00 06 02 42 34 01 00 00 02 00 01 00 f7')
        self.assertTrue(matches(INQUIRY, reply))
        self.assertFalse(matches(INQUIRY, reply[:6] + b'\x35' + reply[7:]))
        request = HEADER + b'\x1c\x00\x03\xf7'
        self.assertTrue(matches(request, HEADER + b'\x4c\x00\x03' + bytes(71) + b'\xf7'))
        self.assertFalse(matches(request, HEADER + b'\x4c\x01\x03' + bytes(71) + b'\xf7'))
        self.assertFalse(matches(request, HEADER + b'\x4c\x00\x02' + bytes(71) + b'\xf7'))

    def test_pair_selection_requires_one_physical_device(self):
        source = {'device_ref': 12, 'name': 'Valvetronix X', 'device_name': 'Valvetronix X', 'offline': 0}
        self.assertEqual(select_pair([source], [source]), (source, source))
        for destinations in ([], [dict(source, device_ref=13)], [source, source], [dict(source, offline=1)]):
            with self.assertRaises(RuntimeError):
                select_pair([source], destinations)

    @unittest.skipUnless(sys.platform == 'darwin', 'Apple CoreMIDI packet builders require macOS')
    def test_native_packet_layout_against_core_midi_builders(self):
        # These packet functions work without a MIDI client/server and do no I/O.
        midi = CoreMIDI()
        storage = C.create_string_buffer(4096)
        pointer = midi.m.MIDIPacketListInit(storage)
        expected = [(111, bytes([1, 2, 3])), (222, bytes(range(256)) + bytes(19)), (333, b'\xf7')]
        for timestamp, data in expected:
            payload = C.create_string_buffer(data)
            pointer = midi.m.MIDIPacketListAdd(storage, len(storage), pointer, timestamp, len(data), payload)
            self.assertTrue(pointer)
        self.assertEqual(list(packet_bytes(C.addressof(storage))), expected)


if __name__ == '__main__':
    unittest.main()
