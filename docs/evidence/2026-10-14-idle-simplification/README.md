# Idle simplification owner study

2026-10-14. Diagnostic execution against Mesh's idle simplification plan.
The [exact-reuse prototype](exact-reuse-prototype.patch) is retained for review;
it is not adopted into the product runtime at this checkpoint.

The prototype compares the entire proposed native frame against the already
owned validated frame with type-exact bounded plain-JSON equality. Binding,
proof, queue-expiry and memory reservation checks still execute. It adds only
header-size bookkeeping and no second retained frame. Focused tests pass 11 cases,
including forced full-path equality, unchanged-host expiry, missing proof on a
cache hit, capacity rejection, same-revision changed rows and delivery rebinding.

An initial [microbenchmark](projection-micro.json) compares 5,000 exact same-frame
admissions per mode at 0/2/12 rows. Both paths use the same candidate class, with
matching disabled for the reference path. Cached admission costs 22/29/62 us;
full admission costs 79/106/211 us. This is an isolated private projection cost,
not Fleet CPU improvement. The original raw result used unittest.mock patches
around both modes and is screening evidence only. A reproducible interleaved
microbenchmark and actual-pipeline hit count follow before a value verdict.
No cadence, wire, native collection, Plus frontend or deployment changes occur.

## Value gate: do not adopt native-document reuse

The reproducible `scripts/compare-idle-projection` runs baseline/candidate/candidate/
baseline in independent Python 3.14 processes, imports explicit runtime roots and
compares full projected-output hashes. [ABBA raw results](projection-abba.json)
and [assessment](projection-assessment.json) show the per-call saving. These
same-frame microbenchmarks deliberately maximize hits; they are not fleet savings.

The actual two-host/two-session pipeline [counter sample](reuse-counts.json) has
48 host projections, 23 native admissions and 21 exact document reuses over 30
seconds plus setup/cleanup. The 21 hits avoid approximately 0.003-0.009 CPU
percentage points at the measured projection costs, depending on roster size.
This estimate transfers an isolated microbenchmark and is not an end-to-end CPU
claim. Even its favorable scale is far below the observed Fleet floor and timing
spread. The value gate stops here: the added equality traversal/bookkeeping is
not adopted, and no longer Fleet CPU runs are justified for this candidate.

The patch and focused test changes remain dated study evidence. Product runtime
and tests are restored to the preceding committed implementation. Agent/RLCD
classification and outcome changes reinforce why identity-only reuse would be
incorrect; this discarded prototype compared every field instead.

## Paired private compatibility checkpoint

Tmux a9 source freeze `c2d81de` builds wheel
`60b72977795b1c6b49d2b019c7eb6be7e5434d00b0793e28959a6a368c419c71`.
Its package descriptor remains `built_unaccepted`; independent acceptance is
recorded here and in Mesh's owning evidence, without changing the builder's
immutable descriptor. Exact installed Mesh integration passes 42 tests with zero
skips; the source core gate passes 404 tests. Product changes are the version
banner and explicit Mesh a19 dependency/worker acceptance only. No native
collector, source cadence, desktop policy or Plus runtime changes are included.
The preparation implementation label follows the new package version and retires
old prepared guards; its semantics and public signatures stay unchanged.

S4 native-command consolidation is not selected for implementation in this
networking pass. Owner collection already supplies attachment's opening roster,
and attachment already combines closing clients/session scope in one process.
Sharing the remaining owner closing batch and attachment opening-client read
requires changing the producer's acquisition interface and consistency bracket.
That adds domain coupling for at most one of the four existing native launches
per cycle, before proving how much of reaped CPU is launch overhead. Keep the
existing conservative brackets, deadlines, PID rechecks and legacy fallback.
A distinct producer-owned native pipeline study can reopen it against measured
remaining owner costs; it is not hidden inside the Mesh optimization or pin bump.

Hosted run 38546950888 at `20c6cf7` passed the 404-test source gate, then rejected
Mesh startup because the workflow retained an independent a18 commit literal.
The [original failed log](ci-pin-failure.log.gz) is preserved. This is a candidate
CI-input mismatch, not a recurrence of the publisher receipt-history defect.
The optional CI install now derives the trusted Git URL/revision from committed
`tool.uv.sources.mesh-plus`, the same reviewed input used by the locked project.
No test or runtime check is relaxed and no package payload changes.
