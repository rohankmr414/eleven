# Preset inventory

Tone Room 1.4.0 includes a **60-program VTX preset bank inside its executable**, in addition to the installer's eight-program `USERBANK.vtxprog` file. Both contain complete 62-byte program records. Neither is a capture of the user's amplifier.

## The three sources of sounds

| Source | Count | Status / implementation use |
| --- | --- | --- |
| Embedded VTX preset bank | 60 | Recovered app data; usable as offline reference sounds after validation |
| Bundled user defaults | 8 | Installer defaults; separate from the app preset bank and the user's saved settings |
| Connected amp | 60 factory addresses + 8 user slots | All read successfully; factory slots match the app table on the tested original VT20X; user backup retained locally |

The embedded data provides names and full parameter values, so an implementation can browse and inspect these sounds without an attached amp. A [2026-10-23 hardware capture](hardware-validation.md) verified every app-table index against factory bank `01` on the owner's original VT20X (identity version fields major 1, minor 1): **60 of 60 complete 62-byte records match exactly**. This does not establish the same contents on every firmware or on Classic Blue. Reading the connected amp remains authoritative.

## Recovered data

- [vtx-app-presets.json](../reference/vtx-app-presets.json): all 60 records, raw bytes, decoded model/parameter values and source offsets.
- [vtx-bundled-user-defaults.json](../reference/vtx-bundled-user-defaults.json): eight installer defaults and retained file header.

`parameters_raw` values use the ranges and scales from [vtx-midi-reference.json](../reference/vtx-midi-reference.json). `raw_hex` retains the full record, including unknown bytes and inactive-effect settings. No MIDI frames or executable code are embedded in these files.

## Embedded VTX preset catalog

Indices below are zero-based app-table positions. Names reproduce the stored 16-byte names with trailing spaces removed. Amp-model indices follow the sequence 0–19 repeated three times.

| App index | Stored name | Amp model | Gain (0–10) | Enabled effects |
| --- | --- | --- | --- | --- |
| 0 | Standard Clean 1 | `deluxe_cl_vibrato` | 3.5 | room |
| 1 | Standard Clean 2 | `deluxe_cl_normal` | 3.5 | room |
| 2 | Classic Crunch 1 | `tweed_4x10_bright` | 5.9 | spring |
| 3 | Classic Crunch 2 | `tweed_4x10_normal` | 9.4 | room |
| 4 | Special Clean | `boutique_cl` | 3.5 | spring |
| 5 | Special OD | `boutique_od` | 6.8 | room |
| 6 | VOX Chime | `vox_ac30` | 5.0 | plate |
| 7 | VOX Boost | `vox_ac30tb` | 7.2 | plate |
| 8 | UK Rock 1 | `brit_1959_treble` | 7.8 | room |
| 9 | UK Rock 2 | `brit_1959_normal` | 8.2 | room |
| 10 | UK HiGain | `brit_800` | 7.8 | room |
| 11 | UK Metal | `brit_vm` | 7.2 | room |
| 12 | Super Lead | `sl_od` | 8.5 | room |
| 13 | CA Metal | `double_rec` | 9.7 | spring |
| 14 | Ecstasy | `cali_elation` | 7.5 | room |
| 15 | EVolution 2 | `erupt_iii_ch2` | 7.8 | room |
| 16 | EVolution 3 | `erupt_iii_ch3` | 7.3 | room |
| 17 | Fuel | `boutique_metal` | 7.3 | room |
| 18 | Orangish Rock | `brit_or_mkii` | 7.8 | room |
| 19 | Blue Sky | `original_cl` | 4.6 | chorus, tape_echo, spring |
| 20 | Otherside | `deluxe_cl_vibrato` | 4.6 | compressor, room |
| 21 | Pride and Joy | `deluxe_cl_normal` | 7.2 | tube_od, spring |
| 22 | Rock This Town | `tweed_4x10_bright` | 2.7 | compressor, tape_echo, spring |
| 23 | Brown Sugar | `tweed_4x10_normal` | 5.8 | fuzz, tape_echo |
| 24 | Higher | `boutique_cl` | 4.6 | compressor, room |
| 25 | Got The Blues | `boutique_od` | 6.8 | gold_drive, tape_echo, hall |
| 26 | Day Tripper | `vox_ac30` | 4.8 | compressor, plate |
| 27 | Tie Your Mother | `vox_ac30tb` | 6.1 | gold_drive, plate |
| 28 | Black Dog | `brit_1959_treble` | 5.3 | gold_drive, tape_echo, plate |
| 29 | Walk This Way | `brit_1959_normal` | 7.6 | brit_lead, spring |
| 30 | Spoonman | `brit_800` | 8.0 | tube_od, room |
| 31 | Love of God | `brit_vm` | 8.6 | analog_delay, spring |
| 32 | Raining Blood | `sl_od` | 8.5 | gold_drive, analog_delay, spring |
| 33 | Enter Sandman | `double_rec` | 7.3 | room |
| 34 | Know Your Enemy | `cali_elation` | 8.1 | analog_delay, spring |
| 35 | AlwaysOnTheRun | `erupt_iii_ch2` | 3.8 | fuzz, tape_echo |
| 36 | Unchained | `erupt_iii_ch3` | 6.6 | flanger |
| 37 | Psychosocial | `boutique_metal` | 5.7 | gold_drive |
| 38 | American Idiot | `brit_or_mkii` | 5.6 | room |
| 39 | Get Lucky | `original_cl` | 4.5 | compressor, plate |
| 40 | Thrill Is Gone | `deluxe_cl_vibrato` | 8.6 | spring |
| 41 | Gravity | `deluxe_cl_normal` | 8.1 | rc_turbo, spring |
| 42 | BornOnTheBayou | `tweed_4x10_bright` | 4.2 | tremolo, room |
| 43 | Cocaine | `tweed_4x10_normal` | 7.5 | fuzz, spring |
| 44 | Purple Rain | `boutique_cl` | 4.4 | chorus, tape_echo, spring |
| 45 | La Grange | `boutique_od` | 2.9 | treble_boost, room |
| 46 | Pride | `vox_ac30` | 4.4 | compressor, analog_delay, plate |
| 47 | No One Knows | `vox_ac30tb` | 8.6 | compressor, room |
| 48 | Cliffs of Dover | `brit_1959_treble` | 10.0 | gold_drive, tape_echo, spring |
| 49 | Paranoid | `brit_1959_normal` | 8.9 | treble_boost, spring |
| 50 | The Trooper | `brit_800` | 7.3 | gold_drive, plate |
| 51 | Satch Boogie | `brit_vm` | 8.1 | analog_delay |
| 52 | Best of You | `sl_od` | 1.8 | rc_turbo, analog_delay |
| 53 | I Stand Alone | `double_rec` | 7.1 | room |
| 54 | Teen Spirit | `cali_elation` | 9.1 | None |
| 55 | Sweet Child | `erupt_iii_ch2` | 7.0 | rc_turbo, tape_echo, spring |
| 56 | Total Destroy | `erupt_iii_ch3` | 7.0 | analog_delay, hall |
| 57 | Walk | `boutique_metal` | 10.0 | rc_turbo |
| 58 | Alive | `brit_or_mkii` | 3.7 | brit_lead, spring |
| 59 | Have A Cigar | `original_cl` | 7.9 | compressor, phaser_black, spring |

## Bundled user defaults

| Slot | Stored name | Amp model | Gain (0–10) | Enabled effects |
| --- | --- | --- | --- | --- |
| A1 | USER A-1 | `deluxe_cl_vibrato` | 4.6 | compressor, room |
| A2 | USER A-2 | `vox_ac30` | 5.0 | plate |
| A3 | USER A-3 | `brit_800` | 7.8 | room |
| A4 | USER A-4 | `double_rec` | 7.1 | room |
| B1 | USER B-1 | `tweed_4x10_bright` | 2.7 | compressor, tape_echo, spring |
| B2 | USER B-2 | `vox_ac30tb` | 8.6 | compressor, room |
| B3 | USER B-3 | `brit_or_mkii` | 3.7 | brit_lead, spring |
| B4 | USER B-4 | `boutique_metal` | 10.0 | rc_turbo |

## How an implementation uses them

1. Load app-bank data as an explicitly labeled offline library. Keep it distinct from live factory data and user-slot backups.
2. To audition an extracted record, validate it and send it as a `40` current-buffer dump. This previews a sound without intentionally overwriting a user slot.
3. To select an existing amp factory sound, use mode `01` / program index through `4E`, then read mode/current state. This is a different action from uploading the extracted record.
4. To keep an edited sound, explicitly save it to one of the eight user slots.
5. A factory-bank export would contain 60 records. This does not establish that Tone Room accepts a 60-record `.vtxprog` container; use a documented voxlink archival format until that compatibility is tested.

## Static proof and recovery boundary

The embedded bank begins at Mach-O file offset `0x21dae0`, virtual address `0x10021dae0`, and occupies 3720 bytes (`60 × 62`). Its SHA-256 is `8e2455cbff2e6cbc146ce2dd71201e87ca8ec9081d5e9285254f8ef2d3c21521`.

Initializer `0x10000d34a` copies from this address to `0x1002d2dd0` with a `0x3e` stride until `0xe88` bytes have been copied. Its caller `0x1000c85b8` initializes a class whose vtable RTTI is `13VTXDataCenter`, sets a count to at least `0x3c` (60), and invokes the copy. This is stronger evidence than finding song-name strings alone. See [native evidence](native-evidence.md).

The following record at `0x21e968` is a separately referenced blank-name/default record. It is outside the 60-record initializer range and is not counted as a sixty-first factory preset. The package also contains defaults for other VOX families; they are not imported into the VTX catalog.

All 60 embedded records and eight installer records passed the documented common/model-dependent range checks and offline MIDI packing round-trips. The recovered bank still needs comparison with a connected amp; no target executable or hardware was run.
