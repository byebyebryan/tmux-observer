# Cached Mesh integration

Mesh owns configured host authority and cached state delivery. Tmux Observer
owns passive native collection, local owner publication, prepared fleet/desktop
composition and independent refresh/action validation. See
[runtime architecture](runtime-architecture.md).

## Prerequisites

Use a compatible Host Mesh authority, the selected Mesh SDK/runtime dependencies,
and an already running owner on each participating host. Each source exports
only its own host's metadata; it does not export a previously aggregated fleet.
Installation/configuration does not start the owner or fleet service.

## Current configuration

Merge an entry like this into the existing private Mesh source configuration
on the owner host. Preserve other sources and mode 0600; this is an excerpt:

```toml
version = 1
host = "workstation"
[sources.tmux_default]
domain = "tmux"
socket = "/run/user/1000/tmux-observer/owner.sock"
```

Use your configured logical host, actual UID and owner runtime path.
The prepared fleet backend must be selected explicitly:

```ini
[Service]
Environment=TMUX_OBSERVER_TRANSPORT=mesh
Environment=TMUX_OBSERVER_MESH_SOURCE=tmux_default
```

The generic packaged unit/CLI default remains legacy; a managed override selects
Mesh. Capture/start the desktop context after the owner is ready as described
in [service contexts](service-contexts.md). Cached clients never perform startup.

## Failure and authority

Admit owner outcomes through the pure profile guard before projecting Fleet v1.
Keep native, desktop and association clocks separate. Partial/unavailable
evidence cannot prove removal. Catalog replacement cancels old children and
revokes joins until a fresh guarded baseline exists. Config failure revokes
current state without switching to direct collection or another backend.

Mesh snapshot/proof/subscribe capabilities supply no action or refresh authority.
Explicit passive refresh retains its bounded separate control path. Fresh
inventory and guarded actions remain independent operations.

## Selection and evidence

The [managed operations guide](managed-operations.md) and deployment owner record
the independently pinned Observer/Plus/Tmux-Mesh cohort, source factories and
rollback inputs. Generic shared CLI and Agent roles retain separate selections.
Retired Agent active-only hosting must not be recreated from old examples.

The [2026-10-20 full-view receipt](evidence/2026-10-20-mesh-a24-full-view/README.md)
records its installed/recovery scope; the later
[public-delivery receipt](evidence/2026-10-23-public-delivery/README.md)
records preparation and public supply inputs. No optional feed/delta selection
follows from source support. The [earlier migration ledger](history/design/mesh-integration-before-20261024.md)
preserves previous tuples, resource failures and rollout commands.

<a id="candidate-rollout"></a>

The [earlier candidate rollout](history/design/mesh-integration-before-20261024.md#candidate-rollout)
retains the instructions referenced by older immutable receipts.
