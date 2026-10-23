# Native implementation evidence: Tone Room 1.4.0

Scope: static inspection of the extracted x86_64 executable, SHA-256 `2317fc2c6af9fdaef1e6152a2b6c2d4bbc5c79880c51221d77271c07ef3e2a65`. No amplifier communication or target execution occurred. Addresses below are the executable's unslid virtual addresses, not live process addresses. Recovered `sub_...` labels are analysis labels, not original source names.

The original local analysis archive contains `native-rea.json` dossiers (pseudocode, assembly, references and limitations) and independent `native-disassembly.txt` output from `otool -tvV`. Those files are retained outside this repository; the evidence identifiers below refer to that archive. Artifact hashes and method are in [sources.md](sources.md). Several Hopper dossiers omit indirect jump-table case bodies, so the packet-builder claims below also use exact branches from that disassembly. This prevents treating incomplete decompilation as complete control flow.

## Transport and discovery

- CoreMIDI imports include `MIDIClientCreate`, endpoint enumeration, input/output port creation, source connection, and `MIDISend`. JUCE and model-specific C++ RTTI names are present. This supports a native C++/JUCE controller architecture; it does not recover its original source tree.
- `0x1000e4686` calls `MIDISend` for a real output port, or `MIDIReceived` for the alternate virtual-endpoint route. Evidence `ev_551408950231ceb305526e1f7a3eca54e4be58bcee6170942002c60932a83b55`.
- `0x1000e3e26` creates CoreMIDI packet lists and calls the transport wrapper. It contains a 256-byte SysEx packet-splitting path. Evidence `ev_9a199870e488f00a02fdad205f321d13ee8e9aadfb834cf8180a3d5e2e347789`. The VTX messages examined here are shorter than that threshold.
- `0x1000ffce8` builds inquiry payload `7E 7F 06 01`, then calls the common SysEx constructor and sender. Evidence `ev_1b04f9759bfd65377b2da9940475f333c342b2cec9ef38f5bfa9bff91f3fefb6`.
- `0x10012d920` adds `F0` before and `F7` after the body. Evidence `ev_1cb2d33b2818907cb11224b4b9c433ba94c498114a29dd216423ee97a597157a`.
- `0x1000ffa96` scans output candidates, compares names against `Valvetronix X`, `VOX 2ch Audio Device`, `Adio`, and `UD-BT01`, and calls the inquiry sender for candidates. Evidence `ev_24de935f2f3b9f46db3a2ea866095859717a082ed366de7b208125dc531aac41`. Names identify candidates, not a validated input/output pair; the exact equality/substring semantics of its string helper were not established.

## Packet builders

VTX uses internal model dispatch index 2 in the inspected builder branches. They write the little-endian immediate `0x01003042`, yielding bytes `42 30 00 01`, followed by a stored device-family byte. The VTX receive handler explicitly checks that byte as `34`.

| Builder entry | VTX branch / key instructions | Meaning |
| --- | --- | --- |
| `0x100018aa4` | Branch `0x100018adb`; `0x100018b15` writes `11 00`; slot at body offset 7 | Save current buffer to user slot |
| `0x100018b4c` | Branch `0x100018bdb`; `0x100018bf0` writes `1C`; `sete` at `0x100018bf7` produces wire bank selector | Stored-program read |
| `0x100018c30` | Branch `0x100018c63`; `0x100018c9d` writes `10` | Current-program read |
| `0x100018d20` | Branch `0x100018d53`; `0x100018d8d` writes `12` | Mode read |
| `0x100018dc0` | Branch `0x100018df3`; `0x100018e2d` writes `40` | Current-buffer dump header |
| `0x100018e60` | Branch `0x100018ef9`; `0x100018f0e` writes `4E`; mode and program follow | Mode/program selection |
| `0x100018f7c` | Branch `0x10001900b`; `0x100019020` writes `4C` | Stored-program dump header |
| `0x100019060` | Branch `0x1000190a7`; `0x1000190e1` writes `41`; ID/sub-ID/LSB/MSB follow | Parameter change |
| `0x10001912c` | Writes `31 00` and custom slot; accepts slots 0–3 | Custom-data read |
| `0x100019178` | Writes `65 00` and custom slot; accepts slots 0–3 | Custom-data write |

The internal bank and mode enums differ from wire values. For example, the read/dump builder uses `sete` to invert its internal bank flag. A new client should use the published wire enums rather than copying Tone Room's internal values.

The last two builders have complete readable dossiers: `ev_811a702875b41652e011f678ae681281efe006a185907d34eedf18c0529573d5` and `ev_594046bc654457f97e33ae6a16f24478ed4cf8d065cc853babffe51674b07cc1`. The custom read's `31` confirms the explicit request definition in VOX's PDF, despite the later response paragraph referring to `1C`.

## Packing and parameter values

- `0x1001018aa` splits a value into `value & 0x7f` and `value >> 7`, calls the `41` builder, wraps it, and sends it. Evidence `ev_18495d3ea65edf4533a0f1fd8a13793fc7666186ff448c643a485ec956783b1b`.
- `0x10012867f` packs each group of seven raw bytes as one prefix and seven low-bit bytes. Prefix bit 0 holds raw byte 0's high bit, prefix bit 1 holds raw byte 1's high bit, etc. It handles the final partial group. Evidence `ev_67469ab787e14e2de500d575119551240e6da54ddf6f53900894c9677b8e8f06`.
- `0x100128763` reverses that packing. Evidence `ev_81eb18db46d8ea09260cda42ceb50061c2d121e8aaaa4a07d737060230dbcc28`.
- `0x100101042` has 62-byte (`0x3e`) program branches whose packed bodies are 71 bytes (`0x47`), matching the specification. Evidence `ev_19a7a8c02c06d1ae26992a0fd7dbbd5c250838f7645d74788ac71a83da921c81`.

## Receive and synchronization paths

`0x1000c92cc` is a VTX-specific receive handler: it checks manufacturer `42` and family bytes `00 01 34`, then dispatches functions `21`, `23`, `24`, `40`, `41`, `42`, `4C`, `4E`, and `65`. Evidence `ev_2dfc06a8ba02b32458aed211293f3f8ff22c2c15e2aa9a5f5e0b890b8fcd47a9`.

Observed branches:

- `40`: unpack 71 bytes to the 62-byte current program and notify a virtual listener.
- `4C`: unpack a stored program, update the corresponding model store, and conditionally schedule the next read. The progress bookkeeping distinguishes the 60-preset range from eight user slots. Do not infer an exact startup sequence solely from the partially decompiled state flags.
- `65`: unpack custom data; during synchronization it advances custom slot indices through 0–3, then posts completion.
- `42`: cancel the outstanding mode-request timeout, update mode/selection, and conditionally start stored-program reads.
- `4E`: update mode/selection from an unsolicited change.
- `41`: forward a parameter-change event through a virtual callback.
- `21`: forward a completed write with its user-slot index.
- `23`: advance a bulk-write sequence when that state flag is set.
- `24`: clear bulk-operation flags and stop the pending action.

This is a bounded analysis of one handler, not proof of all validation or error behavior in the application. No complete reconstruction of its event system was attempted.

## Timing evidence and limits

- Save-current wrapper `0x100100c5c` invokes a sleep helper with `0x96` (150) after sending. Evidence `ev_5b39bdc0a6decbbdff7fb4008b45fbd3a962bb1a67167106fc41977d30e9504f`.
- The helper `0x1001bef7a` converts milliseconds to a `timespec` and calls `nanosleep`; see `otool` instructions and evidence `ev_623278b842ed5baab76043202fdd0184b19340cc8d44c86c80497c97ee35a168`.
- Inquiry scan `0x1000ffa96` uses a 200 ms pre-scan sleep, a wait call with argument 500, and a 150 ms post-probe sleep. Only the sleep helper's units are independently established here; the wait helper was not fully analyzed.
- Action-manager routine `0x1000f2a82` contains the named `eREQID_MODEREQUEST_TIMEOUT` action and schedules it with `0x7d0` (2000) before the mode request. Evidence `ev_6cb636e7eb057c55579b49016c5522448d8a189ca9e9207302679735f967f47b`. A 2-second timeout is a plausible interpretation of this timer API, not a measured requirement.
- The VTX handler inserts small sleeps before some follow-up reads. Slider throttling, safe sustained message rate, retries, and firmware-specific deadlines remain unverified.

## Preset files and reproducibility

See [preset-files.md](preset-files.md) for two independently verified VTX writer branches (8 and 11 records). The raw records align with the official MIDI program layout, but the disk container is separate from the MIDI frame format.

The original DMG was unpacked using a deliberately limited userspace reader for this observed UDIF/HFS+ image, then `pkgutil --expand-full`. Neither the installer scripts nor Tone Room executable were run. Every extracted top-level file hash matches the REA inventory. REA's native analysis session was saved and closed after export.

## Preset-writer evidence identifiers

- Eight-record writer `0x1000f0d46`: `ev_8bab5a555f68605ae283893ed58b706ae68554b787ca164b8764e9089da6826a`. VTX header branch `0x1000f0e65`; write size 528 bytes.
- Eleven-record writer `0x1000f2060`: `ev_fd86e65d4c70b7dc941fc098dfb434069e6ac8f7415ebd9f93021cf8bf2a488e`. VTX header branch `0x1000f21c5`; write size 714 bytes. Exact UI use remains unresolved.
