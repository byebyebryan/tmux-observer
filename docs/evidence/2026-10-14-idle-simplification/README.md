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
