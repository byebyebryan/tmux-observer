# Mesh SDK adoption checkpoints

Implementation follows the [reviewed integration plan](mesh-sdk-integration-plan.md)
and its separately recorded feasibility experiments. The selected managed tuple
remains Mesh a10 / Observer a5 / Plus a5 until artifact and rollout acceptance.

## Pure profile and reviewed dependency

Observer now supplies `TmuxMeshProfile` and immutable `TmuxMeshStateCodec` through
the optional `tmux_observer.mesh_profile` module. Native validation uses the
supported `native` and `delivery` facades. Projection preserves complete
identities, original Service v1 receipts, warming/null and complete-empty state,
and historical records after source failure. Projection and reconstruction own
their mutable data. Callbacks perform no file, process or socket I/O.

The final source and CI dependency is Mesh **0.1.0a13**, commit
`d9cdac4ba6314430c3c8eb4d948a9d697c90b411`. The first profile/reader checkpoint
used released a11. This producer's Mesh worker accepts only the reviewed a13
SDK artifact and keeps the library authority as its default. Older local
SDKs require the corresponding prior Observer artifact; a10 remote bridge
compatibility is a separate installed checkpoint. SDK interface 1 does not
automatically admit future artifacts.

`TmuxMeshCodec` retains full direct Delivery proof admission and
`TmuxMeshAdapter` retains cached publication. The new bound codec is a Reader
hook: Mesh compulsorily checks envelope, proof, receipts and leases, then invokes
`inspect_native` for domain admission. Its binding callback avoids repeating
the native validation already required by the SDK.

The source gate passes **398 tests**, contracts, formatting and lint. The
separate Mesh gate passes **19 tests**, including six pinned frozen Read examples,
18 a10-oracle effective selections, adversarial proof/receipt rejection, callback
purity, optional import isolation and the existing owned native/SSH case.
[The checkpoint report](evidence/2026-10-11-mesh-sdk-adoption/profile-source.json)
binds the tested source files. This checkpoint has not yet wired the profile
through the fleet worker, frozen a new wheel or accepted managed selection.

## Explicit reader integration

The fleet worker now supplies the same owner profile to the public SDK's
configured reader and stream guard. Native validation, Fleet v1 projection,
refresh binding, route reporting and owned shutdown retain their existing paths.
The cached publisher adapter remains the accepted reference implementation.

The source gate passes 398 tests. The Mesh gate passes **20 tests**, including
configured local polling/watch, disconnect revocation and cleanup. Every
existing fleet case and the real-tmux/SSH passivity, refresh, restart and empty
case run with implicit `ReferenceProfile` construction forbidden. Rotation,
authority loss and refresh gap revocation recover through the explicit profile.
[The reader report](evidence/2026-10-11-mesh-sdk-adoption/reader-source.json)
binds these source inputs. Installed artifact and resource acceptance follow.

## Headless operations and mixed-version acceptance

The operations tool now accepts an explicit owner-only scope. It rejects an
active desktop or captured fleet, checks current owner/attachment bindings and
complete native identities, and restarts only the owner during recovery. Capture
and paired rollback retain their scope and staged payload/control guarantees.
The source gate passes **404 tests**, including six added topology, evidence,
recovery and rollback cases. Read-only verification of Snap's selected a10/a5/a5
installation passes exact payload/control checks, current owner evidence, fresh
CLI inventory and preserved native generation/references.

The installed Mesh gate also supports an explicit isolated bridge interpreter.
The frozen a6 candidate with a11 passes all 20 cases against an installed
a10/Observer-a5 SSH bridge. This is mixed-version package/native evidence,
separate from managed adoption. Its ten-minute headless cached-delivery resource
gate passes on both physical hosts: Snap 4.05% CPU, Starship 2.60%, and both within
the unchanged owner/fleet memory ceilings. Disposable services clean up while
ordinary native generations, references and hooks survive. These a11 measurements
remain evidence for their exact candidate; a newer final SDK needs fresh gates.

## Released a13 conformance checkpoint

Mesh published a13 during implementation. Its SDK API, state/view, Reader,
Client, Bridge, transport and frozen contract bytes match the reviewed a11 input.
The additions are opt-in conformance and diagnostics, with compatible CLI commands.
The downloaded 107,803-byte wheel matches SHA-256
`62b42bc76e7d79d95d89c41ee6f73c5e0169d24e2f1ac911c151c13f1f2b6f07`.
[The exact input tuple](evidence/2026-10-11-mesh-sdk-adoption/mesh-a13-inputs.json)
retains the previously reviewed Python 3.14 dependency wheels.

The source gate passes 404 tests; the Mesh gate passes **24 tests**. The portable
kit exercises six independent profile cases, ten owned IPC/remote-proof update,
restart and retirement cases, and one owned actual SSH case. A profile dropping
required receipts is rejected by the independent oracle. These supplement the
existing native passivity, identity, refresh and receipt checks; fixture publisher
conformance does not certify deployment of an extracted owner adapter.
