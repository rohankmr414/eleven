# Original VT20X: read-only hardware validation

On 2026-10-23, the owner ran the experimental probe from macOS Terminal with Tone Room closed. **All 73 requests succeeded.** This establishes a working independent USB-MIDI read path to the owner's original VT20X and validates the recovered factory preset bank on this device.

The probe and full capture remain outside this documentation-only repository. [hardware-read-validation.json](../reference/hardware-read-validation.json) contains the scoped result, packet counts, timings and artifact hashes.

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

## Packet fragmentation and timing

143 received CoreMIDI packets assembled into 73 complete SysEx messages. The two current dumps each arrived as **48 + 31 bytes**; all 68 stored dumps each arrived as **48 + 33 bytes**. Identity and mode replies each fit one packet. The transport must assemble a SysEx stream and must not treat one callback or packet as one message. These packet lengths describe this capture, not a required split point.

Measured from immediately before the send call to receipt of the final matching packet, response latency was 1.274–3.946 ms, median 1.967 ms, mean 2.018 ms. The probe deliberately paused 75 ms before each request and used a five-second timeout with no retries. The full session took about 5.93 seconds. These measurements include host scheduling and do not establish maximum throughput, safe slider rates or write timing.

## Evidence checks and remaining scope

The local verification independently reassembled raw packets, matched the resulting frames to all recorded exchanges, checked that every transmitted frame was an allowed inquiry/read, verified each factory record and reconstructed the backup from the eight responses. Decoding reported no failures. Both mode and current-buffer bytes were unchanged between the first and last reads; sequential reads are not an atomic snapshot.

Still unverified: custom-data reads (`31`), parameter changes (`41`), program selection (`4E`), current-buffer uploads (`40`), persistent writes (`11`, `4C`, `65`), hardware-control notifications, reconnect behavior, sustained traffic, Linux/Raspberry Pi, wireless transport, and Classic Blue compatibility. The next experiments are in the [verification plan](verification.md).
