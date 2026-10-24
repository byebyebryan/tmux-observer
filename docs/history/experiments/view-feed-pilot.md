# Opt-in complete-view feed pilot

> Historical record. This document preserves its original checkpoint and may describe retired providers, interfaces or plans. Use the [current documentation](../../README.md) for supported setup and behavior.

Tmux Observer **0.6.0a9** is a source/private candidate using experimental
[Mesh 0.1.0a24](https://github.com/byebyebryan/mesh-plus/releases/tag/v0.1.0a24),
tag commit `bb0c45399e5b8264c9936ca48457cc9a442431df`. The downloaded wheel is
`mesh_plus-0.1.0a24-py3-none-any.whl`, SHA256
`9bca5b554babfa59ba56b1a4ac5e8e5c66a85e63709731ee1fe7d4f0ed6a18a6`.
This does not change the [managed selection](../../mesh-integration.md#current-configuration).

The publisher still supplies complete native Service v1 views through
`tmux_observer.mesh_publisher.make_publisher`: the existing `CachedPublisher`,
`TmuxCachedSource` and pure `TmuxMeshProfile`. The explicitly selected
`ViewFeedBridge` computes whole-record changes and the ordinary Reader from
`mesh_plus.view_feed.configured_reader` reconstructs and validates full targets.
Hash comparison, empty selector and the Mesh default limits are used; no
publisher token is supplied. This is separate from the retained semantic delta
engine. The frozen Observation, Service, Fleet and compatibility schemas remain
unchanged.

## Explicit setup

An already running owner is required. Reads and feed negotiation neither start
that owner nor collect tmux metadata. Configure the fixed source in a private
Mesh configuration, for example:

```toml
version = 1
host = "snap"
[sources.tmux_default]
domain = "tmux"
socket = "/private/runtime/owner.sock"
```

Use an isolated candidate environment containing the exact Observer candidate
and verified a24 wheel. A trusted `mesh-plus` launcher on each disposable test
endpoint injects the owner factory through the public Mesh CLI:

```python
from mesh_plus.cli import main
from tmux_observer.mesh_publisher import make_publisher

raise SystemExit(main(publisher_factories={"tmux": make_publisher}))
```

The explicit publisher commands in that environment are:

```sh
mesh-plus view-feed-serve --config /private/sources.toml \
  --source tmux_default --socket /private/runtime/feed.sock
mesh-plus view-feed-bridge --config /private/sources.toml \
  --source tmux_default --stdio
```

The first command serves IPC; the second is the fixed non-PTY SSH command
selected by Mesh's feed reader. Configuration chooses only a fixed cached
source. It does not accept executable imports from transport messages. This
recipe describes candidate setup; it authorizes no replacement of the shared
managed launcher or its Agent source.

The owning Fleet client opts into both its local bridge and remote Reader:

```sh
tmux-observer-client fleet --host-id snap --transport mesh --view-feed
```

`--view-feed` requires `--transport mesh`. Without it, Mesh's existing `Bridge`
and `mesh_plus.api.configured_reader` serve the ordinary full-view route.
The generic Fleet CLI still defaults to `--transport legacy`. The candidate's
optional Mesh dependency is a24 in either Mesh mode; prior accepted artifacts
retain their independent a18/a15 pins. Every selected remote endpoint must
support the explicitly requested feed. Unsupported negotiation fails closed;
there is no wire detection or automatic fallback.

## Authority and lifetime

The worker retains its existing thread, ordinary `Reader.watch`, `ReadGuard`
admission, bounded JSON handoff queue and Observer Fleet projection. No live
guard or borrowed feed handle crosses that thread boundary. Mesh atomically
reconstructs owner metadata, record operations and order before returning a
complete candidate. A replacement's empty operation list does not imply an
empty native view.

Full identity remains `hostId/serverGeneration/sessionId/createdAt`. Omitted
rows in partial or unavailable observations cannot establish absence. Snapshot
and proof requests still return full native replies with fresh nonces. A watch
candidate is a wakeup for a full read/proof; it grants no currentness. Gap,
disconnect, source failure and expiry retain their existing invalidation and
recovery rules. Read/subscribe operations do not schedule collection or grant
lifecycle authority.

The existing Tmux source filters native `heartbeat` frames, including newly
accepted samples whose session values are unchanged. Their advancing receipts
reach the ordinary Reader through its periodic full cached read/proof (three
seconds for Tmux), rather than a feed packet. Qualification distinguishes that
native behavior from synthetic metadata-only feed reconstruction. No source
cadence, receipt, capability, native bound or deadline is relaxed for this pilot.

## Qualification and cost boundary

The [owning evidence record](../../evidence/2026-10-20-view-feed-pilot/README.md)
separates source, exact installed wheels, native IPC/fixed SSH, SDK lifetime
tests and cost measurements. `scripts/qualify-view-feed-pilot` runs a bounded
two-owner workload over disposable default-server namespaces and an owned
loopback SSH daemon. It includes cold setup, ordinary Reader full reads/proofs,
one planned reconnect and Observer domain admission/projection. Native session
identities, attachment counts, hooks and options are checked independently.

Byte totals count both directions once at each completed owner-cache JSON and
Mesh JSON edge, including full snapshots/proofs/recovery, with LF framing.
They exclude SSH encryption/framing, failed partial writes and tmux command
stdout. CPU includes the coordinator, reaped descendants and sampled owned tmux
daemon work; actor, oracle, instrumentation and cleanup are included. Summed RSS
is sampled across the owned process tree plus daemonized tmux and descendants,
including source/cache/Reader/profile/runtime allocations. It double-counts
shared pages and may miss transient peaks. These measurements are neither feed
reservation peaks nor a hard physical memory/capacity guarantee.

This pilot does not accept normal-host performance, maximum 256-session capacity,
physical suspend, graphical presentation, installed services, managed recovery,
fleet rollout, release publication or a downstream consumer migration. A smaller
watch packet alone is insufficient to recommend adoption.
