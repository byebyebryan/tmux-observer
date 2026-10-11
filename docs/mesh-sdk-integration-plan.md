# Tmux Observer integration with Mesh SDK v1

Integrate the released Mesh a11 SDK by supplying an Observer-owned pure Tmux
profile throughout configured reads and stream guards. Preserve the accepted
native contracts, Fleet v1 projection and separate refresh/action paths. Accept
the producer package before updating the Tmux Plus artifact pin or managed
selection. Retain the existing cached publisher adapter during this first
checkpoint; native adapter extraction has a separate endpoint review.

Status: preimplementation plan and feasibility validation, 2026-10-11. The
[research record](evidence/2026-10-11-mesh-sdk-research/README.md) establishes
feasibility with disposable experiments. It does not accept an implemented
Observer candidate or change the selected a10/a5/a5 deployment.

## Reviewed inputs

| Input | Exact checkpoint |
| --- | --- |
| Observer source and harness | `3de61eb7d5b3db7fdf4eb2f6207b9f6549935703` |
| Selected Observer wheel | 0.6.0a5; source `5d8b7234ba10920beb59bde35c2f79c73d382b25`; SHA-256 `958d2f5381d57f172294e35654e19c96770ccd38e7ef8421a23f3dcf00abe536` |
| Released Mesh SDK | 0.1.0a11; source `9d570c59041832d177519fd634d26c56ed572e81`; SHA-256 `9d3c2446b2391ab2271236804b4dfc03dfa5d29f2766d72b3d12086848b36359` |
| Mesh API and owner handoff | `17b8096beed20eeece3d0d86e2df655d1bc1f8ed` |
| Tmux Plus source | `3856a9b734c4d8cea100f0298b48c89bb4a19ac4`; pins the complete Observer a5 payload |
| Managed configuration | `62fba85`; `deployments/tmux-observer.json` selects Mesh a10 / Observer a5 / Plus a5 |

The [SDK specification](https://github.com/byebyebryan/mesh-plus/blob/17b8096beed20eeece3d0d86e2df655d1bc1f8ed/docs/sdk-api.md)
and [owner handoff](https://github.com/byebyebryan/mesh-plus/blob/17b8096beed20eeece3d0d86e2df655d1bc1f8ed/docs/sdk-owner-handoff.md)
define the additive Python interface. SDK interface 1, Mesh wire 1, the frozen
Tmux profile and Observation/Service/Fleet versions are separate identities.
No wire, schema, lock, authority ABI or capability change is required.

During validation, Mesh advanced to `d2af3c2` with a
[maintenance plan](https://github.com/byebyebryan/mesh-plus/blob/d2af3c2b09181af13e6ac1a7f4fbd2baf079a1a1/docs/sdk-maintenance-plan.md)
and began an a12 conformance kit. A captured draft of `mesh_plus.testing`
passes six independent Tmux oracle cases with this feasibility profile and
rejects an empty-receipt mutation in three cases. This is supplemental source
research, not a12 package acceptance. Mesh subsequently committed the kit at
`64173d5` and diagnostics at `e91f828`; a11 remains the latest published release
at the follow-up check. The SDK/profile/reader/guard source reviewed below is
unchanged by those commits. Adopt the opt-in profile, network and SSH suites
after their installed-wheel gate and immutable release pass, alongside Observer's
native acceptance. The a11 integration can proceed using the reviewed fixtures
without waiting for that tooling. Reconcile newer released inputs at the start
of implementation rather than pinning a moving HEAD.

## Ownership and integration points

Put the pure implementation in an optional `tmux_observer.mesh_profile` module.
It may import Mesh's documented SDK types and Observer's supported
`native`/`delivery` facades. Importing the ordinary native/core facade must remain
possible without Mesh installed. The profile imports no collector, owner service,
IPC client, desktop adapter, action implementation, Rofi or Agent package.

| Surface | Observer responsibility | Mesh responsibility |
| --- | --- | --- |
| `StateProfile.descriptor` | Use `descriptor("tmux")`; verify native protocol/version and frame limit match the supported facade | Check the reviewed schema identity and SDK descriptor |
| `bind(host, source)` | Return an immutable codec with fixed host, configured source and profile ID | Check endpoint and hello binding before native dispatch |
| `inspect_native(frame)` | Validate Service v1; preserve owner fields, ordered records, clock, publisher and original receipts | Check capacity, lossless roundtrip, scope and chronology |
| `restore_native(owner, records)` | Reconstruct the exact checked Service v1 frame | Bind reconstruction to digest/proof and aggregate projection |
| Record callbacks | Preserve `(hostId, serverGeneration, sessionId, createdAt)` and existing eligibility | Check uniqueness, host order, required evidence and effective expiry |
| `validate_response` / `validate_bridge` | Supply pure domain checks through the bound profile | Retain compulsory envelope, proof, receipt, health and lease checks |

The configured source `tmux_default` is an endpoint selector. The normalized
native receipt key remains `("default", "native")`. Reconstructed native frames
use the SDK's `default` binding. These names must not be collapsed or substituted.
Map a ready owner receipt to current and every nonready receipt to stale exactly
as the accepted reference profile does, retaining the full original Service v1
receipt and error for the Fleet projection. Warming remains null; a complete
empty roster remains an accepted empty roster. Eligibility adds no activity,
attachment or desktop inference.

Use `mesh_plus.api` for profile types, configured readers and guards. Keep the
documented catalog, library authority and IPC transport surfaces where needed;
they are not all exported by that facade. Pass the same profile instance to
`configured_reader`, `ReadGuard` and any SDK validation, reconstruction or current
selection helper. Direct endpoints must carry their explicit bound codec.

| Current file | Planned change |
| --- | --- |
| `src/tmux_observer/mesh_profile.py` | New pure structural profile and immutable bound codec; explicit exports and import isolation |
| `src/tmux_observer/mesh.py` | Expose the new profile while preserving `TmuxMeshCodec` and `TmuxMeshAdapter` compatibility constructors |
| `src/tmux_observer_client/_mesh_worker.py` | Import supported SDK entry points, inject the profile into configured reads and guards, and admit the reviewed a11 artifact |
| `pyproject.toml`, `uv.lock` | Pin a11 and its exact released source; keep Mesh optional |
| `tests`, `tests_mesh`, CI | Add owner-profile conformance, differential fixtures and installed integration coverage |

Both version-dependent branches in MeshWorker need review. Admitting a11 while
omitting it from the library-authority branch would change the default authority
path and costs. Preserve the explicit library authority, route reporting policy,
captured catalog and owned close behavior. SDK interface 1 alone must not admit
untested future artifacts.

`TmuxMeshCodec` currently supplies full validation to direct Delivery clients.
Preserve that public behavior. A Reader-bound profile callback that validates
native semantics is not a standalone replacement for all Mesh proof validation;
generic `Client` supports ordinary callbacks without granting fleet validity.
Keep compatibility clients on their existing facade until a separately accepted
equivalent public admission path exists.

`MeshOwnerState` retains its independent native validation, historical storage,
local UID/clock checks and Fleet v1 receipt translation. `OwnerControl` retains
refresh binding and deadline checks. Neither path gains action authority from
the new profile. Core sampling, desktop joins, UI behavior and lifecycle logic
keep their existing contracts and cadence.

## Implementation sequence and acceptance

| Checkpoint | Work | Exit evidence |
| --- | --- | --- |
| 0 Profile semantics | Freeze the callback mapping above and owner-native fixtures; retain current artifact and SDK compatibility as separate baselines | Reviewed complete identities, warming/empty/failed states, original receipt mapping, strict parsing and exact reconstruction |
| 1 Pure profile and SDK dependency | Pin the reviewed SDK, update both admission/authority branches and implement the optional owner module without reference-profile inheritance; preserve old public adapter/codec APIs | Existing source/Mesh gates plus import isolation, callback purity, bounds, immutable binding, no alias leakage and adversarial native frames |
| 2 Reader integration | Thread the profile through configured IPC/SSH, guards and view helpers | Source gate, differential parity, configured poll/watch, catalog replacement, gaps/expiry, rotation, repeated cancellation and refresh success/revocation |
| 3 Producer artifact | Freeze a fresh Observer prerelease and use its exact bytes for installed gates | Wheel coverage/import origins, existing eight Mesh tests plus explicit-profile cases, owned native/SSH passivity/restart/empty/cleanup, unchanged resource ceilings and foreground deadlines |
| 4 Consumer selection | Update Plus's complete Observer module/wheel pin after producer acceptance; synchronize active selection/setup docs | Tmux Session v1 and lifecycle parity, installed native bundle verification, headless picker frames/callbacks and preserved preferences/history |
| 5 Managed adoption | Prepare exact versioned SDK/package roots, controls, selection and paired rollback | Per-host installed bytes, cached freshness, kernel/interpreter identity, recovery, preserved native generation/references/hooks, rollback and reselection |

Checkpoints 1 and 2 can advance without Agent Observer or Plus checkout changes.
Checkpoint 4 is an artifact compatibility update, with the existing presentation
and action contracts. Plus checks all Observer Python members and hashes, so
adding a pure module still requires its pin to advance before managed selection.

Run `uv run --extra dev ./scripts/check` for the source gate and the separately
pinned Mesh integration gate. Install the frozen candidate in a fresh environment
and run `scripts/check-mesh --installed --artifact ...` for package integration.
Keep normal CI independent of sibling checkout HEADs; use pinned SDK wheels and
owner-controlled fixtures. Preserve all normative bundles and packaged schemas.

Mesh's candidate [diagnostics interface](https://github.com/byebyebryan/mesh-plus/blob/e91f828b4a3480b27091180ea795e069fd5a2036/docs/sdk-diagnostics.md)
can supplement operations evidence after package acceptance. `doctor --sdk`
reports offline package/descriptor facts; `assess` reports one cached evidence
sample and retires its owned connections. Pass the owner profile to Python
assessment helpers. Acquisition success is separate from current rows, and a
sample retains no authority after cleanup. Neither diagnostic replaces native
validation, continuously guarded delivery or the managed recovery gate.

Measure source/native validation cost and the normal cached-delivery resource
scope before promotion. Snap's accepted a10 fixture CPU result was 4.31% against
the unchanged 5% ceiling; profile copying and repeated validation need measurement.
The research prototype's copies and in-memory hooks are not production choices
or resource acceptance. No resource limit or timing budget is relaxed.

Snap's accepted topology has an owner without a managed desktop/Fleet context;
Starship has a captured desktop/fleet. The operations tool currently requires a
desktop for every host. Add an explicit accepted headless verification/recovery/
capture/rollback scope before using that tool for checkpoint 5. Preserve native
server generation and complete references in that evidence. Do not enable a
desktop merely to satisfy a checker.

The mixed-version native experiment supports testing an a11 reader against an
a10 SSH bridge. Start with private/versioned reader SDK selection while retaining
the reviewed shared bridge CLI if the installed candidate passes that matrix.
Changing the shared Mesh CLI/source controls additionally requires Agent delivery
verification; it does not require editing Agent's collector, writer or consumer.

Graphical input/focus and physical suspend remain separate optional acceptance
scopes for this networking-only pass. Required headless, owned native/SSH,
simulated recovery, package/resource and managed recovery checks do not depend
on waking Snap or modifying the picker UI.

## Cached publisher extraction after SDK adoption

The initial profile checkpoint retains `TmuxMeshAdapter`'s reference implementation.
Mesh's `configured_adapter` still constructs `ObserverAdapter` for `mesh-plus
bridge --source tmux_default`; local adapter extraction alone would not replace
that remote path. The current source descriptor accepts only domain/socket and
the SSH transport fixes the bridge command.

Before extracting native IPC adaptation, review how the fixed Mesh CLI reaches
an Observer-owned publisher through installed trusted code, preserving the source
descriptor and remote command contracts. Keep arbitrary module discovery,
wire-selected executable paths and new capabilities out of that design. Reopen
the Mesh producer checkpoint if the supported factory seam is insufficient.

The later adapter must preserve status/watch validation, UID and clock binding,
stream ordering, sample-counter/lease checks and a checked cached reply acquired
after proof nonce arrival. It closes its owned iterators under cancellation and
starts no native collection. Accept that extraction against local and remote
publisher paths independently before claiming the reference integration retired.

## Preimplementation disposition

The released SDK is sufficient for the profile and reader checkpoint. Six Tmux
projections and 18 effective selections match a10; explicit-profile fleet and
mixed-version owned SSH experiments pass. No SDK blocker was found for that
bounded integration. Native publisher extraction still needs the fixed CLI
factory review above. Start implementation with checkpoints 0 and 1 after the
plan is accepted; package publication and live selection retain separate gates.
