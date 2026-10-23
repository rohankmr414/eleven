# voxlink

Implementation reference for an independent VOX Valvetronix X controller, initially targeting the **original VT20X (before Classic Blue)**.

The amp exposes a **USB-MIDI System Exclusive (SysEx)** control protocol. It performs the audio processing; voxlink will manage sounds, parameters and presets. A future interface or MCP server can use the same device service.

## Current scope

This repository contains documentation and machine-readable protocol tables only. No application, MIDI transport, MCP server or device-control implementation is included.

The reference combines VOX's published MIDI specification with static analysis of Tone Room 1.4.0 and its bundled preset file. **No physical amplifier has been tested.** Packet formats have documentary and selected native-code corroboration; response timing, USB compatibility and successful writes remain unverified.

The hardware target is the owner's original VT20X. The protocol baseline is VOX's 2015 VTX specification; Classic Blue compatibility is not established. The original model already provides 20 amp models and 60 programs through Tone Room, plus eight writable user slots. See [hardware scope and sources](docs/sources.md#hardware-scope).

## Implementation reading order

| Reference | What it answers |
| --- | --- |
| [API map](docs/api-map.md) | Which operations to expose, their arguments, results and persistence effects |
| [Wire protocol](docs/wire-protocol.md) | Discovery, frame layouts, commands, replies, events and seven-bit packing |
| [Program and parameter layout](docs/program-layout.md) | Raw record offsets, model IDs, ranges, units and custom defaults |
| [Preset files](docs/preset-files.md) | `.vtxprog` headers and the observed eight- and eleven-record variants |
| [Preset inventory](docs/presets.md) | The 60 sounds embedded in Tone Room and eight bundled user defaults |
| [Session behavior](docs/session-behavior.md) | Synchronization, request matching, edits, saves, reconnects and failures |
| [Implementation boundaries](docs/implementation.md) | Transport, codec, session and API responsibilities |
| [Verification plan](docs/verification.md) | Offline checks, first hardware experiments and unresolved questions |
| [Sources](docs/sources.md) and [native evidence](docs/native-evidence.md) | Provenance, artifact identities, addresses and confidence limits |

Machine-readable references:

- [vtx-midi-reference.json](reference/vtx-midi-reference.json): numeric command/parameter map; numbers are decimal and offsets are zero-based.
- [test-vectors.json](reference/test-vectors.json): specification-derived examples for a future codec. These are synthetic examples, not captured amp traffic.
- [vtx-app-presets.json](reference/vtx-app-presets.json): 60 complete VTX records recovered from the app's embedded bank, with decoded parameters and provenance.
- [vtx-bundled-user-defaults.json](reference/vtx-bundled-user-defaults.json): eight installer default records; these are not the user's saved amp settings.

## State that must remain separate

1. **Current program:** the temporary sound being played and edited.
2. **Stored user programs:** eight persistent slots, A1–A4 and B1–B4.
3. **Local library:** programs and backups stored outside the amplifier.

Auditioning a library program, selecting an existing hardware slot and saving to that slot are different operations. Factory presets are readable; documented program writes target user memory.

## Evidence labels

- **Specified:** defined in the official VOX MIDI implementation or owner's manual.
- **Observed statically:** corroborated in the supplied Tone Room binary or bundled files.
- **Proposed:** behavior recommended for the new application; not a firmware guarantee.
- **Unverified:** requires device or additional file/runtime evidence.

The next implementation milestone is read-only discovery, current-state retrieval and backup of all eight user slots. See the [verification plan](docs/verification.md).
