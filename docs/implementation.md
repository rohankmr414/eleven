# Implementation boundaries

Status: proposed application design. The [experimental scripts](../scripts/README.md) provide a pure codec, macOS read-only transport and a narrowly scoped gain probe. A reusable device service, UI, Linux transport and MCP server remain to be implemented.

## Layers

```text
UI / CLI / MCP tools
        |
application operations and preset library
        |
device session: queue, state, replies, events, readback
        |
codec: frames, packing, typed program fields
        |
MIDI transport: endpoint lifecycle and byte delivery
        |
VT20X
```

| Layer | Responsibilities | Important boundary |
| --- | --- | --- |
| Transport | Enumerate/select MIDI endpoints, send bytes, assemble received SysEx, report hotplug/disconnect | No preset semantics or UI state |
| Codec | Validate frame shapes, encode/decode values, pack/unpack records | Pure transformations; no implicit device I/O |
| Program model | Typed fields, model context, lossless raw-byte preservation | Keep raw bytes authoritative for unknown fields |
| Session | One owner/queue, deadlines, reply matching, unsolicited events, reconciliation | Own every device mutation |
| Library | `.vtxprog` inspection/export, backups, comparisons | File actions do not implicitly write the amp |
| API adapters | Present the operations in [API map](api-map.md) | UI and MCP share the same session semantics |

## Deployment candidates

- A Mac process can use the system MIDI facilities, host the device service and expose local MCP tools.
- A Raspberry Pi can be evaluated as a USB host running a small MIDI/MCP bridge. A browser interface could use the same service over the local network.
- A future Electron app can host the service locally or connect to an existing bridge.

These are candidates, not tested integrations. The Pi must act as a **USB host** for the amplifier; USB gadget mode has a different role. Linux enumeration, bidirectional SysEx and resource usage remain verification items. Running Codex or another MCP client on the bridge is a separate deployment decision and is not required by the amp protocol.

## Minimum first implementation

1. Use and extend the [experimental codec](../scripts/vtx.mjs), checked against the [wire reference](wire-protocol.md), [parameter map](program-layout.md) and [synthetic vectors](../reference/test-vectors.json).
2. Turn the macOS read probe into a reusable transport/session with explicit lifecycle handling; add a Linux transport separately.
3. Preserve the existing eight-slot backup behavior and firmware/transport diagnostics in that service.
4. Add physical-control event handling and readback synchronization.
5. Add temporary parameter/full-program edits after the read path is verified.
6. Add explicit slot saves, custom-default writes and restore flows with readback.
7. Expose the same operations to an MCP server or UI after device behavior is established.

## Avoid accidental assumptions

- A numeric parameter is not necessarily a 0–127 slider: use its model-dependent range and unit.
- Byte 61 and reserved regions are not scratch space.
- A 62-byte custom record is not an ordinary 62-byte program.
- A transport write does not confirm a hardware save.
- A local operation ID cannot be matched against a nonexistent wire transaction ID.
- A `.vtxprog` file is not a SysEx dump.
- Eight user slots do not constrain every local library file to eight records.
- A VTX family identity does not identify the exact amp model.
- Tone Room's native timing constants do not establish safe throughput on USB, Wi-Fi or Bluetooth.

The [verification plan](verification.md) defines the evidence needed before making compatibility claims.
