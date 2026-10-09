# CPU performance pass

2026-10-09. The fleet bookkeeping pass is accepted as Observer 0.4.0a1 / Plus
0.10.0a2. Its fixed bookkeeping fixture improved about 50%, while comparable
ordinary Snap profiles moved from 4.9048% to 4.4701% of one core. Different
working desktops prevent treating that ordinary difference as causal savings.
This pass targets whole-service work rather than enlarging resource budgets.

## Baseline and remaining work

A separate, uninstrumented sixty-second sample of the selected ordinary Snap
processes measured owner/children 1.6216%, fleet/children 2.6887% and the incoming
bridge serving Starship 0.3333%. That physical-host total is 4.6436%; it is not
the release harness's logical-reader associated-bridge accounting. Fleet self
CPU was 2.1000%, with its main thread 1.5166% and desktop worker 0.5667%.
SSH self CPU was 0.0333%, already included in fleet accounting.

Short nonblocking stack samples repeatedly land in structural/schema validation,
JSON processing, local attachment delivery and process reads. Missed samples
make those samples directional attribution, not precise CPU percentages.
The current owner normally invokes tmux four times each two-second cycle.
Those batches contain 24 subcommands with nine sessions, including two pending
annotation subcommands per session. Remote C3 scans remain every three seconds;
unchanged Mesh still starts its public CLI every fifteen seconds.

## Decisions and execution

1. Add a fixed document-pipeline benchmark that includes owner state/delivery,
   framing, bridge validation and reader admission, alongside the existing fleet
   fixture. Run the same input/harness/interpreter against the frozen baseline
   and candidate; record hashes, counts, output equality and CPU separately.
2. Reduce structural traversal allocations and consolidate freshly decoded
   structural checks with immediate semantic admission. Raw bytes must still
   pass framing, pre-parser depth/node bounds, duplicate-key/numeric/Unicode
   checks, complete tree bounds, schema, scope and encoded-size limits.
   Public dictionary validators continue checking caller-owned mutable inputs.
   Private checked admission must be constructed by the actual decoder/checks,
   never by a public bypass flag or a caller's claimed revision.
3. Review outgoing checked-frame encoding and native command batching against
   the measured pipeline. Reuse only producer-owned checked state/bytes; changed
   clocks, receipts, envelope variants and capacity still get their own guards.
   Native sharing must retain both membership/incarnation brackets, original
   deadlines and the independently usable roster when attachments fail. Keep
   only changes with measured benefit and manageable failure semantics.
4. Review Mesh's supported public interface. The current contract offers list
   and report-route, without a change subscription. Do not import provider
   internals or poll private files to invent notification authority. Record the
   disposition if avoiding CLI launches requires a separately accepted provider
   extension. Fresh remote C3 matching remains unchanged in this pass.
5. Freeze an exact producer/consumer pair after source review; independently
   accept native passivity/recovery/actions, ordinary two-host resources, declared
   capacity and Snap graphical behavior. Publish immutable artifacts, apply only
   owned chezmoi targets, verify both hosts, exercise serial paired rollback and
   preserve ordinary sessions/hooks plus unrelated source/live drift.

Two-second native cadence, ten-second source leases, three-second remote proofs
and desktop scans, freshness/uncertainty semantics and all seven wire contracts
remain fixed. Readers and heartbeats start or renew no native work. Existing
96/768 MiB and 5% resource ceilings remain hard gates. The objective is a measured
whole-service decrease; a synthetic percentage alone does not establish it.
Physical suspend remains optional under the always-on scope. Only Snap receives
foreground input; Starship is in active use.

## Review risks

| Risk | Required protection |
| --- | --- |
| Mutable/exotic Python values defeat a reused structural check | Public validators retain complete checks; exotic containers retain their defensive fallback; decoded plain values get semantic checks before callbacks |
| Faster traversal changes occurrence/depth/byte limits | Differential/adversarial boundary tests, cycles, duplicate strings/keys, malformed numbers and nested independent size limits |
| Checked input weakens scope, ordering or proof | Existing adverse admission/provenance/replay/expiry tests; raw network and local inputs remain untrusted |
| Optional native collection invalidates the primary roster | Independent failure/deadline tests and native acceptance before enabling sharing |
| Mesh optimization loses policy or route changes | Public provider contract only; preserve explicit polling bound unless a separately reviewed extension is accepted |
| Synthetic timing is presented as whole-service savings | Separate fixed pipeline attribution from ordinary installed two-host profile |
| Deployment acceptance overlaps peer rollback | Await each operational phase; serialize recovery and paired rollback |

## Checkpoints

| Checkpoint | Exit evidence | State |
| --- | --- | --- |
| CP0 | Reviewed design, full-path baseline and work attribution | Complete |
| CP1 | Structural/decoded admission savings with public/adverse regression gates | Complete; 371 source tests and all seven bundles/style checks pass |
| CP2 | Outgoing/native/Mesh review and measured implementation or explicit disposition | Complete; retained plain-reference reuse and separate Mesh provider startup change |
| CP3 | Frozen producer, independent pinned consumer, native/resource/capacity/Snap UI | Complete; exact producer/native/resources and 23 independent Snap picker cases pass |
| CP4 | Published artifacts, scoped both-host deploy/recovery/rollback/actions and preserved source drift | Pending |

The [first](evidence/2026-10-09-cpu-performance/owner-baseline-1.json) and
[repeat](evidence/2026-10-09-cpu-performance/owner-baseline-2.json) frozen 0.4.0a1
pipeline baselines use Python 3.14, 300 cycles, ten sessions, two decoded owner
readers, one bridge validation and a ten-client local attachment delivery.
CPU is 3.656/3.690 seconds, with 5,996 structural checks and identical wire digest
`16797eca3470e08f6a25cba0a9ef7dd4b6145f792a6ca72c6772ad948900da04`.
Structural checks have 1.610 seconds inclusive in the first run; inclusive
function times overlap and must not be summed. This isolates pipeline work,
excluding native subprocesses, real IPC, remote proof timing and desktop scans.

CP1 groups structural traversal by container and keeps the original defensive
walk for Python subclasses. Fresh local/SSH/bridge input goes from the actual
bounded decoder into immediate complete semantic admission, without repeating
the enclosing plain-tree check. Public mutable-dictionary entry points retain
their original full structural/semantic/byte checks. Control errors do not
become checked owner documents. Scope/order/nonce/expiry/capacity checks and
defensive retained ownership remain independent.

The updated, identical-harness Python 3.14 comparison records frozen baseline
[3.455](evidence/2026-10-09-cpu-performance/cp1-baseline-1.json) /
[3.612](evidence/2026-10-09-cpu-performance/cp1-baseline-2.json) CPU seconds versus
candidate [2.673](evidence/2026-10-09-cpu-performance/cp1-guarded-1.json) /
[2.894](evidence/2026-10-09-cpu-performance/cp1-guarded-2.json).
That is about 21% lower pipeline CPU, with structural checks 5,996 to 5,096
and the same full wire digest and revisions. Runtime module hashes identify
the uncommitted candidate source used at measurement time; package version alone
does not identify it. Preliminary runs using the development Python 3.13 are
excluded from this comparison. Whole-service native acceptance remains open.

## CP2 disposition

Plain JSON session rows now return their checked full reference from the existing
session semantic check; observation scope checks reuse it. Exotic Python inputs
retain the original second read/check because schema access can mutate subclasses.
The public session validator still returns the same checked dictionary. The
updated harness records the native-validation module hash as well. Matched
CP1 [2.569](evidence/2026-10-09-cpu-performance/cp2-base-1.json) /
[2.598](evidence/2026-10-09-cpu-performance/cp2-base-2.json) CPU seconds versus
CP2 [2.471](evidence/2026-10-09-cpu-performance/cp2-candidate-1.json) /
[2.447](evidence/2026-10-09-cpu-performance/cp2-candidate-2.json) show about 5%
additional fixed-pipeline savings. Bytes, revisions and structural-check counts
remain identical. All 371 source tests and seven bundle/style checks pass.

Native command sharing is deferred. The roster must be accepted and published
before optional attachment work, and optional failure/deadline cannot invalidate
a usable roster. The four existing native invocations retain both membership
and process-incarnation brackets. Pending annotations retain explicit empty
versus absent semantics. A format-only pending shortcut would lose that meaning.

Outgoing checked-byte caches and faster copies are also deferred. Current public
frame factories return mutable dictionaries; generic callers/subclasses require
their final structural guard. Checked bytes would need a separate producer-owned
factory and fan-out ownership review. The existing full canonical encoding,
nested size checks and defensive retained copies remain intact.

The public Mesh CLI retains its fifteen-second discovery bound. A separate,
source-accepted provider change in rofi-ssh-plus `a67be31` lazily loads picker,
launcher and history code only for their commands. Its matched fresh-process
fixture reduces mean CPU from 51.9 to 44.2 ms per invocation, about 15%, with
identical configured replies and all 76 tests passing. At this cadence its whole
service saving is small. Mesh has no public watch API; Observer imports no
provider implementation or private files. The provider's immutable managed
archive pin and installed checks remain separate rollout requirements.

The first frozen owner run stopped after three cases at the harness's assumption
that 32 sequential queries all see one native counter. Its
[failure record](evidence/2026-10-09-cpu-performance/owner-first-timing-failure.json)
preserves the missing-counter limitation. The harness now bounds counter advance
by elapsed owner time divided by the unchanged two-second cadence, verifies
monotonic counters and preserves native roster/lifetime checks. Queries that
cross a scheduled boundary may see the next attempt; reads still schedule none.
The same frozen wheel must pass the corrected gate before acceptance.

The first freeze `83d42e5` passed collector/owner/fleet cases, but the consumer
exact-pin check correctly rejected its stale Python version constant against
0.5.0a1 wheel metadata. That wheel is superseded. The ordinary resource run was
interrupted after its readiness/query cases; owned cleanup completed and no
ten-minute resource result was accepted. The package constant is corrected and
the source gate now compares it with project metadata. All runtime acceptance
is rerun on the corrected freeze; earlier records retain their original scope.

## Frozen producer acceptance

The corrected runtime is `42e9ebf2121280fd00b135e855cf2569f9791c94`, Observer
0.5.0a1 wheel SHA-256
`ae5cb6ec2310a0eb6901f39d5c405b4858d717f07883e024628cdd80587eab9e`.
Repeated builds match all 173 members, including the unchanged seven bundles
and complete 78-module runtime. All 371 source tests and style/contract checks
pass; [runtime CI](https://github.com/byebyebryan/tmux-observer/actions/runs/37909172950)
passes independently. The [descriptor](evidence/2026-10-09-cpu-performance/core-candidate.json)
retains its builder-only `built_unaccepted` label; evidence names each gate.

Matched frozen-wheel pipeline runs use baseline
[3.339](evidence/2026-10-09-cpu-performance/frozen-baseline-1.json) /
[3.357](evidence/2026-10-09-cpu-performance/frozen-baseline-2.json) CPU seconds and
candidate [2.462](evidence/2026-10-09-cpu-performance/frozen-candidate-1.json) /
[2.504](evidence/2026-10-09-cpu-performance/frozen-candidate-2.json).
Mean fixed-pipeline CPU is about 26% lower; bytes, revisions, harness and Python
3.14 match. This excludes actual native/IPC/desktop work.

Independent frozen gates pass: [collector](evidence/2026-10-09-cpu-performance/collector.json)
14 cases, [owner](evidence/2026-10-09-cpu-performance/owner.json) eleven,
[two-host fleet](evidence/2026-10-09-cpu-performance/fleet.json) fifteen,
[native local bindings](evidence/2026-10-09-cpu-performance/bindings.json) eleven,
[actual remote desktop](evidence/2026-10-09-cpu-performance/remote-desktop.json)
seven and [simulated recovery](evidence/2026-10-09-cpu-performance/recovery.json)
four. [Capacity](evidence/2026-10-09-cpu-performance/capacity.json) passes eleven
cases with fifteen actual SSH links and 32 readers. Sampled fleet/children/
associated-bridge RSS peaks at 500.39 MiB against 768 MiB; the partial label
preserves synthetic-owner/two-physical-host limits and no capacity CPU claim.

The [ten-minute ordinary profile](evidence/2026-10-09-cpu-performance/normal.json)
passes with combined logical owner/fleet/associated-bridge CPU **3.6248% Snap /
2.1750% Starship** against 5%. Owner CPU is 1.3839% / 0.7521%; fleet/children
2.1277% / 1.2034%; associated bridge 0.1132% / 0.2196%.
Sampled fleet/children/associated-bridge RSS is 60.35 / 77.66 MiB against 96;
owners are below 64 MiB. Each endpoint has 1,188 native invocations, 192 matching
remote proofs, zero new SSH starts and zero local rediscovery; fresh remote
desktop jobs number 198 / 199. Native timing and warm-query deadlines pass;
ordinary full references, generations and hooks survive owned teardown.

The previous ordinary profile was 4.4701% / 2.4262%. The new observed totals are
lower, but active desktops/activity differ, so this is not a causal percentage
savings estimate. One-second RSS samples may miss transient peaks. This native
gate uses the previously selected Mesh provider; the separately measured new
provider has its own installed-byte and managed rollout gate. Producer resource
acceptance does not establish frontend graphics, managed selection or physical
suspend. The independent pinned Plus 0.11.0a1 passes 293 source tests and all
23 exact-wheel Snap graphical cases; repeated consumer wheels/bundles match.
The [consumer record](https://github.com/byebyebryan/rofi-tmux-plus/blob/main/docs/cpu-performance.md)
names its separate runtime, pin, screenshot and cleanup evidence. Scoped managed
deployment acceptance remains open.
