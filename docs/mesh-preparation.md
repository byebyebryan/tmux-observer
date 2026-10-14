# Optional Mesh preparation

Source/private candidate **Tmux Observer 0.6.0a9** supports Mesh SDK 1 and
optional preparation interface 1 with the reviewed **Mesh 0.1.0a19** source
`6e2e7e8608602ceb047c1b6c5b5de57532f6a173`. This is an additive local
Python facade; Observation, Service, Fleet and Mesh wire bytes are unchanged.
Released/managed Observer a7 / Mesh a15 retain their separate acceptance.

## Supported owner facade

```python
from mesh_plus.api import PreparedReadGuard
from tmux_observer.mesh_preparation import make_preparation
from tmux_observer.mesh_profile import TmuxMeshProfile

guard = PreparedReadGuard(
    "tmux", request_id,
    profile=TmuxMeshProfile(), preparation=make_preparation(), host_ids=host_ids,
)
# The owning watch loop admits each frame, reads at its actual clock/time,
# and disconnects the guard on teardown. Reconnect creates a new guard.
```

Importing `tmux_observer.mesh_preparation` requires no Mesh installation and
performs no collection, process, socket or desktop work. Calling the explicit
factory opts into the installed Mesh dependency. The descriptor binds interface 1,
the supported Tmux profile and `tmux-observer-0.6.0a9:preparation-v1` semantics.

For an admitted immutable generation, one rule per record preserves the full
`hostId/serverGeneration/sessionId/createdAt` identity, requires the same
`default` current/partial native receipt keys as `TmuxMeshProfile`, and retains
the same eligibility. These rules are generation-static: clocks, environment,
I/O, collection and mutable external state never contribute. A semantic or
implementation binding change requires guard retirement and fresh admission.
The implementation label is an owner promise, not Mesh attestation.

Mesh continues to own boundary validation, serialized private state, delivery
binding, expiry, gap/resync, disconnect and guard lifetime. Exported dictionaries
are copies. Heartbeats do not renew native facts. The facade grants no action
or collection authority and does not change polling APIs.

## Fleet adoption decision: retain ReadGuard

The actual Fleet worker calls `ReadGuard.accept()` and queues raw Mesh frames
across its thread boundary. Observer's `MeshOwnerState` reconstructs the native
owner document and maintains Observer's prepared Fleet projection. It does not
call Mesh `ReadGuard.current()`. A mechanical PreparedReadGuard replacement
therefore compiles unused rules and removes neither native document admission
nor Observer projection. Production keeps `ReadGuard`; there is no new selector.

The preceding a8/a18 [installed/native qualification](evidence/2026-10-14-preparation/README.md)
certifies that checkpoint and records 40 actual IPC/SSH comparison cases.
The independent a9/a19 installed gate includes the facade tests; its version
label requires fresh preparation rather than reusing an a8 guard. Timing
shows no consistent benefit from the diagnostic replacement. Generic repeated
Mesh-current microbenchmarks remain evidence for their own consumer shape.

A future consumer should adopt only if it actually performs repeated Mesh current
queries on the same generation and its measured work is reduced. Preserve thread
ownership and raw/native projection needs; do not share a live guard across
threads or bypass admission to manufacture a saving. This facade needs no Agent,
Plus, transport or managed deployment migration.
