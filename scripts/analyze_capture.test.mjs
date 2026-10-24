// Synthetic reports built from the public presets; never reads user captures.
import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync, writeFileSync, existsSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { HEADER, pack7bit, currentProgramDump, programDump } from './vtx.mjs';

const load = name => JSON.parse(readFileSync(new URL(`../reference/${name}`, import.meta.url)));
const defaults = load('vtx-bundled-user-defaults.json');
const factory = load('vtx-app-presets.json');
const hex = bytes => Buffer.from(bytes).toString('hex');
const mode = 'f04230000134420002f7';
const current = hex(currentProgramDump(Buffer.from(defaults.programs[0].raw_hex, 'hex')));

function fixture(t) {
  const folder = mkdtempSync(join(tmpdir(), 'eleven-analyzer-'));
  t.after(() => rmSync(folder, { recursive: true, force: true }));
  const report = { status: 'reads_complete', exchanges: [
    { label: 'identity', rx_hex: 'f07e000602423401000001000100f7' },
    { label: 'mode', rx_hex: mode },
    { label: 'current_before', rx_hex: current },
    ...defaults.programs.map(p => ({ label: `user_${p.index}`,
      rx_hex: hex(programDump(p.index, Buffer.from(p.raw_hex, 'hex'))) })),
    ...factory.programs.map(p => ({ label: `factory_${p.index}`,
      rx_hex: hex([...HEADER, 0x4c, 1, p.index, ...pack7bit(Buffer.from(p.raw_hex, 'hex')), 0xf7]) })),
    { label: 'current_after', rx_hex: current },
    { label: 'mode_after', rx_hex: mode },
  ] };
  const run = () => {
    writeFileSync(join(folder, 'report.json'), JSON.stringify(report));
    // An unrelated working directory catches accidental cwd-dependent paths.
    return spawnSync(process.execPath, [fileURLToPath(new URL('./analyze_capture.mjs', import.meta.url)), folder],
      { cwd: tmpdir(), encoding: 'utf8' });
  };
  return { folder, report, run };
}

test('complete synthetic capture exports an exact bank and compares all 60 presets', t => {
  const { folder, run } = fixture(t);
  const result = run();
  assert.equal(result.status, 0, result.stderr);
  const decoded = JSON.parse(readFileSync(join(folder, 'decoded.json')));
  assert.equal(decoded.decoded_messages, 73);
  assert.deepEqual(decoded.failures, []);
  assert.equal(decoded.factory_identical_to_app, 60);
  assert.equal(decoded.current_unchanged_between_reads, true);
  assert.equal(decoded.mode_unchanged_between_reads, true);
  const bank = readFileSync(join(folder, 'user-bank.vtxprog'));
  assert.equal(bank.length, 528);
  assert.equal(createHash('sha256').update(bank).digest('hex'), defaults.provenance.source_sha256);
});

test('partial capture decodes available replies without fabricating a bank', t => {
  const { folder, report, run } = fixture(t);
  report.status = 'incomplete';
  report.exchanges = report.exchanges.filter(p => p.label !== 'user_7');
  const result = run();
  assert.equal(result.status, 0, result.stderr);
  const decoded = JSON.parse(readFileSync(join(folder, 'decoded.json')));
  assert.equal(decoded.capture_status, 'incomplete');
  assert.equal(decoded.user_backup, null);
  assert.equal(existsSync(join(folder, 'user-bank.vtxprog')), false);
});

test('malformed slot reply is reported and prevents a bank export', t => {
  const { folder, report, run } = fixture(t);
  report.exchanges.find(p => p.label === 'user_7').rx_hex = 'f042300001344c0007f7';
  assert.equal(run().status, 1);
  const decoded = JSON.parse(readFileSync(join(folder, 'decoded.json')));
  assert.equal(decoded.failures.length, 1);
  assert.equal(decoded.failures[0].label, 'user_7');
  assert.equal(existsSync(join(folder, 'user-bank.vtxprog')), false);
});

test('analyzer refuses to overwrite an existing backup', t => {
  const { folder, run } = fixture(t);
  const backup = join(folder, 'user-bank.vtxprog');
  writeFileSync(backup, 'existing backup');
  assert.notEqual(run().status, 0);
  assert.equal(readFileSync(backup, 'utf8'), 'existing backup');
});
