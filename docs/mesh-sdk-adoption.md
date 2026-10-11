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

The source and CI dependency is Mesh **0.1.0a11**, commit
`9d570c59041832d177519fd634d26c56ed572e81`. This producer's Mesh worker accepts
that SDK artifact and keeps the library authority as its default. Older local
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
