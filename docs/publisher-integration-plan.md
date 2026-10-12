# Observer-owned cached publisher integration

2026-10-12. Implementation and exact producer acceptance are recorded in the
[publisher acceptance ledger](evidence/2026-10-12-publisher-integration/README.md).
Updated after the Mesh publisher handoff. This is the implementation
plan following the [completed feasibility study](publisher-extraction-plan.md)
and [review](publisher-extraction-review.md). The selected cohort is now Observer 0.6.0a7 / Plus 0.12.0a7 / Mesh reader SDK
and shared CLI 0.1.0a15. I1-I5 and R1-R2 pass their independent source, artifact,
compatibility, resource, public and managed gates. The prior a6/a13/a10 cohort
remains the independently verified paired rollback baseline.

## Accepted producer input

Mesh's upstream source and private-wheel publisher checkpoints are complete.
We do not need to implement another generic wrapper or copy its CLI.

| Input | Reviewed value |
| --- | --- |
| Runtime source | `c46262c0f0185244e96c79ea2036e4f57b2e4e1e` |
| Documentation/acceptance handoff | `de2ee3642501664e8b6ede4dc6d3cf5ff6ba4713` |
| Candidate SDK/CLI | Mesh Plus `0.1.0a15`, SDK interface 1 |
| Private wheel | `mesh_plus-0.1.0a15-py3-none-any.whl` |
| Wheel SHA-256 | `42b25045f8f89afda61e56525f443a189dcc6769637aee5bcab959f096527f0f` |
| Disposition | Accepted upstream input; identical public a15 wheel verified and selected by R2 |

The immutable [public API handoff](https://github.com/byebyebryan/mesh-plus/blob/de2ee3642501664e8b6ede4dc6d3cf5ff6ba4713/docs/publisher-api.md)
and [installed acceptance](https://github.com/byebyebryan/mesh-plus/blob/de2ee3642501664e8b6ede4dc6d3cf5ff6ba4713/docs/evidence/2026-10-11-publisher-factory/README.md)
own the producer evidence. Locally, the private wheel's digest and all 59
runtime/resource members were checked against the handoff source. The installed
publisher core suite was rerun on Python 3.14.8: nine tests passed, no skips;
that rerun excluded SSH, WSS, owner-native acquisition and resource/deployment gates.
Upstream separately records actual fixed SSH, mixed a10 and optional WSS acceptance.
Its native regression inputs are Tmux a5 / Agent a16, not our selected cohort.

Relative to the preceding a14 source, the lock and existing Read/Delivery/native/
WSS schemas, Reader, state and transport remain byte-identical. The publisher
surface is additive under SDK interface 1. WSS remains an independent networking
selection and is not enabled by this plan.

## Actual API and responsibilities

Import `CachedSource`, `CachedPublication` and `CachedPublisher` from
`mesh_plus.api`. The supported constructor is
`CachedPublisher(domain, host, source, native, *, profile)`. An explicit pure
profile is mandatory, and the native object must implement callable `snapshot`
and `watch` methods. `CachedSource` is a structural typing protocol.

- `snapshot()` asynchronously returns a checked cached native Service v1 frame.
- `watch()` returns an async iterator with `aclose()`, yielding the actual Mesh
  `CachedPublication(frame, epoch, barrier)` type. A locally copied DTO is invalid.
- Observer filters native heartbeats, owns UID/request/host/clock/order checks,
  reports loss/restart, and retires each operation's acquisition/read resources.
- Mesh owns copied frames/barriers, profile admission, full Delivery validation,
  canonical digest, original-receipt leases and proof construction. It admits the
  nonce before invoking a new native snapshot. Receiver nonce binding still applies.
- Receipt tracking covers consecutive admitted samples under one publisher/clock.
  Native sample ordering, including any component disappearance/reappearance,
  remains the source's obligation. Tmux retains its fixed required native receipt.

The supported CLI calls are `main(*, publisher_factories=None)` and
`configured_adapter(path, source, *, publisher_factories=None)`. Factories receive
`(host, source, socket)` after descriptor validation and construct publishers
synchronously without acquiring native resources. Factory maps are trusted
installed Python; selected failures never fall back. Omitted domains retain
the declared reference path. Catalog authority commands bypass state imports.

The stock console script still uses reference dispatch. Our trusted launcher
must explicitly inject the Observer factory for both local and remote hosting.
The remote command remains `mesh-plus bridge --source SOURCE --stdio`; the
source descriptor remains version 1 with host/domain/socket fields only.
There is no global source shutdown callback: snapshot/watch own every resource.

## Implementation checkpoints

Commit each reviewed checkpoint. A consumer defect reopens its owning producer
checkpoint; changing an artifact requires fresh evidence for its changed bytes.

| Checkpoint | Concrete work | Required acceptance |
| --- | --- | --- |
| I1 — Native source | Add `src/tmux_observer/_mesh_source.py` with checked cached status/watch acquisition and native stream guards. Use supported Mesh transport lifetime helpers and Observer's native/delivery facades; retain owner-local clock policy. | Request/host/UID/clock/initial sequence and later publisher/sequence/revision/time checks; status/watch only; heartbeat filtering; acquisition, validation and iterator cancellation cleanup; warming/stale/error/empty and receipt ordering remain explicit. |
| I2 — Owner factory and compatibility | Add `src/tmux_observer/mesh_publisher.py` exposing `make_publisher(host, source, socket)`, constructing the public Mesh helper with `TmuxMeshProfile`. Replace `TmuxMeshAdapter` reference inheritance while preserving `(host, path, source)` and the Bridge-compatible surface. Route `_mesh_worker` through the dedicated factory; update the exact dependency/revision/version guard to reviewed a15. | Owned publisher imports exclude Mesh reference adapters, collectors, desktop and actions. Construction opens no socket. Existing public facade constructors/validation and explicit Reader profile/guard behavior survive. No copied generic proof code, CLI rewriting or private Mesh state imports. |
| I3 — Native local and remote integration | Install a private trusted launcher using the same lazy factory map; run owned actual default-server namespaces and native owners through IPC and the fixed SSH command. Adapt fixtures that patch reference `ObserverAdapter.watch` to the Observer source/publication boundary. | Factory invocation on both paths; proof-after-nonce; exact native identities/receipts; update/outage/restart/empty/disconnect; forged proof and expiry rejection; repeated cancellation and teardown; hooks/options/attachments preserved. Keep independent refresh success, coalescing and gap assertions. |
| I4 — Exact Observer candidate | Freeze a committed-source Observer wheel against the accepted a15 wheel and reviewed dependencies; accept installed native/fleet behavior and capacity separately. | Source and Mesh gates, portable profile/network conformance, imported byte parity, mixed old/new matrix below, normal resource comparison on Snap and Starship and declared-capacity deadlines. Native metadata collection remains passive. |
| I5 — Plus candidate | Pin the accepted Observer artifact and reader input; freeze and verify the Plus candidate. | Source/package/headless Tmux Session v1 compatibility, refresh attribution and lifecycle validation. Preserve standalone/provider-neutral behavior. No new graphical gate for unchanged UI wiring. |
| R1 — Public artifacts | Confirm a public immutable Mesh release for the reviewed input before publishing dependent Observer/Plus packages or selecting managed download URLs. Coordinate exact reviewed publication where in scope. | Published wheel digest/runtime parity, coherent dependency metadata and immutable Observer/Plus artifacts. If public bytes differ from the private candidate, reopen the owning acceptance checkpoint. |
| R2 — Managed cohort | Select a versioned shared bridge and inject the static lazy Observer factory in the managed launcher. Preserve the intentionally omitted Agent reference branch and its independent producer/reader/bridge-facade selections. | Exact bytes and descriptors on each host; actual selected Agent cached snapshot/watch/recovery compatibility; owner/fleet readiness and restart recovery; headless consumer checks; paired rollback and reselection. |

The implemented `mesh_publisher.make_publisher` export is independent of the
optional legacy codec facade. Local and fixed-SSH publication pass with reference
integration imports forbidden; the installed capacity and resource launchers
explicitly inject this factory and record its use.

## Compatibility details that must survive

`TmuxMeshCodec.validate()` is a full Delivery validator. The bound
`TmuxMeshStateCodec.validate_bridge()` checks endpoint scope after Mesh's generic
admission; substituting it would weaken direct-client validation. Preserve the
supported legacy codec facade in this pass, separate from the new factory path.
Do not broaden this extraction into a codec/API rewrite.

The implemented grouped-refresh success fixture instruments the owned native
source/publication path and asserts actual publication acknowledgement. It uses
the existing two-second delivery budget; the independent delivered-attempt
attribution and negative coalescing/revocation checks remain. The
[acceptance record](evidence/2026-10-12-publisher-integration/README.md)
retains the controlled reproduction of the earlier fixture cutoff and the final
installed result. Production deadlines and packaged runtime bytes are unchanged.

Use the actual publisher helper rather than the study wrapper. Retain source
guards from the feasibility work only after production review; remove tracing,
fixture counters/environment selectors and copied CLI machinery. Cover both a
late admitted connection after cancellation and failure after admission before
guard construction completes.

| Matrix case | Outcome to prove |
| --- | --- |
| Existing a13 Reader + new a15 owner publisher | Frozen wire/profile interoperability with the explicit Observer profile. |
| New a15 Reader + old a10 reference bridge | Existing cached native delivery remains compatible. |
| New a15 CLI without injection + old Observer | Default reference behavior remains supported. |
| Injected tmux factory + missing/incompatible Observer | Explicit failure, no reference fallback. |
| Shared a15 bridge + selected Agent bridge facade/service | Separate Agent compatibility; do not substitute a sibling HEAD or assume its core and bridge facade versions match. |

## Resource and rollout limits

I1-I5 and R1-R2 are complete for the exact a7/a15 artifacts and their recorded
scopes. The checkpoint table retains the reviewed implementation requirements.
At the Tmux rollout, R2 preserved Agent's omitted reference branch. Its later,
independent a20 publisher adoption adds the Agent factory to the shared launcher;
[post-Agent Tmux revalidation](evidence/2026-10-12-publisher-integration/post-agent-compatibility.json)
checks the combined map without adopting Agent producer work here.

Use the [accepted a13 resource evidence](evidence/2026-10-11-mesh-sdk-adoption/README.md#final-frozen-producer-input)
as the measured baseline: Snap combined CPU 4.286% against 5%, approximately
83 MiB fleet-plus-bridge RSS against 96 MiB, owner RSS against 64 MiB, and a
600-second normal headless workload on each host. Preserve collection cadence,
topology and workload for comparison. The sixteen-owner capacity profile uses
synthetic logical owners on two physical hosts; it is not sixteen-host native
acceptance or a capacity CPU soak. Copy/projection costs need measurement.

Physical suspend, graphical/action behavior changes, WSS selection, native
control mode, events/replay, pooling and provider changes remain separate work.
The accepted a6/a13/a10 reference cohort remains the verified paired rollback
baseline. Its evidence is independent of the selected a7/a15 cohort.
