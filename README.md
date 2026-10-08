# Tmux Observer

Shared observation foundation under development for local and remote tmux clients.
Tmux Observer publishes host-local session metadata through a passive direct
collector and shared owner service. The prepared fleet service has passed
two-host awake/native and simulated recovery acceptance for always-on hosts.
Rofi Tmux Plus consumes its prepared views and retains presentation policy.

## Status

Deliveries A–E accepted in their recorded scopes, 2026-10-08; see the
[status record](docs/implementation-status.md). Pure contracts and the direct
collector and owner service passed isolated native/artifact acceptance.
Fleet/read acceptance has passed for the [always-on scope](docs/always-on-acceptance.md).
Physical sleep/wake is optional and unverified. Frontend migration and scoped
managed deployment passed separate installed/native gates on Snap and Starship;
graphical acceptance uses Starship only. Lifecycle extraction and native tmux
event experiments remain separate follow-ups.

```sh
uv run tmux-observer collect --host-id snap
uv run tmux-observer collect --host-id snap --panes --option @example
uv run tmux-observer owner --host-id snap
uv run tmux-observer snapshot --expected-host snap
uv run tmux-observer refresh --expected-host snap
uv run tmux-observer refresh_status --expected-host snap --publisher-id UUID --ticket-id UUID
uv run --extra dev ./scripts/check
uv run --extra dev python scripts/accept-native-collector --output /tmp/tmux-observer-native.json
```

`collect` is a fresh read of the default server. It does not start a service,
attach a client or create a server/session. Use a configured logical Host Mesh ID.
The pure Python API is `tmux_observer.public`; it imports no native collection,
networking or lifecycle code. Wire schemas and semantic rules are documented in
[wire v1](docs/wire-v1.md). The independent development reader is
`scripts/read-contract --schema observation` (JSON record on stdin).

`owner` explicitly runs the publisher. `status`, `snapshot`, `probe` and `watch`
read prepared state; missing services produce typed failure without activation.
`bridge` exports only that owner over stdio and accepts bounded requests on stdin.
`refresh` returns a bounded ticket; `refresh_status` reads its retained outcome.
Package installation alone does not install or enable the packaged user unit.
The accepted managed selection explicitly enables owners and starts desktop readers.

The separate client CLI has explicit fresh and prepared paths:

```sh
uv run tmux-observer-client snapshot --access direct --json
uv run tmux-observer-client context
uv run tmux-observer-client fleet --host-id snap
uv run tmux-observer-client snapshot --access cached --expected-host snap --json
uv run tmux-observer-client watch --expected-host snap --json
uv run tmux-observer-client refresh --source snap:owner --source snap:desktop --json
uv run tmux-observer-client refresh_status --publisher-id UUID --ticket-id UUID --json
```

`fleet` explicitly starts the per-context service. Its fixed local ID must match
Host Mesh. Remote owners must already be running at the selected installed owner
bridge path. Cached snapshot/status/probe/watch and ticket lookup use the private
fleet endpoint; they never activate services or fall back to direct collection.
Fresh inventory retains Tmux Session v1, while prepared operations return Fleet v1
frames. Desktop absence or unsupported contexts leave viewer membership unknown
without changing owner attachment facts. The candidate fleet unit and explicit
desktop environment handoff are documented in [service contexts](docs/service-contexts.md) and [two-host acceptance](docs/native-fleet-acceptance.md).
Installed/native acceptance and scoped managed rollout have passed separately;
the exact managed tuple and recovery/rollback evidence are linked in the status record.

The extraction baseline is released `rofi-tmux-plus 0.6.0`, source
`407ae58ba422ba88fed7da2f9d845ff274830f0e`. Its public Tmux Session v1 and
Host Mesh v1 behavior must remain compatible during migration.

## Read the design

| Document | Purpose |
| --- | --- |
| [Architecture](docs/architecture.md) | Ownership, process topology, extraction and decisions |
| [Observation contract](docs/observation-contract.md) | Identity, facts, coverage, clocks and uncertainty |
| [Service and networking](docs/service-and-networking.md) | Cached reads, subscriptions, SSH, refresh and recovery |
| [Implementation plan](docs/implementation-plan.md) | Work packages, dependencies, acceptance and rollout |
| [Implementation backlog](docs/implementation-backlog.md) | Concrete tasks, owned paths, delivery order and first implementation pass |
| [Validation plan](docs/validation-plan.md) | Independent producer, transport and frontend proof |
| [Candidate artifacts](docs/candidate-artifacts.md) | Committed-source builds, exact manifests and acceptance boundaries |
| [Design review](docs/design-review.md) | Findings, resolutions, adversarial scenarios and pending gates |
| [Context and sources](docs/context-and-sources.md) | Checked baselines, measurements and primary references |

## Intended boundary

```mermaid
flowchart LR
    T[Local tmux] --> O[Host-local observer]
    O --> P[Owner publisher]
    P -->|Local read or SSH subscription| M[Fleet reader]
    D[Desktop observations] --> M
    H[Host Mesh] --> M
    M -->|Prepared view| R[Rofi Tmux Plus]
    R -->|Explicit validated action| W[Separate lifecycle client]
    W --> T
```

The owner publisher never aggregates remote hosts. The fleet reader combines
owner facts and observations from its own desktop; it never exports its fleet
view as a remote owner's inventory. Host Mesh owns host identity and routes.
Neither observation nor cached presence grants authority to focus, attach,
close, create, rename or kill a session.

## Intended delivery order

1. Define the contract and extract bounded local observation.
2. Independently accept the standalone producer and shared owner service.
3. Add a separate fleet reader, SSH transport and desktop observation adapter.
4. Migrate Rofi reads and correct completion feedback after producer acceptance.
5. Publish and deploy accepted prepared reads through scoped chezmoi changes.
6. Independently extract lifecycle implementation and preserve the old CLI facade
   as a separate follow-up; it need not delay the read-service rollout.

Native tmux event collection is a later optional checkpoint. Initial local
collection is polling; local and SSH subscribers still receive published views
without each subscriber running a collector. Delivery push and native event
observation are separate capabilities.

## Current implementation

[Delivery A, T01–T05](docs/implementation-backlog.md#delivery-a-first-implementation-pass)
establishes package/provenance, contracts, an independent reader, direct collection
and native producer acceptance. After G1, the loop proceeds to the shared owner
service and the early fixture-backed Rofi interaction probe. The backlog and
status record specify the remaining dependencies and acceptance evidence.
