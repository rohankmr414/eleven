# Verification plan and open questions

## Evidence already available

- VOX's published protocol defines framing, commands, offsets and model-dependent parameter ranges.
- Tone Room 1.4.0 packet builders and receiver branches corroborate selected command codes, 62/71-byte record sizing, high-bit packing order and base-128 parameter values.
- The bundled 528-byte bank and two native writer branches establish eight- and eleven-record `.vtxprog` forms.
- A VTX-specific initializer copies 60 complete records from an embedded table. The [recovered bank](presets.md) passes model-dependent range validation and lossless offline MIDI packing checks; all 60 records now also match their live factory slots on the tested original VT20X.
- The separate experimental codec passes 16 offline tests, including all 68 recovered records and comparison with the executable. Five macOS transport tests cover fragmentation, packet layout, the read-only allowlist and endpoint/reply matching. A synthetic capture integration check validates backup generation. That experimental code and vendor fixture are not part of this documentation-only repository.
- The [2026-10-23 hardware session](hardware-validation.md) completed all 73 read requests, backed up eight user slots and preserved mode/current state between the initial and final reads.

**No hardware write was performed.** Identity, mode/current reads and both stored-program banks are verified on the owner's original VT20X with identity version fields 1.1 on macOS. Custom reads, mutations, physical-control notifications, reconnects, Linux/Pi and wireless transport remain unverified. The existing `test-vectors.json` examples remain synthetic and separate from live evidence.

## Offline checks for the future implementation

1. Match all valid and invalid examples in [test-vectors.json](../reference/test-vectors.json).
2. Test every partial packing-group length, all byte values 0–255 and full 62-byte records; verify 71 packed bytes and the unused final-prefix bit.
3. Validate exact message lengths, headers, seven-bit data values and documented selectors.
4. Exercise raw base-256 and wire base-128 encoding independently, including the 1200 ms delay example.
5. Preserve reserved bytes, unused model fields and disabled effects through field edits and file round-trips.
6. Require model context for effect validation; reject undefined parameter IDs/sub-IDs.
7. Parse both observed `.vtxprog` counts, reject truncated bodies and report unknown versions/counts without fabricating compatibility.
8. Simulate interleaved events, late ACKs, NAKs, disconnects and unknown write outcomes. Ensure one writer owns the device session.

## Hardware verification checklist

Items 1–5 were completed in the first read-only session. Items 6–7 remain pending.

Record OS, amp label and hardware generation, USB endpoint names/IDs, device identity bytes and firmware version fields. The intended device is the owner's original VT20X, before Classic Blue; the family identity reply alone does not establish generation. Use a known data-capable USB cable and establish a working host connection before testing wireless bridges.

1. Enumerate and open the selected MIDI input/output pair.
2. Send universal identity inquiry; verify manufacturer/family and input/output pairing.
3. Read mode and current sound; retain timestamped raw TX/RX frames.
4. Read each user slot 0–7 and save a lossless backup outside the amp.
5. Repeat a read to check stability and observe response latency.
6. Observe physical knob changes, effect toggles and program changes while capturing messages; correlate `41`/`4E` with the panel action.
7. Reconnect and confirm state can be reconstructed without replaying writes.

A panel program change can discard unsaved edits even though the client sends only reads. Plan the observation session with the current sound preserved where needed.

## Later mutation verification

After backups and device reads are verified, test one reversible current-buffer parameter edit and read it back. Then test full-buffer preview, selection changes and model-change side effects. Persistent-write tests must target a deliberately chosen slot and verify its complete contents afterward. Test custom-default writes separately from user programs.

For a future bank restore, verify partial-failure reporting and recovery before treating it as a normal workflow. Keep timing measurements specific to the transport and firmware used.

## Open questions

| Question | Current evidence | Required next evidence |
| --- | --- | --- |
| Does this VT20X enumerate and exchange MIDI correctly? | Verified: 73 read requests/replies on macOS | Reconnects, notifications and mutations remain to test |
| Which USB VID/PID and endpoints should discovery use? | Observed `0944:0132`, input/output `Valvetronix X CTRL` | Other hosts/devices; do not hardcode session endpoint handles |
| Does Linux/Raspberry Pi work without a vendor driver? | Not established | ALSA/system MIDI enumeration and bidirectional SysEx |
| Does a Bluetooth MIDI host adapter work? | Tone Room scans `UD-BT01`; not compatibility proof | Identity/read/notification tests with the adapter |
| Is custom request `31` correct? | Official request definition plus native builder agree | Live custom-data response |
| What are safe timeouts, pacing and slider rates? | 73 paced reads: 1.274–3.946 ms response latency, median 1.967 ms; 75 ms test pause | Sustained rates, mutations, failure/reconnect tests; these reads do not establish safe slider rates |
| What happens after a lost ACK or retransmitted write? | No transaction IDs | Controlled readback and recovery tests |
| Does writing the selected slot alter current sound? | Unresolved | Compare mode/current and slot before/after |
| What does the manual-mode program byte mean? | Not separately specified | Compare accepted values and resulting state |
| Which values reset after an amp/effect model change? | Model-dependent schema known | Full before/after current dumps |
| How are custom defaults recalled in each mode? | Bundled manual describes differing modes | Observe commands and resulting state |
| What is raw byte 61? | Unspecified; zero in shipped defaults | Preserve; analyze additional records/firmware evidence |
| What is the eleven-record file writer's UI purpose? | Writer exists | Actual export or caller analysis |
| Does the embedded 60-program bank match the amp's factory bank? | Verified 60/60 byte-exact, index-for-index on original VT20X identity version 1.1 | Other firmware/models remain unverified |
| Are arbitrary counts/other headers compatible? | Only two writer shapes observed | Controlled Tone Room file round-trips |
| Can a Zero 2 W host the whole chosen stack reliably? | No benchmark | Measure memory, CPU, reconnect behavior and client support |

Update this table with the exact device/firmware, experiment and evidence locator when an uncertainty is resolved. Do not promote a proposed design rule into a protocol fact based only on a passing mock test.
