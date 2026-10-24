# Testing Eleven

These are the experimental tools used to investigate the original VT20X, with repository-relative paths and portable offline fixtures. Run the commands below from the repository root.

Requirements: Python 3.9+ and Node.js 22+ on `PATH`. No third-party Python or npm packages are needed. Hardware probes require macOS and its CoreMIDI framework; a Linux/ALSA transport is not included.

| File | Purpose | Device access |
| --- | --- | --- |
| [vtx.mjs](vtx.mjs) | Construct/parse SysEx, pack records and access typed parameters | None; constructs bytes only |
| [probe_macos.py](probe_macos.py) | Enumerate endpoints; optionally read identity, mode, current sound and stored programs | Read-only transmit allowlist |
| [analyze_capture.mjs](analyze_capture.mjs) | Decode a saved read report, export an eight-slot backup and compare factory presets | None |
| [gain_probe_macos.py](gain_probe_macos.py) | Change gain by 0.1, verify, then restore and verify the original sound | Gain only; requires `--run` |

## Offline tests

```sh
node --test scripts/*.test.mjs
python3 -m unittest discover -s scripts -p 'test_*.py' -v
```

All 35 tests pass on the development Mac: 16 codec checks, four capture-analyzer checks, five transport checks and ten gain-probe checks. They cover framing, packing, model-specific ranges, unknown-byte preservation, all 68 public preset records, exact bank reconstruction, incomplete/malformed captures, backup overwrite protection and restoration under simulated failures.

No test opens a MIDI client or sends to an endpoint. One test loads CoreMIDI solely to check packet memory layout and is skipped on other operating systems. The gain tests use Node to encode the public preset records and independently decode them in Python. No local Tone Room installation, extracted binary or private amp capture is required.

These offline results do not establish Linux device support or prove every codec command works on hardware. The [hardware validation](../docs/hardware-validation.md) describes the narrower live evidence.

## Read-only capture on macOS

Power on the original VT20X, connect its mini-USB port with a data cable, close Tone Room and leave the amp controls untouched during capture. Run from a normal user Terminal.

List endpoints without sending messages:

```sh
python3 scripts/probe_macos.py
```

Read identity, mode/current sound and all eight user slots; add `--factory` to also read all 60 factory slots:

```sh
python3 scripts/probe_macos.py --read --factory
```

The probe requires exactly one online Valvetronix input/output pair belonging to the same CoreMIDI device, then validates the VTX identity. Its transmit method permits only identity inquiry and read commands `10`, `12` and `1C`. It cannot select a program or save amplifier settings. Requests are sequential, with a five-second timeout, no retries and a conservative 75 ms pause between requests.

Each invocation creates `captures/<UTC timestamp>/` under the repository root, independent of the shell's working directory. It saves endpoint metadata and exchanges in `report.json` and timestamped raw packets/frames in `traffic.jsonl`. After any completed exchange, the Node analyzer writes `decoded.json`. Eight valid user-slot replies produce a 528-byte `user-bank.vtxprog`; a partial bank is never fabricated. Captures and backups are ignored by Git.

A nonzero probe exit status means the run or decoding was incomplete. Inspect the saved report for what succeeded. The reads are sequential, not an atomic snapshot, so avoid physical edits during the run.

To analyze a capture that has not already produced a bank backup:

```sh
node scripts/analyze_capture.mjs /absolute/path/to/capture-directory
```

The analyzer refuses to overwrite an existing `user-bank.vtxprog`. An incomplete read report can still be decoded successfully; check `capture_status`, `failures` and `user_backup` in `decoded.json` before treating it as a complete backup.

If `MIDIClientCreate` returns `-10833` (`kMIDINoConnection`), the process cannot connect to the MIDI server. This does not prove the amp is disconnected: the restricted coding-agent session exhibited this error while the same probe worked in the user's normal Terminal.

## Temporary gain test

First complete the read-only capture. With Tone Room closed and the controls untouched:

```sh
python3 scripts/gain_probe_macos.py --run
```

Without `--run`, the script prints help and does no device I/O. With it, the probe:

1. Reads identity, mode and current sound, saves the full original buffer locally, then checks that the state is still stable.
2. Lowers gain by one raw unit (0.1 displayed), or raises zero gain to 0.1.
3. Reads back the sound and verifies that only raw byte 19 changed.
4. Restores the original gain and verifies all 62 bytes and the mode/selection.

The only supported mutation is gain parameter `04/00`. The probe cannot select programs, upload full sounds or send persistent saves. It attempts restoration after an uncertain send, a failed readback or a single Ctrl-C. If the selection or sound has diverged, or cannot be read, it stops instead of applying an old gain to another state. A lost connection or second interrupt can prevent restoration; the report explicitly records whether restoration was verified and retains the original gain/buffer for recovery. No mutation is automatically retried.

Output lives in `captures/gain-<UTC timestamp>/`: `report.json`, `traffic.jsonl` and, once read, `current-before.bin`. A successful run requires verified gain-only change and full restoration; missing ACKs are recorded separately from readback results. If restoration is unverified, inspect the report and restore the original gain before saving any sound.

The [first live gain test](../docs/hardware-validation.md#temporary-gain-change) verified raw gain 100 → 99 → 100, both ACKs and complete restoration. Other parameters and persistent writes remain unverified. Historical source hashes identify the original research scripts; the repository copies update paths, client labels, explicit ctypes packing and offline fixtures without changing the gain procedure.

## Using the codec

```js
import { getCurrentProgram, parseMessage, getParameter, setParameter } from './vtx.mjs';

const request = getCurrentProgram();
// A separate transport sends request and assembles a complete reply.
// const { raw } = parseMessage(reply);
// const gain = getParameter(raw, 4, 0); // raw integer 0..100
const change = setParameter(4, 0, 75); // constructs 7.5 gain; sends nothing
```

`parseMessage` consumes one complete SysEx frame. `Framer` in the Python transport assembles fragmented replies and ignores interleaved realtime bytes. Pedal parameter validation requires the current model context. Dump constructors preserve opaque 62-byte records, including reserved fields; they do not validate every field or initialize model defaults.

The codec can construct persistent-write commands, but those constructors never send anything and the included probes do not expose them. See the [wire protocol](../docs/wire-protocol.md), [parameter layout](../docs/program-layout.md) and [session design](../docs/session-behavior.md) before building a broader controller.
