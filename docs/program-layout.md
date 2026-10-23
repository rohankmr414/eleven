# Program and parameter layout

Source: [VOX VTX MIDI Implementation v1.0](https://voxamps.com/wp-content/uploads/2019/07/VTX_Midi_Implementation.pdf), PDF pages 8–17. The [JSON reference](../reference/vtx-midi-reference.json) carries the same numeric fields with source-page locators. No hardware has been tested.

Offsets, model indices and ranges in this document are decimal; parameter IDs/sub-IDs are hexadecimal. All offsets refer to the **unpacked 62-byte record**, never to offsets in a MIDI frame.

## Raw program layout

| Offset | Bytes | Meaning |
| --- | --- | --- |
| 0–15 | 16 | Printable ASCII name (32–126); retain all 16 bytes |
| 16 | 1 | Noise reduction |
| 17 | 1 | Effect flags; preserve unknown bits |
| 18 | 1 | Amp model |
| 19–25 | 7 | Gain, treble, middle, bass, volume, presence/tone, resonance |
| 26–30 | 5 | Bright cap, low cut, mid boost, bias, power class |
| 31 | 1 | PEDAL1 model |
| 32–38 | 7 | PEDAL1 parameters; first field is two bytes |
| 39 | 1 | PEDAL2 model |
| 40–46 | 7 | PEDAL2 parameters; first field is two bytes |
| 47–54 | 8 | Reserved |
| 55 | 1 | Reverb model |
| 56–60 | 5 | Reverb mix, time, pre-delay, low damping, high damping |
| 61 | 1 | Unspecified reverb allocation byte; preserve |

A record must remain lossless: retain reserved bytes, inactive-effect values, unused fields of the selected model and the unspecified final byte. A typed edit changes only the intended field or flag.

## Name and effect enable parameters

Name characters use ID `00`, sub-ID `00`–`0F`, with an ASCII value from 32 to 126. The extracted default bank uses space-padded names; choose and document a padding policy for newly created programs.

| Section | Flag bit position | Raw byte-17 mask | Parameter ID / sub-ID | Value |
| --- | --- | --- | --- | --- |
| PEDAL1 | 1 | `0x02` | `02 / 01` | 0=off, 1=on |
| PEDAL2 | 2 | `0x04` | `02 / 02` | 0=off, 1=on |
| Reverb | 4 | `0x10` | `02 / 04` | 0=off, 1=on |

For example, flags `0x12` enable PEDAL1 and reverb. Toggle only the relevant bit; do not rebuild the entire flag byte from known flags.

## Common parameters

Display scaling is `display = raw / divisor` where a divisor is present. These divisors follow the published range endpoints; exact UI taper and step behavior remain unverified. Two-byte raw fields use little-endian base-256; `41` values always use two base-128 digits.

| Field | ID / sub | Offset | Width | Raw range | Display / enum | PDF pages |
| --- | --- | --- | --- | --- | --- | --- |
| `noise_reduction` | `01 / 00` | 16 | 1 | 0–100 | raw / 10 | 8 |
| `amp_model` | `03 / 00` | 18 | 1 | 0–19 | Model index or raw value | 8, 10 |
| `gain` | `04 / 00` | 19 | 1 | 0–100 | raw / 10 | 8 |
| `treble` | `04 / 01` | 20 | 1 | 0–100 | raw / 10 | 8 |
| `middle` | `04 / 02` | 21 | 1 | 0–100 | raw / 10 | 8 |
| `bass` | `04 / 03` | 22 | 1 | 0–100 | raw / 10 | 8 |
| `volume` | `04 / 04` | 23 | 1 | 0–100 | raw / 10 | 8 |
| `presence_or_tone` | `04 / 05` | 24 | 1 | 0–100 | raw / 10 | 8 |
| `resonance` | `04 / 06` | 25 | 1 | 0–100 | raw / 10 | 8 |
| `bright_cap` | `04 / 07` | 26 | 1 | 0–1 | Boolean switch | 8, 9 |
| `low_cut` | `04 / 08` | 27 | 1 | 0–1 | Boolean switch | 8, 9 |
| `mid_boost` | `04 / 09` | 28 | 1 | 0–1 | Boolean switch | 8, 9 |
| `bias` | `04 / 0A` | 29 | 1 | 0–2 | 0=off, 1=cold, 2=hot | 9 |
| `power_class` | `04 / 0B` | 30 | 1 | 0–1 | 0=A, 1=AB | 9 |
| `pedal1_model` | `03 / 01` | 31 | 1 | 0–9 | Model index or raw value | 9 |
| `pedal2_model` | `03 / 02` | 39 | 1 | 0–6 | Model index or raw value | 9 |
| `reverb_model` | `03 / 04` | 55 | 1 | 0–3 | Model index or raw value | 9 |

## Amp models

The following keys are implementation identifiers transcribed from the reference, not API exports from Tone Room. Presence becomes tone for the models marked below; bright-cap availability is model-dependent.

| Index | Key | Presence means tone | Bright cap available |
| --- | --- | --- | --- |
| 0 | `deluxe_cl_vibrato` | No | Yes |
| 1 | `deluxe_cl_normal` | No | No |
| 2 | `tweed_4x10_bright` | No | Yes |
| 3 | `tweed_4x10_normal` | No | No |
| 4 | `boutique_cl` | No | Yes |
| 5 | `boutique_od` | No | Yes |
| 6 | `vox_ac30` | Yes | Yes |
| 7 | `vox_ac30tb` | Yes | Yes |
| 8 | `brit_1959_treble` | No | Yes |
| 9 | `brit_1959_normal` | No | No |
| 10 | `brit_800` | No | Yes |
| 11 | `brit_vm` | No | Yes |
| 12 | `sl_od` | No | Yes |
| 13 | `double_rec` | No | Yes |
| 14 | `cali_elation` | No | Yes |
| 15 | `erupt_iii_ch2` | No | No |
| 16 | `erupt_iii_ch3` | No | Yes |
| 17 | `boutique_metal` | No | No |
| 18 | `brit_or_mkii` | No | Yes |
| 19 | `original_cl` | No | Yes |

## Effect model indices

### PEDAL1

| Index | Model |
| --- | --- |
| 0 | `compressor` |
| 1 | `chorus` |
| 2 | `tube_od` |
| 3 | `gold_drive` |
| 4 | `treble_boost` |
| 5 | `rc_turbo` |
| 6 | `orange_dist` |
| 7 | `fat_dist` |
| 8 | `brit_lead` |
| 9 | `fuzz` |

### PEDAL2

| Index | Model |
| --- | --- |
| 0 | `flanger` |
| 1 | `phaser_black` |
| 2 | `phaser_orange_1` |
| 3 | `phaser_orange_2` |
| 4 | `tremolo` |
| 5 | `tape_echo` |
| 6 | `analog_delay` |

### REVERB

| Index | Model |
| --- | --- |
| 0 | `room` |
| 1 | `spring` |
| 2 | `hall` |
| 3 | `plate` |

## Model-dependent effect parameters

Resolve the current section model before validating a parameter. The same ID/sub-ID can mean a different field or range under a different model. No parameter ID `07` is defined in this reference.

All rows below use the effect block's ID with the indicated sub-ID. Unlisted allocated bytes must be preserved; they are not additional writable parameters.

### compressor — ID `05`, model indices 0

| Field | Sub-ID | Offset | Width | Raw range | Display divisor | PDF pages |
| --- | --- | --- | --- | --- | --- | --- |
| `sensitivity` | `00` | 32 | 2 | 0–100 | 10 | 10 |
| `level` | `01` | 34 | 1 | 0–100 | 10 | 10 |
| `attack` | `02` | 35 | 1 | 0–100 | 10 | 10 |
| `voice` | `03` | 36 | 1 | 0–2 | 1 | 10 |

### chorus — ID `05`, model indices 1

| Field | Sub-ID | Offset | Width | Raw range | Display divisor | PDF pages |
| --- | --- | --- | --- | --- | --- | --- |
| `speed_hz` | `00` | 32 | 2 | 100–10000 | 1000 | 11 |
| `depth` | `01` | 34 | 1 | 0–100 | 10 | 11 |
| `manual` | `02` | 35 | 1 | 0–100 | 10 | 11 |
| `mix` | `03` | 36 | 1 | 0–100 | 10 | 11 |
| `low_cut` | `04` | 37 | 1 | 0–1 | 1 | 11 |
| `high_cut` | `05` | 38 | 1 | 0–1 | 1 | 11 |

### drive_distortion — ID `05`, model indices 2, 3, 4, 5, 6, 7, 8, 9

| Field | Sub-ID | Offset | Width | Raw range | Display divisor | PDF pages |
| --- | --- | --- | --- | --- | --- | --- |
| `drive` | `00` | 32 | 2 | 0–100 | 10 | 11, 12 |
| `tone` | `01` | 34 | 1 | 0–100 | 10 | 11, 12 |
| `level` | `02` | 35 | 1 | 0–100 | 10 | 11, 12 |
| `treble` | `03` | 36 | 1 | 0–100 | 10 | 11, 12 |
| `middle` | `04` | 37 | 1 | 0–100 | 10 | 11, 12 |
| `bass` | `05` | 38 | 1 | 0–100 | 10 | 11, 12 |

### flanger — ID `06`, model indices 0

| Field | Sub-ID | Offset | Width | Raw range | Display divisor | PDF pages |
| --- | --- | --- | --- | --- | --- | --- |
| `speed_hz` | `00` | 40 | 2 | 100–5000 | 1000 | 12, 13 |
| `depth` | `01` | 42 | 1 | 0–100 | 10 | 12, 13 |
| `manual` | `02` | 43 | 1 | 0–100 | 10 | 12, 13 |
| `low_cut` | `03` | 44 | 1 | 0–1 | 1 | 12, 13 |
| `high_cut` | `04` | 45 | 1 | 0–1 | 1 | 12, 13 |
| `resonance` | `05` | 46 | 1 | 0–100 | 10 | 12, 13 |

### phaser — ID `06`, model indices 1, 2, 3

| Field | Sub-ID | Offset | Width | Raw range | Display divisor | PDF pages |
| --- | --- | --- | --- | --- | --- | --- |
| `speed_hz` | `00` | 40 | 2 | 100–10000 | 1000 | 13 |
| `resonance` | `01` | 42 | 1 | 0–100 | 10 | 13 |
| `manual` | `02` | 43 | 1 | 0–100 | 10 | 13 |
| `depth` | `03` | 44 | 1 | 0–100 | 10 | 13 |

### tremolo — ID `06`, model indices 4

| Field | Sub-ID | Offset | Width | Raw range | Display divisor | PDF pages |
| --- | --- | --- | --- | --- | --- | --- |
| `speed_hz` | `00` | 40 | 2 | 1650–10000 | 1000 | 13, 14 |
| `depth` | `01` | 42 | 1 | 0–100 | 10 | 13, 14 |
| `duty` | `02` | 43 | 1 | 0–100 | 10 | 13, 14 |
| `shape` | `03` | 44 | 1 | 0–100 | 10 | 13, 14 |
| `level` | `04` | 45 | 1 | 0–100 | 10 | 13, 14 |

### delay — ID `06`, model indices 5, 6

| Field | Sub-ID | Offset | Width | Raw range | Display divisor | PDF pages |
| --- | --- | --- | --- | --- | --- | --- |
| `time_ms` | `00` | 40 | 2 | 30–1200 | 1 | 14 |
| `level` | `01` | 42 | 1 | 0–100 | 10 | 14 |
| `feedback` | `02` | 43 | 1 | 0–100 | 10 | 14 |
| `tone` | `03` | 44 | 1 | 0–100 | 10 | 14 |
| `mod_speed` | `04` | 45 | 1 | 0–100 | 10 | 14 |
| `mod_depth` | `05` | 46 | 1 | 0–100 | 10 | 14 |

### reverb — ID `08`, model indices 0, 1, 2, 3

| Field | Sub-ID | Offset | Width | Raw range | Display divisor | PDF pages |
| --- | --- | --- | --- | --- | --- | --- |
| `mix` | `00` | 56 | 1 | 0–100 | 10 | 14, 15 |
| `time` | `01` | 57 | 1 | 0–100 | 10 | 14, 15 |
| `pre_delay_ms` | `02` | 58 | 1 | 0–70 | 1 | 14, 15 |
| `low_damp` | `03` | 59 | 1 | 0–100 | 10 | 14, 15 |
| `high_damp` | `04` | 60 | 1 | 0–100 | 10 | 14, 15 |

## Custom defaults

Custom data is also 62 raw bytes / 71 packed bytes, but it is **not semantically interchangeable with a program**. It stores defaults associated with panel categories. Source: PDF pages 15–17.

- Reserved ranges: 0–15, 19–23 and 47–54, inclusive.
- Byte 17 enables custom sections: bit 0=amp and noise reduction, bit 1=PEDAL1, bit 2=PEDAL2, bit 4=reverb.
- Remaining documented fields reuse program offsets 16, 18, 24–46 and 55–61; offset 61 remains unspecified.
- Bits and bytes outside documented fields must be preserved.

Each custom index contains sections with these allowed model indices:

| Custom index | Amp | PEDAL1 | PEDAL2 | Reverb |
| --- | --- | --- | --- | --- |
| 0 | 0–19 (USER A) | 0 | 0 | 0 |
| 1 | 0–19 (USER B) | 1 | 1–3 | 1 |
| 2 | 0–19 (USER C) | 2–5 | 4 | 2 |
| 3 | Not defined | 6–9 | 5–6 | 3 |

The JSON represents the undefined amp section at custom index 3 as `null`, not an unrestricted range. Validate a custom record against its destination index before writing. Preserve disabled sections as well as enabled ones.

The bundled Tone Room manual describes recalling custom amp settings in Manual/User modes with different behavior in Preset mode. Exact state transitions and initialization on model changes need hardware verification; see [session behavior](session-behavior.md).
