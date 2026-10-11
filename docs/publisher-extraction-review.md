# Cached publisher design review

2026-10-11. Primary-led source/design review, not an independent agent review.
The [plan](publisher-extraction-plan.md) defines this pass's scope.

## Final disposition

**Go for a Mesh producer implementation proposal**, followed by an Observer-owned
cached source. **No-go for runtime adoption in this pass.** The
[accepted study](evidence/2026-10-11-publisher-feasibility/README.md) passes 17
decision-driving checks and six independent profile cases. It proves the design
can serve native cached evidence over owned IPC and the actual fixed SSH command
while retaining reference compatibility. It uses a copied CLI, not a released
public API, and measures no resource budgets.

The a6 Observer / a6 Plus / a13 reader / a10 bridge cohort remains selected.
Retaining the reference integration remains supported. No source defect in that
accepted cohort requires urgent rollout; this extraction clarifies ownership.

## Findings before feasibility

| Finding | Design response |
| --- | --- |
| Local subclass extraction would leave the fixed remote CLI on the reference adapter. | Test the actual fixed SSH command against the candidate factory. |
| Moving the entire reference adapter would duplicate generic proof construction in Observer. | Mesh owns a generic publisher helper; Observer owns a cached native source. |
| A new default CLI factory would break existing old producer installations. | Add trusted Python injection; default and omitted-domain dispatch retain reference behavior. |
| A failing selected factory could accidentally recover via the reference implementation. | Supplied-factory failure is terminal; exercise failure and wrong binding. |
| A13 exports neither the proposed publisher helper nor CLI injection hook. | Treat copied CLI/prototype code as research; Mesh producer acceptance must precede runtime migration. |
| Default portable conformance publishers are synthetic. | Pair profile conformance with owner-native IPC and actual CLI/SSH evidence. |
| Pure profile inspection copies native payloads and can increase validation cost. | Record the extra work and require exact-package resource acceptance later. |
| A shared bridge upgrade affects Agent delivery. | Preserve current selection now; include separate Agent verification in later shared-bridge adoption. |

## Findings from execution and review

| Finding | Required production response |
| --- | --- |
| Candidate envelopes/proofs match the independent reference semantically and preserve the native frame exactly. | Keep frozen Service/Fleet/Delivery contracts; use existing explicit profiles. |
| Factory invocation works locally and through the actual fixed SSH command. | Implement one supported additive seam in Mesh; use the same static Observer factory for both paths. |
| Caller-owned mutable data could alter queued evidence. | Own admitted frame/barrier data; prove mutation isolation. |
| Cancellation after acquisition can lose a successful channel result; native guard construction can fail after admission. | Cover both acquisition windows and active reads with owned cleanup; no later failure may orphan a channel. |
| Eager factory imports would load state/native dependencies during catalog polling. | Keep lazy factory imports and verify real isolated authority reads with an import fence. |
| Same accepted counter with a new expiry could manufacture freshness. | Bind counters to owner publisher/clock, preserve original expiry and mutate tracking only after successful admission. |
| A shaped proof with the wrong nonce can pass generic shape validation. | Retain the receiver's exact request/nonce binding; shape validation alone grants no current rows. |
| The baseline a10 bridge and default a13 reference CLI still interoperate with the explicit a13 reader/profile. | Preserve default dispatch and include mixed-version installed compatibility in the new producer gates. |
| Extra copies/projection/envelope validation may increase CPU or RSS. | Measure the exact artifact under normal and declared-capacity load before downstream migration; do not optimize from the five-second study duration. |
| Generic synthetic Agent input passes, but selected native Agent was not exercised. | Treat shared-bridge Agent acceptance as a later independent checkpoint against its then-selected facade. |

Two exploratory negative fixtures originally failed before the targeted guard;
the final fixtures first pass native shape/semantics. An unsupported CLI help
invocation was replaced by an isolated catalog read. Those earlier runs are not
acceptance. The final report records corrected code digests and cleanup.

## Ordered implementation backlog

Each checkpoint is reviewed and committed independently. A later consumer finding
reopens its owning producer checkpoint. New artifacts are frozen before their
installed/native/resource evidence is taken.

| Checkpoint and owner | Concrete scope | Acceptance before proceeding |
| --- | --- | --- |
| P1 — Mesh Plus | Add proposed `CachedSource`/`CachedPublication`/`CachedPublisher` in a generic publisher module and public API exports; add keyword-only factory injection to `cli.main` and `configured_adapter`. Names are settled by the Mesh producer review. | Mesh source/contract gates; no native/reference/desktop/action imports in helper; explicit profile binding, proof/counter/data ownership/cancellation checks; default CLI compatibility and real authority fast path. Frozen schema/profile bytes stay unchanged. |
| P2 — Mesh Plus | Freeze a separately accepted candidate SDK/CLI artifact and document its public Python surface, factories, capability checks and failure semantics. | Installed public API/import-fence tests, configured IPC/fixed SSH tests, portable profile/network conformance and a10 reference interoperability. Copied study code is not a substitute. No artifact selection follows automatically. |
| P3 — Tmux Observer | Add its native cached source/factory; replace `TmuxMeshAdapter` reference inheritance while preserving `(host, path, source)` compatibility and public codec facade behavior. Local `_mesh_worker` constructs the same owner factory used by the trusted remote entry point. Update the exact SDK pin/version guard only against P2. | Observer source/Mesh gates, native host/UID/clock/request/order guards, status/watch-only operations, proof freshness, cleanup and old-bridge compatibility. Core, collectors, refresh/control, actions, desktop association and contracts retain their behavior. |
| P4 — Tmux Observer | Freeze an exact Observer candidate and exercise direct/native owner, local publisher, fixed remote CLI, fleet composition and declared capacity as separate gates. | Installed bytes/profile conformance, native identities/passivity, outage/restart/empty/disconnect, repeated cancellation, normal resource soak and capacity deadlines. Compare with [a13 resource evidence](evidence/2026-10-11-mesh-sdk-adoption/README.md#final-frozen-producer-input); Snap previously used 4.286%/5% CPU and approximately 83/96 MiB fleet-plus-bridge RSS. |
| P5 — Tmux Plus | Pin the accepted P4 Observer artifact and its reviewed reader input; preserve standalone/provider-neutral Tmux Session v1 facade and lifecycle validation. | Source/package/headless consumer acceptance, mixed old/new publisher delivery and fail-closed action validation. Wiring alone needs no new graphical gate; any UI/action behavior change reopens its own gate. |
| P6 — Managed deployment | Prepare a versioned shared bridge and static lazy Observer factory in the managed `mesh-plus` launcher. Preserve the fixed remote command, default reference Agent branch and paired rollback. | Exact bytes on each endpoint, then-selected Agent cached snapshot/watch/recovery compatibility, source descriptors and topology, owner/fleet recovery, headless consumer checks and paired rollback. Do not edit or adopt Agent producer code as part of this extraction. |

P3 should keep the native source in an owner module separate from the generic
publisher. Research-only trace environment variables, CLI source copying and
fixture metrics must not enter runtime code. Add no module selectors to wire,
configuration or CLI. A missing/unavailable selected factory fails explicitly;
an intentionally omitted domain retains only the declared reference branch.

P4 precedes P5, and P5 plus independent shared-bridge Agent acceptance precede P6.
If compatible semantics or resource budgets fail, retain the existing reference
selection and revise the relevant producer checkpoint. Package publication and
managed adoption remain separately authorized actions.

## Scope closed by this pass

Current Observer/Plus documentation is synchronized while historical acceptance
bodies retain their original scope. The proposed interface, study, exact input
and code digests, corrected negative controls, native passivity and cleanup are
recorded and reviewed. Production source and deployment selection are unchanged.

WSS, native control-mode events, physical suspend, UI refinement and optional
graphical checks are independent follow-ups. This review approves the bounded
implementation sequence above; it does not combine them into the extraction.
