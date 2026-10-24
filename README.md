# Tmux Observer

Passive tmux observation and shared local/remote views. The host-local core reads
session metadata; an explicit owner service publishes it. Prepared readers compose
fleet and desktop evidence. A separate action client validates explicit intent.

[Project walkthrough](https://dev.byebyebryan.com/fleet-plus/projects/tmux-observer/) ·
[Documentation](docs/README.md) · [Runtime architecture](docs/runtime-architecture.md)

This is generic tmux tooling. Agent Plus opens native Codex/Claude managers directly
and has no Tmux runtime dependency. New Tmux features need a concrete tmux workflow.

## Current selection

[**0.6.0a9**](https://github.com/byebyebryan/tmux-observer/releases/tag/v0.6.0a9)
is publicly released, alongside the Tmux Plus 0.12.0a8 bundle. The managed Tmux
reader/bridge retains Mesh 0.1.0a24 and ordinary full-view delivery. The generic
shared CLI has its independent selection.
The [public supply preparation](docs/evidence/2026-10-23-public-delivery/README.md)
records exact build/qualification inputs; the
[publication closeout](https://github.com/byebyebryan/mesh-plus/blob/b306d44c329c6289781cc4db14f939ed2a4d20c2/docs/evidence/2026-10-23-public-delivery/README.md)
records subsequent publication and managed convergence. Deployment manifests own
host selections; dated native/graphical records keep their original scope.

The a9 experimental complete-view feed is explicit and unselected. Semantic delta
is also unselected. Existing generic observation and explicit actions remain supported.

## Previous accepted selection

Earlier a7/a7/a15 and preparation checkpoints remain in the
[README history](docs/readme-history.md). The
[2026-10-20 full-view record](docs/evidence/2026-10-20-mesh-a24-full-view/README.md)
retains its exact native and managed scope.

## Component map

```mermaid
flowchart LR
    T[Default tmux server] --> C[Passive native collector]
    C --> O[Owner publisher]
    O --> M[Mesh Plus state delivery]
    H[Mesh Plus host catalog] --> M
    M --> F[Observer prepared fleet reader]
    D[Endpoint-local desktop evidence] --> F
    F -->|Cached Fleet v1 and watch| U[Tmux Plus]
    U -->|Explicit intent| A[Separate Observer action client]
    A -->|Fresh validation and action| T
```

The owner exports only its own host. Each desktop has its own prepared reader;
UI clients share that reader's upstream connections. Mesh delivers state,
Observer validates native facts and joins independent desktop receipts, and
Plus chooses labels, views, ordering, selection and confirmations. Refresh
uses a separate bounded Observer control path. Actions independently validate
the current route and complete target; cached presence grants no action authority.
See [runtime architecture](docs/runtime-architecture.md) for package and process boundaries.

## Use the read interfaces

Examples use `snap` as a configured logical host ID. Substitute your endpoint's
Mesh local ID. Python 3.11+ is required; native/service support targets Linux.
From this checkout, run an explicit fresh local read:

```sh
uv run tmux-observer collect --host-id snap
uv run tmux-observer collect --host-id snap --panes --option @example
```

`collect` reads the configured default tmux server. It starts no service,
attaches no client and creates no server or session. It emits metadata only.

The owner publisher is an explicit, long-running operation. Run it separately
before querying its prepared state:

```sh
uv run tmux-observer owner --host-id snap --local-attachments
```

In another terminal, these operations read the running owner:

```sh
uv run tmux-observer status --expected-host snap
uv run tmux-observer snapshot --expected-host snap
uv run tmux-observer watch --expected-host snap
```

A fleet reader needs the configured Mesh authority, a `tmux_default` source
on each participating host and already running owners. The selected backend
is explicit:

```sh
uv run --extra mesh tmux-observer-client fleet --host-id snap --transport mesh
```

In another terminal with the same desktop environment:

```sh
uv run tmux-observer-client context
uv run tmux-observer-client snapshot --access cached --expected-host snap --json
uv run tmux-observer-client watch --expected-host snap --json
```

Cached reads and subscriptions start neither services nor native collection.
Missing, warming, failed and incompatible services return explicit states;
they never fall back to a fresh read. The generic fleet CLI defaults to
`legacy`; managed selection passes `--transport mesh` explicitly.

Fresh fleet diagnosis remains a separate operation, returning Tmux Session v1:

```sh
uv run tmux-observer-client snapshot --access direct --json
```

Explicit passive refresh returns a scoped ticket. Use the reply's fleet
publisher and ticket IDs for lookup:

```sh
uv run tmux-observer-client refresh --source snap:owner --source snap:desktop --json
uv run tmux-observer-client refresh_status --publisher-id UUID --ticket-id UUID --json
```

Package installation does not install or enable user units. Deployment captures
desktop context and starts services explicitly; see [service contexts](docs/service-contexts.md)
and [current Mesh source configuration](docs/mesh-integration.md#current-configuration).

## Develop and read further

```sh
uv run --extra dev ./scripts/check
uv run --extra dev --extra mesh python scripts/check-mesh
```

The first command is the source/contract/lint gate. The second adds separate
Mesh integration checks. Native probes use owned disposable resources.
Package, installed, resource, graphical and recovery acceptance keep their own gates.

The pure native API is `tmux_observer.native`; `tmux_observer.public` retains
the compatibility facade. Prepared reads use `tmux_observer_client.public`.
Actions use `tmux_observer_actions.public` independently of observation services.

Start with the [documentation index](docs/README.md), [runtime architecture](docs/runtime-architecture.md),
[wire contracts](docs/wire-v1.md) and [action/desktop contracts](docs/boundary-wire-v1.md).
The [original architecture](docs/architecture.md), [first-delivery backlog](docs/implementation-backlog.md)
and historical acceptance records preserve their original decisions and scope.
Native control-mode events and physical sleep/wake remain optional follow-ups.
