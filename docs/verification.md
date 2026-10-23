# Verification plan and open questions

## Evidence already available

- VOX's published protocol defines framing, commands, offsets and model-dependent parameter ranges.
- Tone Room 1.4.0 packet builders and receiver branches corroborate selected command codes, 62/71-byte record sizing, high-bit packing order and base-128 parameter values.
- The bundled 528-byte bank and two native writer branches establish eight- and eleven-record `.vtxprog` forms.
- The earlier investigation's separate codec passed 14 offline tests, including fixed vectors, packing boundaries, malformed input and lossless round-trips of the bundled eight-record bank. That experimental code and vendor fixture are not part of this documentation-only repository.

**No amp traffic was captured, no program was read from the user's device and no hardware write was performed.** This repository's vectors are synthetic. Passing offline codec checks does not establish device compatibility.

## Offline checks for the future implementation

1. Match all valid and invalid examples in [test-vectors.json](../reference/test-vectors.json).
2. Test every partial packing-group length, all byte values 0–255 and full 62-byte records; verify 71 packed bytes and the unused final-prefix bit.
3. Validate exact message lengths, headers, seven-bit data values and documented selectors.
4. Exercise raw base-256 and wire base-128 encoding independently, including the 1200 ms delay example.
5. Preserve reserved bytes, unused model fields and disabled effects through field edits and file round-trips.
6. Require model context for effect validation; reject undefined parameter IDs/sub-IDs.
7. Parse both observed `.vtxprog` counts, reject truncated bodies and report unknown versions/counts without fabricating compatibility.
8. Simulate interleaved events, late ACKs, NAKs, disconnects and unknown write outcomes. Ensure one writer owns the device session.

## First hardware session: read-only

Record OS, amp label, USB endpoint names/IDs, device identity bytes and firmware version fields. Use a known data-capable USB cable and establish a working host connection before testing wireless bridges.

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
| Does this VT20X enumerate and exchange MIDI correctly? | No live connection | Identity plus complete read responses |
| Which USB VID/PID and endpoints should discovery use? | Only Tone Room name hints | OS enumeration on actual hardware |
| Does Linux/Raspberry Pi work without a vendor driver? | Not established | ALSA/system MIDI enumeration and bidirectional SysEx |
| Does a Bluetooth MIDI host adapter work? | Tone Room scans `UD-BT01`; not compatibility proof | Identity/read/notification tests with the adapter |
| Is custom request `31` correct? | Official request definition plus native builder agree | Live custom-data response |
| What are safe timeouts, pacing and slider rates? | Some native delay constants | Timestamped measurements, failure/reconnect tests |
| What happens after a lost ACK or retransmitted write? | No transaction IDs | Controlled readback and recovery tests |
| Does writing the selected slot alter current sound? | Unresolved | Compare mode/current and slot before/after |
| What does the manual-mode program byte mean? | Not separately specified | Compare accepted values and resulting state |
| Which values reset after an amp/effect model change? | Model-dependent schema known | Full before/after current dumps |
| How are custom defaults recalled in each mode? | Bundled manual describes differing modes | Observe commands and resulting state |
| What is raw byte 61? | Unspecified; zero in shipped defaults | Preserve; analyze additional records/firmware evidence |
| What is the eleven-record file writer's UI purpose? | Writer exists | Actual export or caller analysis |
| Are arbitrary counts/other headers compatible? | Only two writer shapes observed | Controlled Tone Room file round-trips |
| Can a Zero 2 W host the whole chosen stack reliably? | No benchmark | Measure memory, CPU, reconnect behavior and client support |

Update this table with the exact device/firmware, experiment and evidence locator when an uncertainty is resolved. Do not promote a proposed design rule into a protocol fact based only on a passing mock test.
