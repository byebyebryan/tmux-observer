# Mesh state delivery integration

Started 2026-10-09. The user authorized the migration goal loop after review of
Mesh Plus's [handoff](https://github.com/byebyebryan/mesh-plus/blob/fd40916/docs/handoff.md)
and frozen state boundary. This ledger owns the candidate implementation and
acceptance. Published artifacts and managed selection retain their earlier
evidence until separately selected.

## Scope and decisions

- Mesh owns catalog authority and reusable cached state transport. Observer's
  native collector, owner schedule, source receipts and local attachment profile
  retain their authority. Agent Observer is a reference, not an edit target.
- One Mesh reader runs within each existing desktop fleet service. Local cached
  clients retain their 250 ms deadline and never establish upstream connections.
- The coordinator retains Fleet v1, desktop context/bindings, historical rows,
  bounded refresh tickets and independent action semantics. Mesh owner outcomes
  are admitted through its pure guard before compatibility projection.
- An unavailable source revokes current facts immediately; it does not establish
  removal. Complete owner inventories and catalog removal remain authoritative.
- Mesh's frozen capabilities are snapshot, proof and subscribe. Explicit owner
  refresh stays on a separately bounded legacy control path during this delivery.
  Fresh inventory and actions retain their accepted explicit paths. No control
  capability or wire lock is changed implicitly.
- Catalog/watch replacement cancels old children, revokes old joins, resolves a
  fresh ordered catalog and requires a new guarded watch before positives return.
- The Mesh backend is explicitly selected; failure never falls back silently.
  The legacy backend remains available for candidate comparison and rollback.
- Native two-second sampling, ten-second leases, separate desktop/association
  clocks and original source deadlines remain fixed. Normal/capacity memory,
  CPU, native passivity, graphical and installed gates remain independent.

## Checkpoints

| Gate | Result | State |
| --- | --- | --- |
| M0 | Reviewed scope, exact starting tuple and migration boundaries | Complete |
| M1 | Cached Tmux adapter, guarded Mesh-to-Fleet projection and independent fixtures | Source/native pass |
| M2 | Shared fleet Mesh reader, catalog recovery and bounded refresh compatibility | Source/native pass |
| M3 | Full source and isolated exact-package acceptance, public facade parity | Source pass; package pending |
| M4 | Owned native/SSH, resource/capacity and applicable Snap graphical acceptance | Owned native pass; remaining gates pending |
| M5 | Exact reviewable rollout, dependency/launcher/source configuration and rollback | Pending |

Starting source: Observer `128f7f8`, Tmux Plus `5105eae`, Mesh `fd40916`, SSH Plus
`e01f89c`. Observer/Plus's accepted runtime is 0.5.0a1 / 0.11.0a1. Mesh source is
the unreleased 0.1.0a2 candidate; deployed catalog authority remains 0.1.0a1.
The installed authority does not include a public Mesh bridge launcher or prove
delivery dependency availability. Those are candidate packaging/rollout inputs.
Mesh's sibling checkout subsequently advanced to a3 diagnostics while this work
ran. It was preserved. This candidate deliberately keeps the reviewed a2 commit
in an isolated package environment; a3 requires an independently selected tuple.

## Acceptance

M1 checks lossless native reconstruction, full identities, original receipts,
local/remote clocks, partial delivery, warming/complete-empty distinction, source
failure, source replacement, stale retained rows, route binding and invalid frames.
Pure prepared imports exclude collectors, transport loops and action execution.

M2 checks one source subscription per selected host/context, bounded event
handoff, independent host recovery, catalog failure/replacement, scope epochs,
stop/owned-child cleanup, refresh coalescing and post-request sample completion.
Desktop/binding input invalidation remains independent of receipt-only renewal.

M3 runs `uv run --extra dev ./scripts/check`, the Mesh standalone gate and the
separate integration suite with the exact Mesh candidate. Isolated wheels must
match their source/data manifests; consumer pins identify complete package roots.
Fresh Session v1 and cached Fleet v1 retain distinct semantics and strict bounds.

M4 records candidate-specific native evidence rather than reusing old results.
Use disposable sessions, sockets, preferences and owned SSH endpoints. Native
rosters, generations, client counts, hooks, options and ordinary session lifetime
survive. Resource gates include all bridge/worker children and preserve existing
5 percent CPU and 96/768 MiB fleet ceilings. Snap graphical input preserves
ordinary focus. Physical suspend and Starship foreground acceptance remain
outside this loop's acceptance scope.

M5 prepares exact artifacts and scoped managed controls only after candidate
gates pass. Preserve unrelated source/live edits, private history and ordinary
services. Recovery and rollback are serialized across endpoints. Publication or
live promotion follows the user's concrete authorization for the reviewed tuple.

## Candidate implementation

`tmux_observer.mesh` exposes the Tmux adapter/codec over Mesh's reference cached
adapter. `mesh_fleet.MeshFleetPublisher` keeps the prepared fleet endpoint,
desktop jobs and ticket store. Its worker owns one guarded replacement stream,
an in-process local Mesh bridge, and configured remote Mesh SSH bridges. The
handoff is bounded to eight replacements / 16 MiB. Native retained documents
reserve the existing 16 MiB pool before copying. Reconnect, catalog loss, clock
jump and route/publisher replacement revoke positive validity and old tickets.

The coordinator reconstructs and checks original native records before retaining
them. Fleet v1 requires proof remaining time to match its source header encoding.
For remote compatibility it re-encodes only that header at Mesh's cached bridge
encoding in the **source** clock. Sample time, acceptance, expiry and the retained
native frame remain unchanged. Queue delay consumes the translated Mesh lease.

An idle control facade holds no native watch or process. Only explicit refresh
or ticket lookup launches a bounded one-shot native request, with at most four
workers and one queued operation per host. Control replies never update owner
facts. A completed native child still waits for Mesh-confirmed post-request
attempt/proof before completing its fleet ticket. CLI request correlation is an
additive option; no public schema or Mesh lock changed.

The regular stdlib source gate runs without the Mesh extra. Development resolves
that extra from immutable public Git revision `fd40916f2b0e5c9d2a3f8b51d0da02585894ddcb`.
The wheel declares optional `mesh-plus==0.1.0a2`; candidate/install workflows must
supply that exact wheel and its declared dependencies separately.

## Candidate rollout

The default remains `legacy`. Opt in only after the paired artifact and resource
gates accept the selected tuple. The concrete managed changes will include:

1. Select the exact Observer and pinned Tmux Plus wheels/bundles together.
   Select the a2 Mesh wheel plus exact JSON Schema/runtime dependency wheels for
   the endpoints' Python ABI. Hash all installed modules, schemas and dependency
   payloads. An authority-only a1 installation is insufficient.
2. Add the public `~/.local/bin/mesh-plus` launcher. Observer's managed client
   launcher must include the selected Mesh/dependency Python root; the existing
   wrapper exposes only Observer. The pure owner/direct/action launchers keep
   their independent entry paths.
3. Manage a private `~/.config/mesh-plus/sources.toml` on each endpoint, mode 0600:

   ```toml
   version = 1
   host = "snap" # "starship" on the other endpoint
   [sources.tmux_default]
   domain = "tmux"
   socket = "/run/user/1000/tmux-observer/owner.sock"
   ```

   Render the actual managed UID/runtime path; validate it against the already
   running fixed owner. Configuration and package installation start no service.
4. Select the packaged fleet unit and a reviewed managed drop-in:

   ```ini
   [Service]
   Environment=TMUX_OBSERVER_TRANSPORT=mesh
   Environment=TMUX_OBSERVER_MESH_SOURCE=tmux_default
   ```

   Discover each active context's exact fleet unit. Restart only that owned unit,
   one endpoint at a time. Prepared/fresh/native identity, viewer freshness,
   explicit refresh, separate disposable actions, reconnect and exact installed
   bytes must pass before selecting the second endpoint.
5. Exercise rollback by selecting `TMUX_OBSERVER_TRANSPORT=legacy` on the same
   candidate tuple and restarting one reader at a time. Full tuple rollback
   selects the previously accepted Observer 0.5.0a1 / Plus 0.11.0a1 and restores
   their previous fleet unit; Mesh authority a1 is its separate rollback input.
   Restore prior launcher/config bytes only after all new readers have stopped.

These instructions are a reviewable source plan, not an applied managed change.
Ordinary two-host desktop resources, capacity, installed selection/recovery and
serial paired rollback retain separate promotion gates. Physical suspend and
Starship foreground input remain excluded.
