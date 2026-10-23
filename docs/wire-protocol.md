# VTX wire protocol

Source: [VOX VTX MIDI Implementation v1.0](https://voxamps.com/wp-content/uploads/2019/07/VTX_Midi_Implementation.pdf), PDF pages 1–7. All byte literals here are hexadecimal; slot counts and lengths are decimal. Identity and reads `10`, `12`, `1C` were [validated on the owner's original VT20X](hardware-validation.md). Other commands remain unverified on hardware.

## Transport and framing

The control transport is MIDI SysEx over USB. A USB host must open a matching MIDI input/output pair. Tone Room uses CoreMIDI on macOS; the new transport may use the relevant OS MIDI API.

The documented VTX envelope is:

```text
F0 42 30 00 01 34 function payload... F7
```

`42` is the manufacturer ID, `30` is the documented channel-zero format byte, and `00 01 34` is the VTX model/family portion. In tables below, `H` abbreviates `F0 42 30 00 01 34`. No checksum appears in the documented message layouts. Do not assume other MIDI channel values are supported.

The transport must assemble complete SysEx frames across callbacks, handle multiple frames per callback and handle interleaved MIDI real-time status bytes separately. A packet/callback boundary is not necessarily a message boundary. Feed only complete frames to the codec; keep malformed/unknown traffic available for diagnostics.

The hardware capture confirmed fragmentation: each 79-byte current dump arrived as 48 + 31 bytes and each 81-byte stored dump as 48 + 33 bytes in CoreMIDI packets. These are observed packet divisions on this host, not fixed boundaries a parser should require.

## Identity inquiry

```text
Request: F0 7E 7F 06 01 F7
Reply:   F0 7E 00 06 02 42 34 01 00 00 minor 00 major 00 F7
```

Validate manufacturer `42` and family `34 01`. The documented member bytes are `00 00`; they do not distinguish VT20X, VT40X and VT100X. Preserve the raw identity and version fields rather than inventing a model-specific identifier.

## Requests, mutations and replies

| Operation | Host sends | Expected device reply | Effect |
| --- | --- | --- | --- |
| Get mode | `H 12 F7` | `H 42 mode program F7` | Read |
| Get current program | `H 10 F7` | `H 40 packed71 F7`, or NAK | Read |
| Get stored program | `H 1C bank slot F7` | `H 4C bank slot packed71 F7`, or NAK | Read |
| Get custom data | `H 31 00 index F7` | `H 65 00 index packed71 F7`, or NAK | Read |
| Set mode/selection | `H 4E mode program F7` | ACK / NAK | Selection change |
| Set parameter | `H 41 id sub low7 high7 F7` | ACK / NAK | Current-buffer edit |
| Replace current program | `H 40 packed71 F7` | ACK / NAK | Current-buffer edit |
| Save current to user slot | `H 11 00 slot F7` | `H 21 00 slot F7` / `H 22 00 slot F7` | Persistent write |
| Replace stored user program | `H 4C 00 slot packed71 F7` | ACK / NAK | Persistent write |
| Replace custom data | `H 65 00 index packed71 F7` | ACK / NAK | Persistent write |

The zero before `index` or a write-current slot is a reserved/fixed byte. For `1C` and `4C`, the byte before slot is a bank selector. Incoming `4C` writes target user bank `00`; factory bank `01` is documented as readable.

Generic responses:

| Message | Meaning |
| --- | --- |
| `H 23 F7` | Data-load completed / success |
| `H 24 F7` | Data-load error / NAK |
| `H 26 F7` | Data-format error |
| `H 21 00 slot F7` | Program-write completed |
| `H 22 00 slot F7` | Program-write error |

Generic ACK/NAK has no transaction ID, operation code or parameter ID. Serialize operations that depend on it. Write acknowledgements include a slot, but panel writes can also emit `21`; slot matching alone is not an absolute correlation guarantee.

## Selectors

| Selector | Values |
| --- | --- |
| Mode | `00` user, `01` preset, `02` manual |
| Program bank | `00` user, `01` preset |
| User slot | `00`–`07`: A1, A2, A3, A4, B1, B2, B3, B4 |
| Factory preset | `00`–`3B` (0–59) |
| Custom index | `00`–`03` (0–3) |

The manual-mode program byte is not separately constrained in the specification. Using `00` is a candidate to test, not an established semantic rule. Do not copy Tone Room's internal enum numbers; native builders translate them into these wire values.

## Two numeric encodings

A single-parameter message uses two base-128 digits:

```text
low7  = value & 0x7F
high7 = (value >> 7) & 0x7F
value = low7 | (high7 << 7)
```

Both digits must be 0–127. Validate the parameter's own range, which is usually much narrower than the 14-bit envelope.

Inside a raw program, a two-byte numeric field is ordinary little-endian:

```text
value = raw[offset] | (raw[offset + 1] << 8)
```

For delay time 1200 ms, the raw record stores `B0 04`; the parameter message stores `30 09`. Never interchange these representations.

## Seven-bit dump packing

Each program or custom record has 62 raw eight-bit bytes. Split raw bytes into groups of at most seven. For a group `r[0..n-1]`, emit a prefix followed by `n` data bytes:

```text
prefix bit j = (r[j] >> 7) & 1
data[j]      = r[j] & 0x7F
decoded[j]   = data[j] | (((prefix >> j) & 1) << 7)
```

Bit 0 corresponds to the first raw byte. The final group has six raw bytes, so its packed representation has seven bytes. Thus `62 + ceil(62 / 7) = 71` packed bytes. Prefix bits without a corresponding raw byte are zero in the observed packing routine.

Independent example:

```text
Raw:    00 7F 80 FF 55 AA 01
Packed: 2C 00 7F 00 7F 55 2A 01
```

Frame sizes including `F0` and `F7`: current dump 79 bytes; stored/custom dump 81; parameter change 12; mode data/change 10; ACK/NAK/format error 8; program-write ACK/NAK 10.

## Concrete examples

```text
Read current sound:       F0 42 30 00 01 34 10 F7
Read user B4:             F0 42 30 00 01 34 1C 00 07 F7
Gain 5.0 (raw 50):        F0 42 30 00 01 34 41 04 00 32 00 F7
Delay 1200 ms:            F0 42 30 00 01 34 41 06 00 30 09 F7
Save current to user B4:  F0 42 30 00 01 34 11 00 07 F7
```

The delay example requires PEDAL2 model 5 or 6 (tape echo / analog delay). These are specification-derived vectors, not permission to send writes or evidence of successful communication. More vectors are in [test-vectors.json](../reference/test-vectors.json).

## Device-initiated notifications

The amp can send `41` when a physical parameter changes, `4E` when mode/program changes and `21` after a panel program write. Parse these even while waiting for another response. Refresh the current program after a selection change and refresh the affected stored slot after a panel write.

## Specification ambiguity resolved statically

The custom-data response text refers to request `1C`, while its request definition specifies `31`. Tone Room's builder at `0x10001912c` emits `31 00 index`, corroborating `31` as the custom request. See [native evidence](native-evidence.md). Live confirmation is still pending.
