# Original VT20X: hardware validation

On 2026-10-23, the owner ran the experimental probe from macOS Terminal with Tone Room closed. **All 73 requests succeeded.** This establishes a working independent USB-MIDI read path to the owner's original VT20X and validates the recovered factory preset bank on this device.

The [probes and offline tests](../scripts/README.md) are included in this repository; full captures and personal amp backups remain local. [hardware-read-validation.json](../reference/hardware-read-validation.json) contains the first session's scoped result, packet counts, timings and artifact hashes. A later [temporary gain test](#temporary-gain-change) also succeeded. Source hashes in those historical reports identify the original scratch versions, before repository paths, client labels and explicit ctypes packing were updated for Eleven.

## Device and transport

| Item | Observation |
| --- | --- |
| Hardware | Original VT20X, before Classic Blue, identified by owner |
| Host | macOS 27.0.1, Apple silicon arm64 |
| USB | `Valvetronix X`, vendor `VOX Amplification Ltd.`, VID/PID `0944:0132` |
| CoreMIDI | One online input and output, both named `Valvetronix X CTRL`, same device/entity |
| Identity reply | `F0 7E 00 06 02 42 34 01 00 00 01 00 01 00 F7` |
| Identity version fields | Major 1, minor 1 |
| Connection | Local USB, normal user Terminal; no wireless bridge |

The family identity does not uniquely identify the wattage or hardware generation. USB `bcdDevice = 0x0100` is a USB release descriptor, not the MIDI identity version. Endpoint reference handles and unique IDs were retained locally but are not portable discovery constants.

The restricted agent process could not create a CoreMIDI client (`-10833`, `kMIDINoConnection`). Execution from the user's Terminal succeeded. That earlier failure was therefore not evidence of a faulty USB connection or incompatible amp protocol.

## Verified operations

| Request | Count | Matching response | Result |
| --- | --- | --- | --- |
| Universal identity inquiry | 1 | 15-byte VTX identity | Matched manufacturer/family and read version fields |
| `12` mode | 2 | 10-byte `42` | Same mode and selection before/after |
| `10` current sound | 2 | 79-byte `40` | Same complete 62-byte record before/after |
| `1C 00 slot` user bank | 8 | 81-byte `4C 00 slot` | All slots 0–7 read and backed up |
| `1C 01 slot` factory bank | 60 | 81-byte `4C 01 slot` | All slots 0–59 match app records exactly |

The factory comparison includes every byte of all 60 records, including unused fields and reserved bytes: 3720 bytes total, SHA-256 `8e2455cbff2e6cbc146ce2dd71201e87ca8ec9081d5e9285254f8ef2d3c21521`. This verifies the app-table-to-factory-slot mapping for this device/version, not every VTX firmware.

The 528-byte user backup contains the observed 32-byte `.vtxprog` header and eight complete read-back records. Its SHA-256 is `0706b89330814212deb97a75e856b3f389a3928011908afe9823cfbaac23bcb3`. The backup and user settings remain local. It has not been restored to the amp or imported into Tone Room.

## Read-session packet fragmentation and timing

143 received CoreMIDI packets assembled into 73 complete SysEx messages. The two current dumps each arrived as **48 + 31 bytes**; all 68 stored dumps each arrived as **48 + 33 bytes**. Identity and mode replies each fit one packet. The transport must assemble a SysEx stream and must not treat one callback or packet as one message. These packet lengths describe this capture, not a required split point.

Measured from immediately before the send call to receipt of the final matching packet, response latency was 1.274–3.946 ms, median 1.967 ms, mean 2.018 ms. The probe deliberately paused 75 ms before each request and used a five-second timeout with no retries. The full session took about 5.93 seconds. These measurements include host scheduling and do not establish maximum throughput, safe slider rates or write timing.

## Temporary gain change

Capture `gain-20261023T174546.723684Z` records a separate user-authorized current-buffer test on the same device/host. It completed 13 request/reply exchanges in about 1.10 seconds:

1. Read identity, mode and the complete current program; save the original 62-byte record locally and recheck that state is stable.
2. Send `F0 42 30 00 01 34 41 04 00 63 00 F7`, changing raw gain 100 → 99 (display 10.0 → 9.9).
3. Receive `F0 42 30 00 01 34 23 F7` after 2.697 ms. Read the current buffer: only raw offset 19 differs, with the intended value 99. Mode/selection remain unchanged.
4. Recheck state and send `F0 42 30 00 01 34 41 04 00 64 00 F7`, restoring raw gain 100.
5. Receive the same ACK form after 2.207 ms. Read current/mode again: all 62 original bytes and mode/selection are restored exactly.

18 received MIDI packets assembled into 13 replies. The original current-buffer SHA-256 is `42e7d78bae909670ad77760f384f4e5085c31eb9ff2d5513370da45b8f0a3aef`. The raw original sound remains local. [hardware-gain-validation.json](../reference/hardware-gain-validation.json) retains the selected command bytes, result and capture hashes.

Independent JavaScript decoding of the actual frames confirmed the parameter ID/sub-ID, values, ACKs, single-byte change and full restoration; separate raw-packet reassembly matched the recorded replies. Every other transmission was identity or a mode/current read. No program selection, full-buffer upload or persistent-write command was sent. Stored user slots were not reread in this experiment, so it does not independently establish their post-test contents.

This validates one temporary parameter edit at values 99/100 in user mode. It does not establish all parameter ranges, effect/model side effects, dirty-state UI behavior, persistent saves or safe continuous-slider rates.

## Evidence checks and remaining scope

The local verification independently reassembled raw packets, matched the resulting frames to all recorded exchanges, checked that every transmitted frame was an allowed inquiry/read, verified each factory record and reconstructed the backup from the eight responses. Decoding reported no failures. Both mode and current-buffer bytes were unchanged between the first and last reads; sequential reads are not an atomic snapshot.

Still unverified: custom-data reads (`31`), parameters other than the tested gain values, program selection (`4E`), current-buffer uploads (`40`), persistent writes (`11`, `4C`, `65`), hardware-control notifications, reconnect behavior, sustained traffic, Linux/Raspberry Pi, wireless transport, and Classic Blue compatibility. The next experiments are in the [verification plan](verification.md).
