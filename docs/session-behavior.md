# Session behavior

This document is a **proposed application contract** built around the specified messages. It does not claim to reproduce Tone Room's complete state machine or measured firmware behavior.

## Ownership and state

One device session should own the MIDI input/output pair and one serialized operation queue. Future UI and MCP clients submit operations through that owner rather than opening competing writers.

Maintain separate state for:

- `desired`: the most recent user intent, including pending edits.
- `confirmed`: the latest device state, with timestamp and verification level.
- `stored`: the last retrieved persistent slots and custom defaults.
- `library`: local programs/files independent of the active device.

A disconnected session may retain a cached snapshot, but must mark it stale. A successful data transmission is not an ACK, and an ACK is not a full readback. Include connection generation and a local operation ID in application events; these are not fields on the wire.

## Connect and synchronize

```text
open candidate input/output pair
  -> universal identity inquiry
  <- validate VTX family identity
  -> read mode
  <- mode data
  -> read current program
  <- current dump
  -> read user slots 0..7 sequentially when backup is requested
  <- retain complete raw records and slot metadata
```

Names seen in Tone Room's scanner include `Valvetronix X`, `VOX 2ch Audio Device`, `Adio` and `UD-BT01`. They are discovery hints, not an exhaustive allowlist or proof of a valid paired input/output. Match identity and responses before reporting a connected session. USB VID/PID and Linux endpoint behavior are not established by this investigation.

Read custom defaults separately when required. Reading all 60 factory presets is optional and can be deferred. Treat a multi-request snapshot as potentially inconsistent if the user changes a physical control while it is collected; resynchronize affected state.

## Reply matching

| Pending operation | Match candidate |
| --- | --- |
| Identity inquiry | Universal identity response with VTX manufacturer/family |
| Mode read | `42` mode data |
| Current read | `40` current dump |
| Stored-program read | `4C` with the requested bank and slot |
| Custom-data read | `65` with reserved zero and requested index |
| Parameter/mode/dump mutation | Generic `23`, `24` or `26`, with only one such mutation outstanding |
| Save current | `21` or `22` with requested slot; reconcile panel-write notifications |

The lack of transaction IDs means even a serialized queue cannot reliably distinguish every delayed or unsolicited acknowledgement. After a timeout, do not immediately send an unrelated write that could consume a late ACK. Resynchronize and read back the affected state; establish any drain/reset policy from hardware tests.

Dispatch unsolicited `41`, `4E` and `21` events separately from ordinary replies. A conflicting mode change should invalidate queued edits tied to the previous program/model until resynchronization. Preserve unknown messages with direction, timestamp and connection identity for diagnostics.

## Operation sequences

### Parameter edit

Validate the parameter against the confirmed model context, encode `41`, send it, await completion and update the confirmed field. If hardware events conflict, refresh the full current program. Continuous-control updates may later be coalesced by parameter; safe rates and ordering must first be measured. Do not coalesce across a model change or save operation.

### Select a program

Resolve unsaved-edit policy in the caller, send `4E`, await ACK, then read mode and current program. Replace model-dependent field mappings from the received program. Program selection must not implicitly save the old sound.

### Preview a full sound

Keep a recoverable snapshot of the current program if the user expects revert. Send `40`, await ACK and read current data back. Revert is another current-buffer update, not a documented firmware undo operation; it must account for physical edits since the snapshot.

### Save current to a slot

Take the queue's current-state snapshot, send `11 00 slot`, await matching `21` and read the slot with `1C 00 slot`. Compare to the expected raw record. Physical edits can race with the write; report mismatches rather than silently treating them as success.

### Write a complete stored program

Send `4C 00 slot packed-program`, await generic ACK, read the slot and compare. Whether writing the currently selected slot changes the playing buffer is unverified; refresh current state as appropriate. Do not equate a slot write with program selection.

### Restore a bank

Back up the destination before the restore when a backup is requested by the workflow. Write and verify one slot at a time, recording the result of each. On failure, stop and return the partial result. No atomic bank write or automatic rollback is documented.

### Custom defaults

Validate each section against the custom index, preserve unused bytes/sections, send `65`, await ACK and read back with `31`. Recalling custom settings and writing their stored defaults are separate actions; mode-specific recall behavior needs validation.

## Failure and reconnect

- Invalid argument: reject before sending any bytes.
- NAK or format error: retain raw response and stop the affected operation; do not repeatedly resend unchanged bytes.
- Timeout after sending a mutation: mark outcome unknown and read back before retrying.
- Disconnect: stop sending, invalidate endpoint handles and preserve pending-write uncertainty.
- Reconnect: identify the device again, refresh mode/current state and reconcile affected stored slots before replaying intent. Do not automatically replay persistent writes.

Timeout values, retry count, minimum packet spacing, slider limits and firmware differences remain unverified. Tone Room's static delays are clues for measurements, not universal deadlines. See [native evidence](native-evidence.md) and [verification](verification.md).
