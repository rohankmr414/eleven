// Decode recorded reads only. This program cannot open MIDI or send messages.
import assert from 'node:assert/strict';
import { readFileSync, writeFileSync } from 'node:fs';
import { resolve, join } from 'node:path';
import { createHash } from 'node:crypto';
import { parseMessage, getParameter, pack7bit, unpack7bit } from './vtx.mjs';

if (process.argv.length !== 3 || ['-h', '--help'].includes(process.argv[2])) {
  console.log('Usage: node scripts/analyze_capture.mjs <capture-directory>');
  process.exit(['-h', '--help'].includes(process.argv[2]) ? 0 : 1);
}
const folder = resolve(process.argv[2]);
const report = JSON.parse(readFileSync(join(folder, 'report.json'), 'utf8'));
const presets = JSON.parse(readFileSync(new URL('../reference/vtx-app-presets.json', import.meta.url), 'utf8'));
const hex = input => Buffer.from(input).toString('hex');
const sha = input => createHash('sha256').update(input).digest('hex');
const decoded = new Map();
const failures = [];
const programs = [];
for (const item of report.exchanges) {
  try {
    const frame = Buffer.from(item.rx_hex, 'hex');
    const message = parseMessage(frame);
    if (message.raw) {
      assert.deepEqual(unpack7bit(pack7bit(message.raw), 62), message.raw);
      const raw = Buffer.from(message.raw);
      programs.push({ label: item.label, name: raw.subarray(0, 16).toString('ascii').trimEnd(),
        amp_model: getParameter(raw, 3, 0), gain_raw: getParameter(raw, 4, 0),
        raw_hex: hex(raw), sha256: sha(raw) });
    }
    decoded.set(item.label, message);
  } catch (error) { failures.push({ label: item.label, error: error.message }); }
}
const users = Array.from({ length: 8 }, (_, i) => decoded.get(`user_${i}`));
let backup = null;
if (users.every((p, i) => p?.type === 'programDump' && p.bank === 0 && p.program === i)) {
  const header = Buffer.alloc(32);
  header.write('VTXPROG1000 ', 'ascii');
  const bytes = Buffer.concat([header, ...users.map(p => Buffer.from(p.raw))]);
  backup = { file: 'user-bank.vtxprog', bytes: bytes.length, sha256: sha(bytes) };
  writeFileSync(join(folder, backup.file), bytes, { flag: 'wx' });
}
const factory = presets.programs.flatMap(p => {
  const actual = decoded.get(`factory_${p.index}`);
  if (!actual) return [];
  assert.equal(actual.type, 'programDump');
  assert.equal(actual.bank, 1);
  assert.equal(actual.program, p.index);
  return [{ index: p.index, app_name: p.name,
    device_name: Buffer.from(actual.raw).subarray(0, 16).toString('ascii').trimEnd(),
    identical: hex(actual.raw) === p.raw_hex.toLowerCase() }];
});
const before = decoded.get('current_before'), after = decoded.get('current_after');
const modeBefore = decoded.get('mode'), modeAfter = decoded.get('mode_after');
const summary = {
  capture_status: report.status, identity: decoded.get('identity') ?? null,
  mode: modeBefore ?? null, decoded_messages: decoded.size, failures,
  current_unchanged_between_reads: before?.raw && after?.raw ? hex(before.raw) === hex(after.raw) : null,
  mode_unchanged_between_reads: modeBefore && modeAfter ? modeBefore.mode === modeAfter.mode && modeBefore.program === modeAfter.program : null,
  user_backup: backup,
  factory_read: factory.length, factory_identical_to_app: factory.filter(p => p.identical).length,
  factory_comparison: factory, programs,
  limitations: ['Reads do not prove writes, Linux/Pi support, or wireless operation.',
    'Sequential reads are not an atomic snapshot; physical edits can change state during capture.'],
};
writeFileSync(join(folder, 'decoded.json'), JSON.stringify(summary, null, 2) + '\n');
console.log(JSON.stringify({ ...summary, programs: undefined, factory_comparison: undefined }, null, 2));
if (failures.length) process.exitCode = 1;
