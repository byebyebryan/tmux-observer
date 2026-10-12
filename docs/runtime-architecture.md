# Runtime architecture

Updated 2026-10-12. Snap and Starship select Observer 0.6.0a7 / Tmux Plus
0.12.0a7, with Mesh SDK/shared CLI 0.1.0a15 and the Observer-owned cached
publisher factory. [Publisher integration](publisher-integration-plan.md) and the
[accepted artifact/managed evidence](evidence/2026-10-12-publisher-integration/README.md)
bind the separate source, package, resource and operational gates. This is the
current component overview. The [original architecture](architecture.md) and
[boundary design](component-boundaries.md) retain the extraction history.
[Managed operations](managed-operations.md) owns selection and recovery.

## Who owns what

| Component | Package or repository | Responsibility |
| --- | --- | --- |
| Native contract and collector | `tmux_observer.native`, `collector`, `attachment_collector` | Full session identities and bounded passive default-server metadata reads |
| Owner publisher | `tmux_observer.owner`, `delivery` | Fixed host scope, scheduled samples, independent receipts, snapshot/watch and passive refresh hints |
| Networking and catalog | [Mesh Plus](https://github.com/byebyebryan/mesh-plus) | Logical hosts/routes, reusable local/SSH state delivery, proof and recovery |
| Mesh profile, adapter and composition | `tmux_observer.mesh_profile`, `_mesh_source`, `mesh_publisher`, `tmux_observer_client.mesh_fleet` | Pure native projection, checked cached acquisition, public Mesh publisher construction and guarded owner composition and existing Fleet v1 facade |
| Desktop association | `tmux_observer_client.desktop`, local bindings and desktop adapters | Endpoint-local Niri/terminal/process evidence joined to accepted native inputs |
| Prepared consumer facade | `tmux_observer_client.public`, `contract` | Cached queries/watch, context identity, source freshness and bounded refresh tickets |
| Action client | `tmux_observer_actions.public`, `contract` | Independent route/target validation, native lifecycle, terminal launch and window actions |
| UI and legacy CLI | [Tmux Plus](https://github.com/byebyebryan/rofi-tmux-plus) | Labels, views, filter, ordering, remembered context, confirmation and Tmux Session v1 compatibility |

These responsibilities do not require a process or distribution for every row.
Observer ships three package roots: core, client/composition and actions.
Pure contracts can be consumed without importing their native, transport or action
implementations. Action imports do not enter passive core/read paths.

## Process topology

A host publishes its own default server through one owner service. A desktop
runs a separate context-scoped fleet service; its Mesh reader and desktop work
are components of that service. A headless owner needs neither a compositor
nor a fleet reader.

```mermaid
flowchart TB
    subgraph OwnerHost[Each owning host]
        T[Default tmux server] --> O[Observer owner publisher]
        O --> B[Owner-only Mesh adapter and bridge]
    end
    H[Mesh host catalog and selected routes] --> M
    B -->|Local IPC or reader-initiated SSH| M
    subgraph Desktop[Each viewing desktop]
        M[Mesh state reader] --> F[Observer fleet coordinator]
        N[Niri and terminal/process evidence] --> D[Desktop association]
        F -->|Accepted owner inputs| D
        D -->|Independent receipts| F
        F -->|Private cached IPC and watch| U[Tmux Plus and other clients]
    end
    U -->|Explicit request| A[Observer action client]
    A -->|Independent local or routed validation| T
```

Remote state exports only owner facts. It never exports another desktop's fleet
or viewer state. Multiple local clients share the fleet service's collection and
transport; separate desktops retain independent views. No reverse desktop
connection or cross-host fleet replication is involved.

Observer's cached source owns Service v1 status/watch admission, fixed host/UID/
request/clock/order checks and operation cleanup. Its resource-free public factory
supplies that source and the pure Tmux profile to Mesh's generic `CachedPublisher`.
Mesh owns copied publication, canonical digest, original receipt leases and
nonce proof. The installed launcher injects the same static lazy factory for
fixed SSH dispatch. Agent factory/reference selection is independent of Tmux;
its subsequent a20 publisher adoption retains the Tmux factory in the shared map.

The selected fleet uses Mesh's public configured reader and pure admission guard.
Observer retains native semantics, complete identities, original source receipts,
historical rows and the Fleet v1 projection. Loss, gaps or scope replacement
revoke positive facts until guarded current state returns.

## Three paths with different guarantees

| Path | Interface | What happens |
| --- | --- | --- |
| Explicit fresh read | `collect`; client `snapshot --access direct`; Plus `inventory` | Bounded native reads, with explicit fresh fleet composition where requested |
| Prepared read | Owner snapshot/watch; client `snapshot --access cached` and watch | Reads already published state; starts no service, collection or upstream connection in the UI client |
| Explicit action | `tmux_observer_actions.public`; Plus lifecycle CLI/picker intent | Revalidates the selected route and exact target independently before dispatch |

Explicit refresh is a fourth, narrow control operation: it hints bounded passive
collection and returns an incarnation-bound ticket. Mesh's frozen state surface
has snapshot, proof and subscribe; it has no refresh or lifecycle capability.
Observer therefore keeps refresh on a separate bounded owner control path.
Fresh inventory and action routing also retain their independent accepted paths.
See the [Mesh integration ledger](mesh-integration.md#scope-and-decisions).

The generic fleet command and packaged unit default to the `legacy` backend.
Current managed controls explicitly select `mesh` and source `tmux_default`.
A failed Mesh backend never silently chooses legacy or direct collection.
The prior Observer/Plus a6 pair, Mesh a13 reader and a10 shared CLI provide the
recorded paired rollback baseline; older SDK roots remain available. Legacy remains an explicitly
selectable backend.

## Identity, clocks and uncertainty

The complete target is `(hostId, serverGeneration, sessionId, createdAt)`.
A rename preserves identity. A replacement server or reused session ID does not.
Names, titles, paths and PIDs are evidence rather than replacement identities.

Owner facts, native attachment associations, desktop observations and transport
health have separate provenance and leases. A heartbeat or cached delivery
renews no source fact. Cross-host boot clocks are not directly comparable; Mesh
carries conservative remote freshness proof, which Observer validates before
projecting current native facts.

Scheduled native observation remains polling, normally every two seconds with
ten-second leases. Subscription push improves delivery; it does not introduce a
tmux control client or native event source. Stable local desktop associations can
be retained while their independent native inputs remain current; their original
discovery time is preserved and display confidence remains qualified.

A complete-empty sample can establish absence. A failed or partial sample cannot
prove that an omitted session was removed. Unknown, unsupported, stale, failed
and warming states remain visible. Retained metadata is useful for diagnosis and
All/host views; it supplies no current attachment or action authority.

## Contracts and safety

[Wire v1](wire-v1.md) defines Observation, Service and Fleet layers.
[Boundary wire v1](boundary-wire-v1.md) adds native attachments, desktop association,
local bindings and explicit actions. [Tmux Session v1](https://github.com/byebyebryan/rofi-tmux-plus/blob/main/docs/TMUX_SESSION_V1.md)
remains the public Plus compatibility facade.

The core publishes metadata only. It does not collect pane contents, prompts,
raw environments, credentials or action handles. It never creates a server/session,
attaches a client, installs hooks or repairs tmux configuration. Service lifetime
does not keep a session alive.

Actions separately validate native identity, route and operation-specific guards.
A terminal-spawn result is not proof of completed remote attachment. An uncertain
dispatch is surfaced once and never automatically retried. Viewer presence is a
display observation, not a verified focus/close handle or provider lifecycle authority.

## Acceptance and remaining work

The [current publisher evidence](evidence/2026-10-12-publisher-integration/README.md) records
independent source, exact package/native, headless picker, ordinary two-host
resource, declared capacity, installed recovery and paired rollback gates.
The a15 ten-minute resource gate covers headless cached delivery; it does not
measure desktop/viewer work. Earlier desktop-inclusive measurements retain their
own artifact scope. Snap/Starship recorded CPU is 4.580%/2.751% against 5%;
fleet/associated-bridge RSS is 83.621/82.828 MiB against 96 MiB, and owner RSS
is 22.641/24.895 MiB against 64 MiB. Future changes need measured comparison.
The capacity profile uses sixteen synthetic logical owners on two physical hosts;
fifteen actual SSH links and thirty-two readers pass the 250 ms cached RPC gate.
Its conservative combined sampled peak is 693.383 MiB against 768 MiB. It does
not establish native truth on sixteen physical hosts or a capacity CPU soak.
RSS is sampled and Mesh byte/proof counters remain unmeasured.

Observer-owned cached publication is implemented and selected through Mesh's
public a15 helper and trusted factory seam. The
[integration plan](publisher-integration-plan.md) records completed I1-I5 and
R1-R2 checkpoints, including local/fixed-SSH publication, old/new compatibility,
exact artifacts/resources, public releases and managed recovery/paired rollback.
The legacy `TmuxMeshCodec` keeps its pure reference-codec compatibility; the
dedicated runtime publisher factory imports no reference adapter. The
[feasibility review](publisher-extraction-review.md) preserves the earlier study
and its original acceptance limits.

Optional native control-mode events need an independent passivity and benefit
gate. Physical sleep/wake and graphical checks for the Mesh wiring releases
remain outside their accepted scope. Use the [documentation index](README.md)
to find each contract, operating guide and historical evidence record.
