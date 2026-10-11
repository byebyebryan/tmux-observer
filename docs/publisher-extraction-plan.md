# Cached publisher extraction: design and feasibility

2026-10-11. This pass covers documentation, a proposed interface, isolated
feasibility and an implementation decision. It does not select new packages or
replace the accepted Observer a6 / Plus a6 / reader SDK a13 / bridge CLI a10 cohort.
The [completed SDK adoption](mesh-sdk-adoption.md) remains accepted.

## Problem and intended boundary

Observer owns its pure native profile and explicit Reader/ReadGuard bindings.
`TmuxMeshAdapter` still subclasses Mesh's reference `ObserverAdapter`, which
implements native cached IPC as well as generic proof envelopes. Mesh's fixed
CLI constructs the same reference adapter for remote publication. Moving only
the local class would leave the remote path unchanged.

The intended extraction gives Observer native cached-source policy and gives
Mesh reusable publisher/proof construction. It preserves Service v1, Fleet v1,
Tmux Session v1, configured host/source/socket binding and the fixed remote
command `mesh-plus bridge --source SOURCE --stdio`. Reads start no collection;
refresh, actions, desktop association and UI policy keep their existing paths.

| Owner | Proposed responsibility |
| --- | --- |
| Observer | Cached Service v1 status/watch requests, native parser, UID/clock/request binding, native sequence/revision/incarnation checks, native publication barrier |
| Mesh | Generic profile admission, candidate/proof construction, original receipt counter/expiry checks, Bridge delivery and owned connection lifetime |
| Trusted entry point | Explicit static factory mapping for reviewed installed code |
| Configuration | Existing same-user private descriptor: version, host, configured source, domain and socket |

## Proposed additive interfaces

These names are design candidates, not exports in released SDK a13.

`CachedPublication(frame, epoch, barrier)` carries a native cached frame and its
owner-defined stream barrier. `CachedSource` has async `snapshot()` and async
`watch()` yielding those publications. Observer's `TmuxCachedSource(host, socket)`
supplies that interface without inheriting a Mesh reference integration.

Mesh's proposed `CachedPublisher(domain, host, source, native, profile=...)`
implements the existing Bridge adapter surface. It binds the explicit pure
profile, validates lossless native state, preserves complete receipts and emits
the unchanged Delivery payload. `proof({nonce})` validates the nonce before
calling a new native cached `snapshot()`; retained watch data cannot prove owner
liveness. Equal accepted counters cannot acquire a new expiry within an owner
publisher/clock binding. Publisher replacement resets that binding.
Published frames and barriers are owned copies; a source retaining its input
cannot mutate queued evidence. Failed admission updates no accepted counters.

The proposed CLI hook is `main(*, publisher_factories=None)`, threaded to
`configured_adapter(..., publisher_factories=None)`. A trusted installed caller
may supply a captured mapping such as `{"tmux": make_tmux_publisher}`. A factory
receives `(host, source, socket)` after existing descriptor admission. Keys are
the fixed supported domains; callbacks and adapter binding are checked before
serving. There is no CLI argument, config field, remote module name or entry-point
discovery mechanism for choosing code.

Default calls preserve the reference integration. A domain omitted from an
explicit mapping retains that declared compatibility path. A supplied factory
that cannot load, raises or returns a wrong binding fails; it never falls back to
the reference adapter. The factory mapping is copied at entry so later caller
mutation cannot change one invocation's code selection.
The trusted entry point imports its factory lazily when the selected publisher
is constructed. Catalog-only commands retain the stdlib authority fast path.

The explicit new entry point requires its paired Observer factory. Existing
launchers retain reference publication until a separately accepted managed change.
The shared bridge environment affects Agent delivery too: changing it requires
Agent cached-delivery compatibility evidence even when Agent source is untouched.

## Alternatives reviewed

| Option | Disposition |
| --- | --- |
| Replace Observer's local subclass only | Insufficient: fixed remote CLI still constructs the reference adapter. |
| Copy native and generic proof code wholesale into Observer | Reject: generic Delivery logic would acquire a second owner and drift risk. |
| Automatic installed-module discovery or fallback after factory failure | Reject: obscures selected implementation and failure semantics. |
| Wire/config-selected module, executable or arbitrary profile | Reject: expands authority and the source descriptor contract. |
| Change default CLI dispatch to require a new Observer factory | Reject for this additive design: breaks older producer installations. |
| Add trusted Python factory injection and a generic Mesh publisher | Preferred feasibility candidate: preserves default CLI compatibility and explicit adoption. |
| Retain reference integration | Supported fallback decision if extraction cost or feasibility is unfavorable; not a runtime defect. |

## Checkpoints in this pass

1. Synchronize current Observer/Plus documentation and preserve historical bodies.
   Commit after checking links, selected tuple, whitespace and scope attribution.
2. Record this proposal and reviewed immutable inputs. Keep prototype modules
   under `studies/publisher/`, outside ordinary package discovery and entry points.
3. Exercise owner-native semantics and the proposed factory through owned IPC
   and the real fixed SSH command. Use released a6/a13 inputs, an independently
   pinned old bridge, isolated owner sockets and disposable default-server namespaces.
4. Record exact code/input digests, explicit passes/failures/skips, cleanup and
   limitations. Review the design against the evidence; produce a bounded backlog.

The prototype may load a copied a13 CLI with only the proposed injection seam.
It must identify those changed bytes separately from the released SDK. No
monkeypatch of installed CLI state establishes supported API acceptance. A copied
CLI experiment proves feasibility only; Mesh must implement and independently
accept its own public seam before Observer production adoption.

## Feasibility acceptance

| Area | Required evidence |
| --- | --- |
| Ownership | Mesh-side generic wrapper imports no native collector, desktop, action or reference adapter; Observer source uses pure native/delivery facades. |
| Factory | IPC and actual fixed SSH CLI invoke the intended owner factory; default reference path remains available; supplied factory failure never falls back. |
| Admission | Wrong host/source/UID/clock/request, malformed native frame, stream order and incarnation conflicts reject; complete identities remain intact. |
| Proof | Cached read occurs after nonce admission; digest/nonce/receipt forgery rejects; expiry and equal-counter lease renewal cannot grant current rows. |
| State | Warming, complete-empty, historical failure and unsupported/partial semantics remain distinct. |
| Recovery | Owner update/restart/outage, new stream and disconnect revoke/recover correctly; repeated cancellation retires owned iterators and channels. |
| Native passivity | Owned session generation/references/hooks/options/attachment counts survive read traffic; only fixture resources are created/stopped. |
| Compatibility | Pinned reader/current profile can read the old reference bridge and proposed publisher; factory-free CLI remains compatible. |

Portable profile and network conformance supplements these checks. Its default
sample publisher and forced SSH fixture do not prove a production native factory
or the actual fixed CLI path. Dynamic bridge UUIDs, sequences and acquisition
times are compared semantically; native frame/receipt preservation is exact.

The study is not a resource soak, a deployed service test, graphical acceptance,
physical suspend or certification of a generic publisher for arbitrary domains.
Record extra projection/copy/validation costs for the later package resource gate.

## Later implementation and acceptance

An affirmative feasibility decision permits a scoped implementation proposal,
not publication or deployment. Mesh first accepts the generic publisher and CLI
factory seam, preserves frozen inputs and checks default/reference compatibility.
Observer then accepts its native source/factory against that immutable Mesh input.
Every new reader artifact needs review because the worker currently admits only a13.

| Pair | Later required outcome |
| --- | --- |
| Existing a13 reader, existing a10 bridge and a6 owner | Baseline unchanged. |
| New reader, a10 reference bridge and a6 owner | Compatible frozen wire/native semantics. |
| Existing a13 reader, new owned publisher/bridge | Compatible frozen wire and explicit profile admission. |
| New injected launcher, old Observer without the factory | Explicit incompatible setup; no reference fallback for selected tmux factory. |
| New Mesh CLI with no factory injection, old producer | Existing reference behavior remains supported. |
| Shared new bridge, selected Agent native facade | Separate Agent cached snapshot/watch/recovery acceptance. |

After independent producer source, installed/native, cancellation, capacity and
normal resource gates, Plus may pin the new exact Observer artifact and run its
headless package/facade checks. A managed cohort requires exact bytes, per-host
topology, recovery and paired rollback. The unchanged UI needs no new graphical
gate for wiring alone; graphical/action or physical sleep changes require their
own scope. No WSS, event source, broker, pooling or provider change belongs here.

The final [review](publisher-extraction-review.md) accepts the
[executed feasibility study](evidence/2026-10-11-publisher-feasibility/README.md)
and records its limits and producer-first implementation sequence.
