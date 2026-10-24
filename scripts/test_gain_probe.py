"""Offline gain-test scenarios. Never instantiate CoreMIDI or open hardware."""
import contextlib
import io
import json
from pathlib import Path
import queue
import subprocess
import time
import unittest

from gain_probe_macos import ACK, HEADER, INQUIRY, Session, decode_current, decode_mode, gain_frame, run_test


class FakeSession:
    def __init__(self, gain=100, fault=None):
        self.raw = bytearray(62)
        self.raw[19] = gain
        self.original = bytes(self.raw)
        self.fault = fault
        self.writes = []
        self.selection = [0, 2]

    def identity(self):
        return bytes.fromhex('f07e000602423401000001000100f7')

    def mode(self, label):
        if self.fault == 'scene_change' and label == 'mode_changed':
            self.selection = [0, 3]
        return self.selection.copy()

    def current(self, label):
        if self.fault == 'changed_read_timeout' and label == 'current_changed':
            raise TimeoutError('read timed out')
        if self.fault == 'interrupt' and label == 'current_changed':
            raise KeyboardInterrupt()
        if self.fault == 'disconnect' and self.writes:
            raise TimeoutError('disconnected')
        if self.fault == 'preflight_drift' and label == 'current_preflight':
            self.raw[20] = 1
        if self.fault == 'other_field' and label == 'current_changed':
            self.raw[20] = 1
        return bytes(self.raw)

    def gain(self, label, value):
        self.writes.append((label, value))
        if self.fault == 'rejected' and label == 'gain_change':
            return 'rejected'
        if self.fault == 'restore_rejected' and label == 'gain_restore':
            return 'rejected'
        self.raw[19] = value
        if self.fault == 'send_error_after_change' and label == 'gain_change':
            raise RuntimeError('send returned an error after changing device')
        return 'timeout' if self.fault == 'no_ack' else 'ack'


class GainTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Public preset records encoded by the independent JavaScript codec.
        # No captured user sound or installed Tone Room binary is required.
        result = subprocess.run(['node', '--input-type=module', '-e', """
            import { readFileSync } from 'node:fs';
            import { currentProgramDump } from './vtx.mjs';
            const records = ['vtx-app-presets.json', 'vtx-bundled-user-defaults.json']
              .flatMap(name => JSON.parse(readFileSync('../reference/' + name)).programs)
              .map(p => ({ raw_hex: p.raw_hex,
                frame_hex: Buffer.from(currentProgramDump(Buffer.from(p.raw_hex, 'hex'))).toString('hex') }));
            process.stdout.write(JSON.stringify(records));
        """], cwd=Path(__file__).resolve().parent, check=True, capture_output=True, text=True)
        cls.records = json.loads(result.stdout)

    def run_case(self, gain=100, fault=None):
        session, report, persisted = FakeSession(gain, fault), {}, []
        with contextlib.redirect_stdout(io.StringIO()):
            passed = run_test(session, report, lambda: persisted.append(json.loads(json.dumps(report))))
        return session, report, persisted, passed

    def test_success_and_gain_boundaries(self):
        for original in [0, 1, 50, 100]:
            session, report, persisted, passed = self.run_case(original)
            target = original - 1 if original else 1
            self.assertTrue(passed)
            self.assertEqual(session.writes, [('gain_change', target), ('gain_restore', original)])
            self.assertEqual(bytes(session.raw), session.original)
            self.assertEqual(report['changed_offsets'], [19])
            self.assertFalse(persisted[0]['mutation_attempted'])
            self.assertEqual(persisted[0]['original_raw_hex'], session.original.hex())

    def test_missing_ack_uses_readback_without_repeating_change(self):
        session, report, _, passed = self.run_case(fault='no_ack')
        self.assertTrue(passed)
        self.assertEqual(report['change_response'], 'timeout')
        self.assertEqual(report['restore_response'], 'timeout')
        self.assertEqual(len(session.writes), 2)

    def test_rejected_edit_is_not_retried_or_saved(self):
        session, report, _, passed = self.run_case(fault='rejected')
        self.assertFalse(passed)
        self.assertTrue(report['restored_verified'])
        self.assertEqual(session.writes, [('gain_change', 99)])

    def test_uncertain_send_read_timeout_and_interrupt_attempt_restore(self):
        for fault in ['send_error_after_change', 'changed_read_timeout', 'interrupt']:
            session, report, _, passed = self.run_case(fault=fault)
            self.assertFalse(passed)
            self.assertTrue(report['restored_verified'])
            self.assertEqual(session.writes[-1], ('gain_restore', 100))
            self.assertEqual(bytes(session.raw), session.original)

    def test_scene_change_divergence_and_disconnect_do_not_blindly_restore(self):
        for fault in ['scene_change', 'other_field', 'disconnect']:
            session, report, _, passed = self.run_case(fault=fault)
            self.assertFalse(passed)
            self.assertFalse(report['restored_verified'])
            self.assertEqual(session.writes, [('gain_change', 99)])
            self.assertIn('restore_error', report)

    def test_preflight_drift_aborts_before_mutation(self):
        session, report, _, passed = self.run_case(fault='preflight_drift')
        self.assertFalse(passed)
        self.assertFalse(report['mutation_attempted'])
        self.assertEqual(session.writes, [])

    def test_restore_rejection_does_not_claim_success(self):
        _, report, _, passed = self.run_case(fault='restore_rejected')
        self.assertFalse(passed)
        self.assertFalse(report['restored_verified'])

    def test_gain_constructor_only_exposes_valid_gain(self):
        self.assertEqual(gain_frame(99).hex(), 'f042300001344104006300f7')
        for value in [-1, 101, 1.5, True, '20']:
            with self.assertRaises(ValueError):
                gain_frame(value)

    def test_transport_session_with_fragmented_replies_and_acks(self):
        frames = {
            'identity': bytes.fromhex('f07e000602423401000001000100f7'),
            'mode': bytes.fromhex('f04230000134420002f7'),
            'current_before': bytes.fromhex(self.records[0]['frame_hex']),
        }

        class SimulatedMIDI:
            def __init__(self):
                self.incoming = queue.Queue()
                self.current_frame = bytearray(frames['current_before'])
                self.sent_gain = []

            def reply(self, frame):
                for start in range(0, len(frame), 48):
                    self.incoming.put((time.monotonic(), 0, bytes(frame[start:start + 48])))

            def send_read(self, destination, request):
                if request == INQUIRY:
                    self.reply(frames['identity'])
                elif request == HEADER + b'\x12\xf7':
                    self.reply(frames['mode'])
                elif request == HEADER + b'\x10\xf7':
                    self.reply(self.current_frame)
                else:
                    raise AssertionError('Unexpected read')

            def send_gain(self, destination, value):
                self.sent_gain.append(gain_frame(value))
                self.current_frame[29] = value  # Raw offset 19 in packed current frame.
                self.reply(ACK)

        midi, report, log = SimulatedMIDI(), {'exchanges': []}, io.StringIO()
        original = decode_current(bytes(midi.current_frame))[19]
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(run_test(Session(midi, 1, report, log), report, lambda: None))
        self.assertEqual(midi.sent_gain, [gain_frame(original - 1 if original else 1), gain_frame(original)])
        self.assertTrue(report['both_gain_acknowledgements_received'])
        self.assertEqual(bytes(midi.current_frame), frames['current_before'])
        traffic = [json.loads(line) for line in log.getvalue().splitlines()]
        self.assertEqual(sum(x['kind'] == 'rx_frame' for x in traffic), len(report['exchanges']))

    def test_decoder_matches_all_68_reference_records_encoded_by_js(self):
        self.assertEqual(len(self.records), 68)
        for record in self.records:
            self.assertEqual(decode_current(bytes.fromhex(record['frame_hex'])).hex(), record['raw_hex'])
        self.assertEqual(decode_mode(bytes.fromhex('f04230000134420002f7')), [0, 2])
        with self.assertRaises(ValueError):
            decode_mode(bytes.fromhex('f04230000134420008f7'))
        malformed = bytearray(HEADER + b'\x40' + bytes(71) + b'\xf7')
        malformed[-8] = 0x40
        with self.assertRaises(ValueError):
            decode_current(bytes(malformed))


if __name__ == '__main__':
    unittest.main()
