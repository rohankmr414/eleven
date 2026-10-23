# Tone Room preset files

Status: **observed statically** in Tone Room 1.4.0 build 2910 and its bundled `USERBANK.vtxprog`. This is a bounded file-format reconstruction, not an official VOX disk-format specification. See [sources](sources.md) for artifact hashes.

## Container

A `.vtxprog` file contains a 32-byte header followed by consecutive unpacked 62-byte program records. It has no MIDI `F0`/`F7` envelope and does not use MIDI seven-bit packing.

| File offset | Length | Observed contents |
| --- | --- | --- |
| 0 | 12 | `56 54 58 50 52 4F 47 31 30 30 30 20`, ASCII `VTXPROG1000 ` including trailing space |
| 12 | 20 | Zero padding in the sample and both inspected writers |
| 32 | 62 × count | Raw program records |

No separate count field, wrapper checksum or trailer was observed. For these forms, `count = (file_size - 32) / 62`. The meaning of `1000` beyond the observed signature/version string is unknown.

The bundled bank contains eight records and is 528 bytes. Their starting file offsets are `32, 94, 156, 218, 280, 342, 404, 466`. Its names run from `USER A-1` to `USER B-4` and are space-padded to 16 bytes. These are shipped defaults, not a backup of the user's amplifier.

## Two writer forms

| Writer function | VTX record count | Total bytes | Evidence |
| --- | --- | --- | --- |
| `0x1000f0d46` | 8 | 528 (`0x210`) | Header selection at `0x1000f0e65`, stride `0x3e`, count comparison to eight |
| `0x1000f2060` | 11 | 714 (`0x2ca`) | Header selection at `0x1000f21c5`, count comparison to `0xb` at `0x1000f2256` |

Both use the same header and raw record size. The exact UI call path of the eleven-record VTX writer is unresolved. It does not imply eleven hardware user slots. These observations also do not establish that arbitrary record counts are accepted by Tone Room.

## Proposed parser/export behavior

1. Check the signature, minimum header length and that the body length is divisible by 62.
2. Retain the original header and all record bytes. Report unknown header values or record counts instead of silently rewriting them.
3. Decode known fields using the [program layout](program-layout.md); retain invalid/unrecognized field values for inspection rather than clamping on load.
4. Distinguish structural parsing from permission to send a record to the amp. Validate a record's model-dependent fields before applying it.
5. Support the observed eight- and eleven-record forms for inspection. Initially export the confirmed eight-record bank shape for backups; broader library-export compatibility needs testing.
6. For an amp restore, require an explicit mapping to the eight user slots. Opening a file alone has no device side effect.

Fields not changed by the caller must survive a load/save cycle byte-for-byte. This includes disabled-effect settings, the reserved bytes at raw offsets 47–54 and the unspecified byte at offset 61. The wire packing is a separate transformation performed only when constructing a MIDI dump.

## Tone Room interaction semantics

The bundled VTX manual establishes these intended behaviors:

- Selecting a program in a local file list sends it to the temporary current buffer for audition.
- Selecting a hardware user-program button selects that existing amp slot.
- Saving user programs creates a computer backup; loading user programs overwrites amp slots.
- Opening a program file adds it to the local library, separate from a hardware restore.
- Copying to a hardware user slot is a persistent overwrite. Factory preset slots are not write destinations.
- Live edits require a later explicit write to become a saved user program.
- Tone Room's limit of three open file tabs is a UI rule, not an amplifier limit.

Manual locators: connection p.2; file preview and backup/restore p.3; copying p.4; live edits p.5; write/custom settings pp.6–7; file/write details pp.8–9. See [sources](sources.md).

Other registered extensions (`.vx2prog`, `.agtprog`, `.absprog`, `.vx50gtvprog`, `.cam50prog`) belong to other products. Similar lengths do not establish compatible schemas.
