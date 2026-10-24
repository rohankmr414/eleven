import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import * as vtx from './vtx.mjs';

const hex = input => Buffer.from(input).toString('hex');
const unhex = value => Uint8Array.from(Buffer.from(value.replaceAll(' ', ''), 'hex'));
const rawFixture = () => {
  const raw = new Uint8Array(62);
  raw.fill(32, 0, 16);
  return raw;
};

test('inquiry and read packets match published layouts, not captured traffic', () => {
  assert.equal(hex(vtx.inquiry()), 'f07e7f0601f7');
  assert.equal(hex(vtx.inquiry(0)), 'f07e000601f7');
  assert.equal(hex(vtx.getMode()), 'f0423000013412f7');
  assert.equal(hex(vtx.getCurrentProgram()), 'f0423000013410f7');
  assert.equal(hex(vtx.getProgram(vtx.BANK.USER, 7)), 'f042300001341c0007f7');
  assert.equal(hex(vtx.getProgram(vtx.BANK.PRESET, 59)), 'f042300001341c013bf7');
  assert.equal(hex(vtx.getCustomData(3)), 'f04230000134310003f7');
});

test('mutation packets use distinct operation codes', () => {
  assert.equal(hex(vtx.setMode(vtx.MODE.PRESET, 12)), 'f042300001344e010cf7');
  assert.equal(hex(vtx.setParameter(4, 0, 75)), 'f042300001344104004b00f7');
  assert.equal(hex(vtx.writeCurrentProgram(7)), 'f04230000134110007f7');
});

test('7-bit conversion uses source high bits in ascending prefix positions', () => {
  const raw = unhex('00 7f 80 ff 55 aa 01');
  const packed = unhex('2c 00 7f 00 7f 55 2a 01');
  assert.deepEqual(vtx.pack7bit(raw), packed);
  assert.deepEqual(vtx.unpack7bit(packed, 7), raw);
  assert.equal(hex(vtx.pack7bit(unhex('80 ff'))), '03007f');
});

test('packing all byte values covers full groups and every partial-group size', () => {
  for (let length = 0; length <= 256; length++) {
    const raw = Uint8Array.from({ length }, (_, i) => i);
    const packed = vtx.pack7bit(raw);
    assert.equal(packed.length, length + Math.ceil(length / 7));
    assert.ok(packed.every(value => value <= 127));
    assert.deepEqual(vtx.unpack7bit(packed, length), raw);
  }
  const last = vtx.pack7bit(new Uint8Array(62).fill(255));
  assert.equal(last.length, 71);
  assert.deepEqual(last.slice(-7), unhex('3f 7f 7f 7f 7f 7f 7f'));
});

test('packing rejects invalid bytes, lengths, and noncanonical padding', () => {
  for (const raw of [[-1], [256], [1.5], [NaN]]) assert.throws(() => vtx.pack7bit(raw));
  assert.throws(() => vtx.unpack7bit([0], 1));
  assert.throws(() => vtx.unpack7bit([0, 128], 1));
  assert.throws(() => vtx.unpack7bit([2, 0], 1));
  assert.throws(() => vtx.unpack7bit([], -1));
  assert.throws(() => vtx.currentProgramDump(new Uint8Array(61)));
  assert.throws(() => vtx.currentProgramDump(new Uint8Array(63)));
});

test('raw 16-bit values and wire 14-bit values use different encodings', () => {
  let raw = vtx.withParameter(rawFixture(), 3, 2, 5); // Tape delay model.
  raw = vtx.withParameter(raw, 6, 0, 1200);
  assert.equal(hex(raw.slice(40, 42)), 'b004');
  assert.equal(vtx.getParameter(raw, 6, 0), 1200);
  const packet = vtx.setParameter(6, 0, 1200, vtx.programContext(raw));
  assert.equal(hex(packet), 'f042300001344106003009f7');
  assert.equal(vtx.parseMessage(packet, vtx.programContext(raw)).value, 1200);
});

test('parameter validation observes effect-specific ranges and spans', () => {
  assert.throws(() => vtx.setParameter(5, 0, 100)); // Model context is required.
  assert.throws(() => vtx.setParameter(5, 4, 0, { pedal1Model: 0 })); // Compressor has only four fields.
  assert.throws(() => vtx.setParameter(6, 4, 0, { pedal2Model: 1 })); // Phaser has only four fields.
  assert.throws(() => vtx.setParameter(6, 0, 1649, { pedal2Model: 4 }));
  assert.throws(() => vtx.setParameter(6, 0, 1201, { pedal2Model: 5 }));
  assert.throws(() => vtx.setParameter(8, 5, 0)); // Undocumented last reverb byte is not an API.
  assert.throws(() => vtx.setParameter(7, 0, 0));
  assert.throws(() => vtx.setParameter(2, 3, 0));
  assert.throws(() => vtx.setParameter(3, 0, 20));
  assert.throws(() => vtx.setParameter(0, 0, 31));
  assert.throws(() => vtx.setParameter(4, 0, 100.5));
  assert.throws(() => vtx.setParameter(4, 11, 2));
});

test('editing a field preserves unknown bytes and original input', () => {
  const raw = rawFixture();
  raw[17] = 0xa9; // Includes reserved bits.
  raw.fill(0xcb, 47, 55);
  raw[61] = 0xde;
  const original = raw.slice();
  const edited = vtx.withParameter(raw, 2, 2, 1);
  assert.deepEqual(raw, original);
  assert.equal(edited[17], 0xad);
  assert.deepEqual(edited.slice(47, 55), raw.slice(47, 55));
  assert.equal(edited[61], 0xde);
  assert.equal(vtx.getParameter(edited, 2, 2), 1);
  assert.equal(vtx.getParameter(edited, 2, 1), 0);
  assert.throws(() => vtx.withParameter(raw, 8, 5, 1));
});

test('identity parsing validates the documented family and reports version', () => {
  const id = vtx.parseMessage(unhex('f0 7e 00 06 02 42 34 01 00 00 02 00 01 00 f7'));
  assert.deepEqual(id, { type: 'identity', manufacturer: 66, family: [52, 1], member: [0, 0], minor: 2, major: 1 });
  assert.throws(() => vtx.parseMessage(unhex('f0 7e 00 06 02 41 34 01 00 00 02 00 01 00 f7')));
});

test('response parsing distinguishes acknowledgements, errors, and mode notifications', () => {
  assert.equal(vtx.parseMessage(unhex('f0423000013423f7')).type, 'ack');
  assert.equal(vtx.parseMessage(unhex('f0423000013424f7')).type, 'nak');
  assert.equal(vtx.parseMessage(unhex('f0423000013426f7')).type, 'formatError');
  assert.deepEqual(vtx.parseMessage(unhex('f04230000134210003f7')), { type: 'writeAck', function: 33, program: 3 });
  assert.deepEqual(vtx.parseMessage(unhex('f04230000134220003f7')), { type: 'writeNak', function: 34, program: 3 });
  assert.deepEqual(vtx.parseMessage(unhex('f0423000013442013bf7')), { type: 'modeState', function: 66, mode: 1, program: 59 });
  assert.equal(vtx.parseMessage(unhex('f042300001344e0001f7')).type, 'modeChange');
});

test('frame parser rejects wrong family, length, reserved byte, status bytes, and functions', () => {
  for (const packet of [
    'f0423000013523f7', 'f042300001342300f7', 'f04230000134210103f7',
    'f04230000134410400ff00f7', 'f0423000013477f7', 'f0423000013423',
    'f04230000134420300f7', 'f042300001341c0008f7',
    'f042300001344108054000f7'
  ]) assert.throws(() => vtx.parseMessage(unhex(packet)), packet);
});

test('selectors reject nonexistent slots and invalid IDs', () => {
  assert.throws(() => vtx.inquiry(1));
  assert.throws(() => vtx.getProgram(2, 0));
  assert.throws(() => vtx.getProgram(0, 8));
  assert.throws(() => vtx.getProgram(1, 60));
  assert.throws(() => vtx.getCustomData(4));
  assert.throws(() => vtx.writeCurrentProgram(-1));
  assert.throws(() => vtx.writeCurrentProgram(8));
  assert.throws(() => vtx.setMode(2, 64));
});

test('all request builders can be parsed without transport', () => {
  for (const packet of [vtx.inquiry(), vtx.getMode(), vtx.getCurrentProgram(),
    vtx.getProgram(0, 0), vtx.getCustomData(0), vtx.writeCurrentProgram(0), vtx.setMode(2, 0)]) {
    assert.ok(vtx.parseMessage(packet).type);
  }
});

test('eight bundled defaults reconstruct the source bank and round-trip through dumps', () => {
  const source = JSON.parse(readFileSync(new URL('../reference/vtx-bundled-user-defaults.json', import.meta.url)));
  const bank = Buffer.concat([Buffer.from(source.provenance.header_hex, 'hex'),
    ...source.programs.map(p => Buffer.from(p.raw_hex, 'hex'))]);
  assert.equal(createHash('sha256').update(bank).digest('hex'), source.provenance.source_sha256);
  assert.equal(bank.length, 32 + 8 * 62);
  assert.equal(bank.subarray(0, 12).toString('ascii'), 'VTXPROG1000 ');
  for (let slot = 0; slot < 8; slot++) {
    const raw = Uint8Array.from(bank.subarray(32 + slot * 62, 32 + (slot + 1) * 62));
    const current = vtx.currentProgramDump(raw);
    assert.equal(current.length, 79);
    assert.deepEqual(vtx.parseMessage(current).raw, raw);
    const stored = vtx.programDump(slot, raw);
    assert.equal(stored.length, 81);
    assert.deepEqual(vtx.parseMessage(stored), { type: 'programDump', function: 76, bank: 0, program: slot, raw });
    const custom = vtx.customDataDump(slot % 4, raw);
    assert.deepEqual(vtx.parseMessage(custom).raw, raw);
    assert.deepEqual(vtx.unpack7bit(vtx.pack7bit(raw), 62), raw);
  }
});

test('all 68 recovered preset records retain their hashes and round-trip through MIDI', () => {
  let count = 0;
  for (const filename of ['vtx-app-presets.json', 'vtx-bundled-user-defaults.json']) {
    const bank = JSON.parse(readFileSync(new URL(`../reference/${filename}`, import.meta.url)));
    for (const preset of bank.programs) {
      const raw = Uint8Array.from(Buffer.from(preset.raw_hex, 'hex'));
      assert.equal(raw.length, 62);
      assert.equal(createHash('sha256').update(raw).digest('hex'), preset.sha256);
      assert.deepEqual(vtx.parseMessage(vtx.currentProgramDump(raw)).raw, raw);
      assert.deepEqual(vtx.parseMessage(vtx.programDump(count % 8, raw)).raw, raw);
      count++;
    }
  }
  assert.equal(count, 68);
});

test('recovered factory records retain the documented extracted block hash', () => {
  const bank = JSON.parse(readFileSync(new URL('../reference/vtx-app-presets.json', import.meta.url)));
  const recovered = Buffer.concat(bank.programs.map(p => Buffer.from(p.raw_hex, 'hex')));
  assert.equal(bank.programs.length, bank.provenance.record_count);
  assert.equal(recovered.length, bank.provenance.byte_length);
  assert.equal(createHash('sha256').update(recovered).digest('hex'), bank.provenance.block_sha256);
});
