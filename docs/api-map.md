# Application API map

All API names in this document are **proposed voxlink interfaces**, not recovered Tone Room exports or existing implementations. The wire operations are specified by VOX; their exact bytes are in [wire-protocol.md](wire-protocol.md).

Arguments use zero-based numeric indices. A `Program` contains the complete 62-byte raw record plus decoded fields; decoded fields alone are insufficient for a lossless backup. A returned result should distinguish requested changes, acknowledged changes and readback-verified changes.

## Device and reads

| Proposed operation | Arguments | Wire action | Result |
| --- | --- | --- | --- |
| `list_devices` | None | Enumerate OS MIDI inputs/outputs | Endpoint identifiers and names; candidates only |
| `connect` | Input/output endpoint pair | Open endpoints, send identity inquiry | Verified VTX family identity and raw version fields |
| `disconnect` | Session | Close endpoints | Disconnected state; pending operations cancelled or uncertain |
| `get_amp_state` | Session | `12`, then `10` | Mode, selection, current program, timestamp; not an atomic device snapshot |
| `read_user_slot` | Slot 0–7 | `1C 00 slot` | `4C 00 slot` with program |
| `read_factory_preset` | Preset 0–59 | `1C 01 preset` | `4C 01 preset` with program |
| `backup_user_bank` | Destination outside amp | Read user slots 0–7 sequentially | Eight raw records, slot labels and acquisition metadata |
| `read_custom_defaults` | Index 0–3 | `31 00 index` | `65 00 index` with 62-byte custom record |

The universal identity identifies the VTX family, not the particular VT20X/40X/100X variant. Port names do not establish a correct input/output pair.

## Current sound and selection

| Proposed operation | Arguments / preconditions | Wire action | Persistence |
| --- | --- | --- | --- |
| `set_parameter` | Parameter ID, sub-ID, raw integer, current model context | `41 id sub low7 high7` | Current buffer only |
| `set_effect_enabled` | Section and Boolean | `41 02 sub 00-or-01 00`; sub 1/2/4 | Current buffer only |
| `rename_current_program` | Up to 16 printable ASCII characters | Name-character parameter changes, ID `00`, sub 0–15; or a full current dump | Current buffer only |
| `preview_program` | Complete valid program | `40 packed-program` | Replaces current buffer; does not save a user slot |
| `select_user_slot` | Slot 0–7 | `4E 00 slot` | Changes selection; may discard unsaved edits |
| `select_factory_preset` | Preset 0–59 | `4E 01 preset` | Changes selection; may discard unsaved edits |
| `select_manual_mode` | Manual program-byte policy to verify | `4E 02 program` | Changes mode; exact program-byte behavior unverified |

After selecting a program, read mode and the current program. An ACK confirms command reception/processing according to the protocol, but does not supply the resulting program contents. A model change may reset associated fields; read them back before using the old model's parameters.

For names, space-padding and use of a complete current dump are application choices. A multi-character sequence is not atomic. For effect toggles, the parameter sub-ID is a bit **position**, not a packed mask.

## Persistent writes

| Proposed operation | Arguments | Wire action | Verification |
| --- | --- | --- | --- |
| `save_current_to_slot` | Explicit user slot 0–7 | `11 00 slot` | Match `21 00 slot`, read slot and compare |
| `write_user_slot` | Explicit slot and complete program | `4C 00 slot packed-program` | Generic ACK, then read slot and compare |
| `restore_user_bank` | Eight programs and destination mapping | Eight serialized user-slot writes | Verify each slot; record partial completion |
| `write_custom_defaults` | Index and valid custom record | `65 00 index packed-custom` | Generic ACK, then read custom record and compare |

Expose permanent writes separately from live edits. A timeout after transmission means **unknown outcome**, not proof of failure. Do not automatically retry or roll back a bank restore; first determine which slots changed. There is no documented multi-slot transaction or rollback command.

## Files and local-only actions

| Proposed operation | Result |
| --- | --- |
| `open_library_file` | Parse a `.vtxprog` file without communicating with the amp |
| `export_library_file` | Serialize a supported container shape; preserve unknown bytes |
| `export_user_bank` | Serialize eight read programs in A1–B4 order |
| `compare_programs` | Compare raw bytes and explain known field differences |

File opening is not auditioning, and importing a library is not restoring the amp. See [preset-files.md](preset-files.md) for count limitations.

## Events and errors

Proposed events: `connection_changed`, `identity_received`, `mode_changed`, `parameter_changed`, `current_program_updated`, `user_slot_written`, `operation_failed`, `operation_uncertain`, and `diagnostic_frame`.

Proposed error categories: invalid argument, unsupported device, port unavailable, disconnected, timeout, device NAK, format error, unexpected response and readback mismatch. Keep raw device function/bytes alongside normalized errors. Avoid reporting a successful save until the selected verification level has completed.

An MCP interface can expose these same operations. The transport and session should own parameter validation, write ordering and confirmation of outcomes; a tool caller must not have to assemble arbitrary SysEx.
