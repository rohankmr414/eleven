# Sources and provenance

Investigation date: 2026-10-23. Initial target: the owner's original VOX VT20X (before Classic Blue), within the Valvetronix X family.

## Hardware scope

The owner identified the device as the original VT20X. Our baseline is the 2015-07-31 VTX MIDI specification and supplied Tone Room 1.4.0 artifacts. The [original VT20X specifications](https://voxamps.com/en-gb/product/vt20x/) list USB mini Type-B, 11 panel/20 editor amp models, 33 panel/60 editor programs and eight user memories. The recovered app bank therefore does not depend on owning Classic Blue. Subsequent [live reads](hardware-validation.md) matched all 60 factory slots on this particular amp to the recovered records.

VOX describes [VT20X Classic Blue](https://voxamps.com/product/vt20x-classic-blue/) as using VET+ modeling and an expanded role for the 12AX7 tube stage. Its page also lists Tone Room 1.4.0, but that alone does not prove identical firmware behavior, preset contents or sound. Classic Blue protocol compatibility is unverified and outside the initial hardware target. Do not infer hardware generation solely from the VTX family identity reply.

## Published sources

| Source | Used for | Locators |
| --- | --- | --- |
| [VTX MIDI Implementation](https://voxamps.com/wp-content/uploads/2019/07/VTX_Midi_Implementation.pdf) | Numeric protocol contract | v1.0, 2015-07-31; 17 PDF pages. Commands/framing/packing pp.1–7; parameters pp.8–15; custom data pp.15–17 |
| [VT20X/VT40X owner's manual](https://voxamps.com/wp-content/uploads/support/VT20X_VT40X_OM_EFGS1_WEB.pdf) | Modes, user memories, panel/editor differences | English section pp.7–13 |
| [Tone Room product page](https://voxamps.com/product/toneroom/) | Product-family and editor context | Retrieved during the investigation; historical compatibility lists do not establish current OS support |
| [VT20X specifications](https://voxamps.com/en-gb/product/vt20x/) | Physical USB interface and amp/editor context | USB mini Type-B; eight user programs |

The JSON's `source_pages` are one-based PDF page numbers in the VTX MIDI specification. Functional numeric facts have been transcribed; treat the linked vendor document as the primary source when resolving discrepancies.

## Supplied artifacts

| Artifact | Identity |
| --- | --- |
| `ToneRoom_Installer_140.dmg` | SHA-256 `109ac595b9175bfc6215f2415ddc3cbe3cc9eb3d941a6721851f6bcc613605e5` |
| `Tone Room Installer.pkg` | SHA-256 `c26b9cba70d7cf1a1d85688cba5413bfca8c3c38d9b38d71fb4a3bd3665c6a56` |
| `Tone Room.app/Contents/MacOS/Tone Room` | x86_64 Mach-O; 3,076,256 bytes; SHA-256 `2317fc2c6af9fdaef1e6152a2b6c2d4bbc5c79880c51221d77271c07ef3e2a65` |
| App bundle metadata | `jp.co.korg.voxamps.toneroom`; release 1.4.0; build 2910 |
| Bundled `USERBANK.vtxprog` | 528 bytes; SHA-256 `711b322a96ed9a2c3fc65a9d54c0870caa98e24c723ed8e9217a8839cbd3f60f` |
| Bundled `ToneRoom_UM_1.4.0_VTX_E.pdf` | 16 pages; SHA-256 `ba83585657187fe39f62c5c6779705570e7409486e14e1c42e91a026b4a49bd1` |

The bundled manual provides the intended editor interactions documented in [preset-files.md](preset-files.md). It is distinct from the amplifier owner's manual and the MIDI implementation PDF.

## Method and confidence

The DMG was extracted with a limited userspace reader and its package expanded without running installer scripts or Tone Room. Five extracted top-level file hashes matched REA's independent read-only mounted inventory. Static Hopper analysis through REA was checked against `otool` disassembly where indirect branches were absent from decompiler output.

The [native evidence summary](native-evidence.md) retains addresses and original REA evidence identifiers. The detailed analysis archive, installer, app binary, bundled presets and PDF files remain outside this repository. Evidence IDs identify records in that original archive; they are not public URLs or downloadable files here.

This repository packages the implementation-relevant findings independently of those large local research inputs. It does not contain original Tone Room source code, an executable replacement or firmware. The hardware validation summary retains identity bytes, aggregate observations and hashes; complete traffic and the user's settings backup remain outside the repository.

The [preset inventory](presets.md) includes derived JSON reference data: 60 complete records from the VTX initializer's table and eight records from the installer defaults. Each record retains raw bytes and a SHA-256; the embedded block's byte range, hash and native references make the extraction reproducible. Original vendor files remain outside the repository.

## Live evidence

The owner ran the experimental read-only CoreMIDI probe from a normal macOS Terminal with Tone Room closed. Capture `20261023T173434.743506Z` contains 73 transmitted requests, 143 received MIDI packets and 73 assembled replies. Independent checks reassembled the packet stream, matched it to the recorded exchanges, verified the read-only transmit allowlist, compared all 60 factory records and reconstructed the eight-slot backup. [Hardware validation](hardware-validation.md) documents the scope; [machine-readable evidence](../reference/hardware-read-validation.json) retains artifact hashes and measurements. These observations supplement the static REA evidence and are not REA runtime captures.

The owner then ran a separately authorized temporary gain test, capture `gain-20261023T174546.723684Z`. Its 13 exchanges include two gain mutations and ACKs, readback of the gain-only change and byte-exact restoration. [Gain evidence](../reference/hardware-gain-validation.json) retains the result and artifact hashes; full traffic and original user sound remain local. This live test does not establish persistent-write behavior.

## Known source ambiguities

- The custom-dump response paragraph refers to request `1C`; the explicit request definition and inspected app builder use `31`.
- The reverb allocation includes raw offset 61 without a defined field. Preserve it.
- Display divisors derive from published raw/display endpoints; actual UI tapers and steps have not been measured.
- The official MIDI layout does not specify the `.vtxprog` disk container. That format is supported by separate bundled-file and native-writer evidence.
- The family identity does not establish which VTX wattage variant is connected.

All hardware compatibility and timing claims remain subject to the [verification plan](verification.md).
