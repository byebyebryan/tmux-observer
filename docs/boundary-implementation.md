# Component extraction execution

Started: 2026-10-08. Authorized scope is the reviewed B0–B5 implementation loop,
incremental commits/pushes and verified scoped managed selection. The
[wire freeze](boundary-wire-v1.md) owns executable decisions; the
[design](component-boundaries.md#next-implementation-sequence) owns responsibility
and acceptance boundaries. This ledger does not replace the existing accepted
operations tuple.

| Gate | State | Evidence / next action |
| --- | --- | --- |
| B0 contracts | Committed/pushed; CI passed | `bf5f838`; three new bundles, independent corpus, split pure domains and blocked-import checks |
| B1 native associations | Source and both-host frozen native passed; final resource gate pending | Optional same-owner cached endpoint; shared opening bracket, independent receipt and explicit Plus annotation profile |
| B2 desktop | Source and frozen Starship native passed; final resource gate pending | 219 tests; separate Niri reads, process evidence and pure matcher; prepared profile input and explicit C3/legacy projections |
| B3 actions | Source and frozen native gates passed | UI-neutral SDK/legacy facade; both-host native, actual SSH writes and Starship focus/close; 285 tests |
| B4 frontend | Source, installed CLI and Snap GUI passed | Narrow lazy clients, C5 picker intents, unchanged legacy CLI argv and test-only historical baseline; 287 tests and 30 installed CLI cases |
| B5 selection | Pending | Exact candidate artifacts, normal/capacity profiling, published/scoped managed selection and rollback |

The final B0 source gate passed 196 tests, 24 new independent valid/invalid
fixtures, eight existing fixtures, compile and Ruff checks. Doc links/fences and
whitespace passed. All 26 old validator function/class bodies match their baseline
AST. The local cached request, independent receipt and effect/projection
consistency are included in this final state.
Original accepted contract bytes remain unchanged. No native sessions, graphical
input, installed artifact or managed selection has changed in B0.

The B1 source gate passed 208 tests and 25 independent boundary cases. The
preliminary checkout-built installed probe passed 11 native cases on Snap,
including actual client switch, server replacement, process UID rejection,
unchanged counts/last-attachment/geometry/options/hooks and destroy-unattached
session lifetime. Eight ordinary default-server references survived and owned
fixtures were removed. This dirty-tree probe is development evidence; the frozen
committed candidate has a separate accepted gate. Version 0.2.0a1 is not selected.

Candidate tooling now validates format-2 three-package/six-bundle coverage and
retains format-1 verification for existing accepted artifacts. Repeated frozen
builds and both-host native proof precede downstream runtime selection.

The latest user instruction moves further foreground acceptance to Snap because
Starship is now in active use. Earlier Starship graphical evidence remains valid
for its recorded candidate; no further Starship graphical input is authorized.
Snap acceptance uses isolated preferences and disposable sessions/windows,
preserving ordinary focus and sessions. A compositor idle overlay is a separate
graphical obstacle, not
authorization to unlock or alter the desktop. No host suspension/RTC tests or
native-event experiments are included. Physical sleep remains optional/unrun.

Keep accepted 96 MiB normal / 768 MiB capacity memory and 5% CPU budgets. New
sampling is shared and bounded; no cadence speedup is selected. Measure cached
query cost, source lag, ticket completion and visible UI adoption separately.

The frozen B1 source `1472eda` produced the same 128-member wheel in two builds:
`3880d7e59558b7f74c5cbe50a75f36d8f4b153e9441f97dda07e96e96853d7c9`.
Clean harness `913d50e` passed all 11 installed native cases on
[Snap](evidence/2026-10-08-b1-associations-snap.json) and
[Starship](evidence/2026-10-08-b1-associations-starship.json), preserving eight/seven
ordinary references and removing owned roots. Both verified all 50 Python package
members and imported the installed implementation. The
[first Starship failure](evidence/2026-10-08-b1-starship-teardown-race.json) was an
owned-fixture teardown race: `kill-server` returns before shutdown completes.
The corrected harness waits for complete native absence before testing the
no-server profile; it changes no producer code. B1 normal resource acceptance is
deferred to the final integrated candidate, after B2 removes desktop native reads.

B2 moves compositor reads to `_niri_observation`, bounded process/annotation
capture to `_process_evidence`, types to `_desktop_types` and the pure policy to
`_desktop_matching`. The coordinator reads the optional cached profile every two
seconds using its existing desktop worker; read requests schedule no native work.
Process/window incarnation checks share the original two-second desktop budget
and process-read cap. Irrelevant non-terminal windows start no process scans.

The adapter emits a validated C3 association batch and a separate legacy
projection. C3 confirms only current local native bindings. A remote launch marker
and compatible SSH argv qualify as `matched` only with a unique current title and
positive native attachment count; otherwise C3 is unknown. Fleet/Tmux v1 preserves
its existing remote launch confirmation, including its old weaker launch-only
cases. This is an explicit compatibility projection, not end-to-end current remote
binding proof. Missing/failed local associations now produce unknown rather than
inventing absence. `DesktopResult.association` crosses the adapter/coordinator
boundary and is checked against the accepted job; it does not add a daemon or
inflate the published Fleet 1 envelope.

Binding, source incarnation, process birth and profile availability participate
in desktop input invalidation. Lease-only renewal preserves the material key;
independent association expiry still revokes positive views. Desktop imports work
with native collectors/actions blocked. A headless coordinator loads neither the
desktop implementation nor a profile reader; explicit `scanner=False` also
disables the adapter in a captured desktop. No UI or managed selection has changed.

The first installed B2 probe on Starship
[failed before viewer creation](evidence/2026-10-08-b2-starship-local-only-failure.json).
Local-only Mesh correctly supplies no remote executable; a new process recheck
attempted to treat that null as a path. The producer gate is reopened, with a
local-only scan regression and failure isolation so malformed adapter inputs
cannot stop the healthy owner reader. The original failing wheel remains
`c6737239e1cca1422d9b24f2e2a7ad7de50fd260f7c80429969902ccac756d3e`.
The harness now persists bounded owned-worker diagnostics and completed cleanup
on failure. Its dependency checker was staged separately in an owned directory
when Starship's configured registry refused dev dependencies; candidate wheel
bytes and isolated worker imports remain independently checked. No fixture
viewer was opened in this failed run; ordinary services and sessions survived.

The repaired wheel passed empty/current native evidence, actual Kitty joins,
client switch, rename and owner restart, but context replacement did not recover.
A [diagnostic repeat](evidence/2026-10-08-b2-starship-title-churn-failure.json)
isolated unrelated window title churn: window identities and process evidence
remained stable while titles changed between the two compositor reads. Rechecking
the complete title string revoked every row. B2 now brackets the set of session
references a title qualifies, so ordinary command/activity title updates preserve
evidence while changed session bindings and duplicate window IDs revoke it.
The diagnostic harness only wraps existing reads, publishes no raw titles/argv,
and records its dirty harness state separately from the frozen wheel.
Source regressions cover binding-stable churn, changed bindings and duplicate
IDs in the closing compositor capture. The failed wheel is not accepted.

Frozen B2 source `2d127af` produced the 134-member wheel
`88f615be9d4075e9e56b5af11791797b35fb11606510b1587272ef7ec71b849b`.
The [clean installed Starship gate](evidence/2026-10-08-b2-desktop-starship.json)
passed all nine native/desktop cases, including context replacement, compositor
failure independent of owner facts and headless sharing. Owned viewers/services
were stopped, owned roots removed and ordinary sessions/focus preserved. The
source gate passed 219 tests, independent contract corpora and compile/Ruff checks.
This proves the installed desktop adapter; Rofi adoption, two-host resources and
managed selection remain later gates. Snap had no graphical probes.

B3 extracts the six explicit lifecycle operations into `tmux_observer_actions`.
`ActionClient.execute` accepts the frozen C5 request and returns its independently
validated result. `LifecycleService` retains the old method/response facade for
the later CLI migration. Neither needs Rofi, an owner, a fleet reader or a native
inventory collector. The native executor selects the default server explicitly
and ignores ambient `TMUX`/`TMUX_PANE`; its exact-reference lookup does not consult
a capped prepared roster. Remote programs use the same fixed default selection.

Native commit, terminal spawn, attachment, focus, viewer close and transport have
separate outcomes. A failed terminal launch after create retains the committed
reference and session. Once a remote write is dispatched, a missing or malformed
acknowledgement returns uncertainty and never selects another route. A complete
native acknowledgement stays confirmed even if later Mesh reporting fails.
Remote terminal/launch-marker evidence does not confirm current remote native
attachment. Legacy verified handles retain their existing guarded close contract;
they do not strengthen C3 remote association claims.

Ordinary focus now requires one fresh compatible window, current process/window
incarnations and repeated native guards. Duplicate candidates fail explicitly;
the C5 `new` viewer policy bypasses reuse. Existing verified close checks, pidfd
pinning and session-survival checks are retained. Python installations without
pidfd bindings report unsupported close capability; synthetic source checks on
Python 3.13 do not establish native close acceptance. The installed Starship
graphical action gate uses its system Python with the required bindings.

The source gate passes 285 tests and both independent contract corpora. A
preliminary checkout-built installed headless probe passed seven owned native
cases, preserved eight ordinary references and removed its private servers. It
is development evidence only. Frozen both-host native actions, actual Starship
focus/close, frontend parity, resources and selection remain separate gates.

Frozen B3 source `b0c99bc` produced the 151-member wheel
`76fde2ef94c10456b7958e814e5b15b4d11de12c329f77b1acdeabe5cbc1707d`.
Installed headless gates passed seven cases on
[Snap](evidence/2026-10-08-b3-actions-snap.json) and
[Starship](evidence/2026-10-08-b3-actions-starship.json), checking all 73 Python
package members. A clean `8d80e9c` harness passed
[four actual SSH cases](evidence/2026-10-08-b3-remote-actions.json) and
[seven Starship desktop cases](evidence/2026-10-08-b3-desktop-actions-starship.json).
These include native required-option refusal, exact rename/kill, unique focus,
duplicate refusal, actual pidfd close, destroy-unattached refusal and native
client-switch invalidation/recovery. Private server namespaces and injected
catalog/reporting isolate these checks; they do not establish ordinary Mesh
provider selection. Ordinary references survived and owned roots/viewers were
removed. Starship focus restoration was accepted. Snap had no GUI input.

The direct client now owns the optional explicit native association job for fresh
`inventory --with-viewers`. Its desktop projection consumes that job's profile
and never invokes a collector. Both-host frozen `feae678` headless native probes
passed eight cases including unchanged attachment counts, options/hooks and
ordinary references. Consumer review subsequently found a missing legacy caller
endpoint/timestamp and optional-scan failure isolation. Those producer defects
were reopened and repaired, with wall-clock endpoint milliseconds preserved and
unknown display facts on scan failure. The source gate now passes 290 tests.

The packaged owner unit explicitly enables local associations; a manually started
headless owner still defaults to the optional profile being disabled. This unit
is an unselected candidate. Integrated both-host native/resource acceptance must
include the enabled profile before any managed promotion.


The B4 runtime source checkpoints are Observer `b192638` (290 source tests)
and Plus `1148dcf` (287 source tests). Repeat committed-source builds produced
identical wheel bytes: Observer
`5f481b8d14bc3e876728c5cb2a223fe1abe844f5a02c12840f2395a8db7c6592`
(152 members) and Plus
`111634792da3f06ec1a0327f0a05606f12cab9c97902cc0e751b53d7ca06b418`
(35 members). All three Observer package roots are independently pinned by the
consumer. Superseded frontend native/action/network implementations reside only
in the test baseline and are excluded from the wheel.

The [installed frontend CLI](evidence/2026-10-08-boundary-b4/frontend-direct.json)
passed 30 native cases across both hosts. Current native SDK checks passed eight
cases on each host, four actual SSH cases and seven Snap desktop action cases,
with owned cleanup and ordinary full-reference preservation. These records are
under `evidence/2026-10-08-boundary-b4/` and retain their actual harness provenance.
The Plus repo records 21 passed frozen Snap picker cases, inspected screenshots,
104.55 ms warm frame p95 and 175-177 ms observed launch surfaces. Its earlier
Starship run passed 11 cases then lost a transient warning during automatic
reconnect; the revised fault keeps the owned delivery supervisor stopped through
expiry while the renderer continues. It retains the 15-second warning deadline
and independently checks read-only reconnect.

The [enabled-profile capacity check](evidence/2026-10-08-boundary-b4/capacity.json)
passed 11 cases with sixteen synthetic owners, fifteen actual SSH links and
thirty-two readers. Conservative combined fleet/bridge RSS was 498.42 MiB against
768 MiB; all ten near-cap validated queries finished within 250 ms (max 150.21 ms).
Owner association profiles are enabled with synthetic empty-client inputs;
native sampling and ordinary desktop matching remain separate resource evidence.

The [ten-minute normal probe](evidence/2026-10-08-boundary-b4/normal-failed-cpu.json)
passed functional/query/memory checks but failed the unchanged Snap CPU target:
5.1656% against 5% (Starship 3.1436%). Sampled fleet/associated-bridge peaks were
73.80/87.53 MiB against 96 MiB. This private native fixture had no attached
clients or matching ordinary windows, and the recorded harness was dirty; it
cannot establish final resource acceptance. The failure remains recorded and
blocks managed promotion of this candidate. The next pass coalesces bounded
native reads and measures passive observation of actual existing sessions and
windows without sending graphical input on either host.


The resource repair coalesces read-only native commands within the existing
absolute deadline and output limits. Every command in a chain is independently
allowlisted, with at most 64 commands. Minimal Plus annotation reads retain
explicit present-empty/absent semantics and verified session markers; expanded
option requests retain their original per-option reads. Closing client and full
server/reference rows share one process, while both client snapshots and process
birth checks remain required. For up to 32 sessions, the minimal owner plus
association profile uses six native process starts per sample instead of
`6 + session_count`. Cadence, freshness, query deadlines and resource budgets
are unchanged. Simulation tests cover hostile chains, malformed/reordered scope,
client/session reuse, empty closing rows and command limits; frozen native proof
and actual-session resource acceptance remain required.

The normal resource endpoint now observes ordinary default servers passively,
using private installed services/IPC/provider preferences and captured Niri
contexts. Its harness refuses native mutations and skips server creation and
server teardown. It requires actual client profiles and positive matching
windows on both endpoints before measurement. No graphical input is sent.

The [actual-session ten-minute probe](evidence/2026-10-08-boundary-b4/normal-actual-failed-cpu.json)
used the frozen `c84ca2e` wheel on both endpoints, with eight ordinary sessions
each and fourteen/six native clients. Snap failed the unchanged combined CPU
target at 6.7263%; Starship passed at 4.0018%. Fleet/associated-bridge sampled RSS
was 89.00/80.39 MiB against 96 MiB, and owner RSS remained below 64 MiB. Warm query
deadlines and native reference/hook preservation passed. This remains a rejected
resource candidate; it is neither published nor selected.

The next repair shares the opening native generation/roster read, bringing the
ordinary minimal owner plus association profile to five process starts per
sample for up to 32 sessions. The reader retains an independently validated
projection between dependency changes and exact lease boundaries, checks a
cheap dependency stamp on every projection request, and validates every complete
outgoing frame at its current time. Returned trees cannot modify that retained
projection. Document validation checks each repeated immutable string once,
while still counting every occurrence toward depth/node limits and rejecting
unclean, oversized or invalid Unicode values. Sampling cadence, network proof,
query deadlines and all resource targets remain unchanged; installed acceptance
must measure this new candidate separately.

The [second actual-session probe](evidence/2026-10-08-boundary-b4/normal-prepared-failed-cpu.json)
used frozen `bde0f68` and again preserved ordinary sessions/hooks and query
deadlines. Snap still failed at 7.2507% combined CPU; Starship passed at 3.5720%.
Fleet/associated-bridge sampled RSS stayed within 96 MiB on both hosts. This
candidate remains unselected; the apparent code savings did not establish a
passing resource result.

A focused owned diagnostic found the scheduler and projection independently
invalidating the same input hash. Separate dependency stamps now let the
projection reuse a key already computed for the latest inputs, while an actual
dependency change or lease boundary still recomputes it. Pure contract validators
retain their initial complete wire pass and every semantic check. For a tree of
plain JSON types, bounded serialization reuses that content/structure validation;
Python subclasses retain the second pass. Serialized byte limits, finite numbers
and strict Unicode checks always run. Tests cover mutating subclasses, byte and
content bounds, dependency changes, expiry and returned-tree mutation.

The default optional Niri adapter now uses one fixed passive `"Windows"` socket
request per read, with same-UID peer checking, a complete-record byte cap and one
absolute BOOTTIME deadline including parsing. It checks both opening and closing
window captures as before. Malformed/late/foreign replies remain unavailable;
there is no second-transport retry. Explicit injected command adapters retain
their bounded CLI path. This follows Niri's
[documented IPC protocol](https://github.com/YaLTeR/niri/blob/main/niri-ipc/src/lib.rs)
and was compared passively against the actual Snap CLI window identities; owned
framing tests and separate frozen/native/resource acceptance remain required.

Frozen Observer `2cebf8c` and Plus `7a9155e` reproduce identical committed-source
wheels (`a71428d…` and `92fe44eb…`). The source gates pass 312 and 287 tests.
Current installed native gates pass 14 collector and 11 association cases per
host, eight headless action cases per host, four actual SSH action cases, seven
Snap window-action cases and nine Snap desktop-observation cases. Starship
receives no graphical input. The exact frontend passes thirty installed CLI
cases across both endpoints and twenty-one Snap picker cases; ready/confirmation
screenshots are inspected. Warm frame p95 is 100.50 ms, observed launch surfaces
are 177–179 ms, and one owned Refresh notice clears in 246.47 ms. Callback/surface
timing does not establish compositor presentation. Current records are under
[`evidence/2026-10-08-boundary-b5/`](evidence/2026-10-08-boundary-b5/); the Plus
repository retains its exact picker record and owned screenshots separately.

The enabled-profile sixteen-owner capacity run passes eleven cases with fifteen
actual SSH links and thirty-two readers. Conservative sampled fleet/bridge RSS
is 497.86 MiB against 768 MiB; native topology and capacity CPU remain outside
that synthetic logical-owner acceptance. The current actual-session ten-minute
run again fails Snap's unchanged five-percent CPU gate: 6.3647%, with Starship at
2.9777%. Memory, cached-query deadlines, native references and hooks pass. The
failed resource record is retained in
[`normal-socket-failed-cpu.json`](evidence/2026-10-08-boundary-b4/normal-socket-failed-cpu.json).
No release or managed promotion follows these functional passes.

An owned forty-five-second
[CPU diagnostic](evidence/2026-10-08-boundary-b5/cpu-diagnostic.json) confirms that
the remaining cost is local: 115 native process starts, 2,513 main-thread wire
tree checks and 165 input hashes. Timings are instrumented, inclusive and not
additive; this diagnostic is not normal-resource acceptance. The ten-minute run
starts no new Observer SSH connections and receives about 3 MiB of owner protocol
payload per endpoint. The resource review records alternatives; the user asks
for the CPU cause before choosing any replacement ceiling. Five percent remains
the promotion gate while the remaining repeated work is investigated.

Chezmoi source `e553f90` repairs coordinated rollback of both exact package
payloads; `565e9b9` requires current desktop evidence and, for an explicitly
profile-enabled selection, a current scope-matching local association receipt.
Ten owned filesystem/readiness tests pass. These are helper source checks;
installed paired rollback/reselection and managed selection remain pending.

The next CPU repair reuses a complete enclosing plain-JSON tree check for nested
snapshot validation within that same invocation. Every public entry still walks
the complete tree; all nested semantic, scope, byte and header checks remain.
Python subclasses retain the full nested fallback and final recheck. Five new
adversarial cases cover mutation during outer/nested schema access, independent
native/association snapshot byte ceilings and the separate header ceiling.
Same-interpreter microbenchmarks over 3,000 records show roughly one-third lower
service, association-delivery and actual fleet-frame validation CPU. This is
function-level evidence, not a normal-resource pass.

The minimal C1 path also shares explicit annotation reads with the complete
closing native roster/generation query. Scope markers and present-empty/absent
semantics remain checked, and every chain stays within 64 read-only commands and
the original absolute deadline. Up to 31 sessions need two C1 process starts;
the independent C2 association sample still needs its two starts and both client
captures/process-birth checks. Larger rosters are bounded in chunks, while
expanded/legacy/custom-profile reads retain their previous path. The source gate
passes 319 tests; frozen native evidence is required for this new candidate.

The normal-resource harness now explicitly uses `/usr/bin/python3` on each
endpoint, matching the managed launchers, and records the installed interpreter
identity. Earlier fixtures used UV's selected interpreter. That runtime difference
must be disclosed rather than treated as evidence of the managed CPU cost.
The next profile retains the five-percent gate, counts all associated children,
and keeps the existing safety instrumentation, cadence, freshness and deadlines.
