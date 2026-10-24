# Optional Mesh preparation

The optional pure Python preparation facade is retained in Observer a9 with
SDK 1. It was introduced by the a8/a18 qualification; those original package
and native results remain bounded to their receipt. Observation, Service, Fleet
and Mesh wire meanings are unchanged. This facade does not automatically replace
the fleet consumer's independently selected guard or transport.

Current selection belongs to [managed operations](../maintenance/operations.md).

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
the supported Tmux profile and `tmux-observer-0.6.0a8:preparation-v1` semantics.

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

A future consumer should adopt only if it actually performs repeated Mesh current
queries on the same generation and its measured work is reduced. Preserve thread
ownership and raw/native projection needs; do not share a live guard across
threads or bypass admission to manufacture a saving. This facade needs no Agent,
Plus, transport or managed deployment migration.
