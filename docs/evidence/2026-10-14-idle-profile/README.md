# Idle Tmux owner and Mesh Fleet profiling

2026-10-14. Verdict: **the small-roster CPU cost is real and substantially fixed**.
The useful next work is reducing repeated idle scheduling/validation/native command
work, rather than changing SSH carrier or adopting PreparedReadGuard mechanically.
This pass changes diagnostics and documentation only. Services, configuration,
contracts, source runtime implementations and deployed selections are unchanged.

## Live baseline: selected Observer a7 / Mesh a15

[Three-minute raw sample](live-baseline.json.gz) and [summary](live-summary.json)
measure the running Snap systemd service cgroups at one-second intervals. CPU is
percent of one logical core, not percent of total machine capacity. There were
two local sessions and four Starship sessions in the cached Fleet view. These
are observations of a working desktop, not a controlled idle-host experiment.

| Component | CPU | End cgroup memory |
| --- | ---: | ---: |
| Fleet and local children | 2.632% | 43.21 MiB |
| Owner and native command children | 1.098% | 15.87 MiB |
| Local sum | 3.730% | 59.08 MiB |

The stable Fleet Python PID accounts for 2.628%; its SSH client accumulated zero
CPU ticks. The owner Python PID accounts for 0.533%, and its reaped native children
for 0.561%. Proc ticks and cgroup accounting have different granularity and do
not sum exactly. Memory is cgroup accounting, not RSS/PSS. Remote host CPU and
bridges outside these cgroups are excluded; this is not a complete distributed
reader budget. No production profiler was attached or live process restarted.

Separate cached [start](live-start.json)/[end](live-end.json) reads span 212.458
seconds, overlapping the resource window. The owner accepted 105 samples with
**zero native owner view-revision changes**. Fleet's view revision changed by
five; do not claim that all desktop/remote facts were completely static. These
cached reads do not schedule native collection. Selected on-disk versions and
[code/dependency tree hashes](runtime-inputs.json) identify the deployed package
roots; they are not independent attestation of every already-loaded module.

## Controlled installed-runtime fixtures

The new [probe](../../../scripts/profile-idle-mesh) loads explicit installed runtime
roots and the owning repository's fixture helpers. It runs two private default-server
tmux namespaces, owners with local attachments enabled, one Fleet coordinator,
and actual authenticated localhost SSH to the remote bridge. No ordinary session,
unit, hook, attachment, route-health or configuration is modified. Before/after
native identity/attachment references are checked and all owned resources close.

[Summary and raw counters](summary.json) retain each case and harness hash. Four
sequential 60-second uninstrumented runs use the deployed a7/a15 pair:

| Sessions per host | Desktop scanning | Local owner incl. reaped commands | Fleet Python |
| --- | --- | ---: | ---: |
| 0 | off | 0.967% | 1.683% |
| 2 | off | 0.783% | 1.550% |
| 12 | off | 1.283% | 2.367% |
| 2 | on | 1.200% | 2.800% |

These are single observations, not confidence intervals or causal savings claims.
The empty/two-session order already shows noise. They establish a substantial
empty-roster floor and a cost that grows with larger rosters. Each owner accepts
30 new samples per 60-second interval even when idle. Local Fleet session rows
remain equal in the headless cases; desktop cases change their composite rows.
Native session identities and attachment counts remain unchanged on both hosts.

The initial four cases count only the three named Python roots plus reaped child
CPU. Their old scope string does not enumerate every excluded persistent child;
it must not be read as whole-tree accounting. A separate expanded `transport-2`
run explicitly measures persistent transport roots: local owner 1.150%, Fleet
2.000%, remote bridge 0.533%, remote owner 1.150%, SSH client zero ticks. SSH daemon
helpers and tmux servers are excluded. Do not compare the remote bridge's CPU
against actual tailnet endpoints or infer a causal percentage from serial runs.

A new isolated installation of the prior private a8/a18 wheels was also measured
with the same CPython 3.14.8 and dependency roots: `candidate-2` passes current-state
and cleanup checks, with local owner 1.450%, Fleet 2.467%, remote bridge 0.650%.
This single, later case is **not** matched upgrade regression/improvement evidence.
The owner, collector and attachment collector files are byte-identical across
these versions, and Mesh's deadline helper AST is unchanged. Upgrading the tuple
alone does not remove the identified repeated-work mechanisms. No candidate is
deployed by this check; exact wheel hashes are in runtime inputs.

## Function and call-count evidence

Two separate 60-second `--profile` runs cover headless and captured desktop modes.
Four compressed JSON profiles per run bind owner-local, owner-remote, Fleet and
remote bridge. CPython 3.14's cProfile collects process-wide; the harness enables
one profiler per process after imports. Its built-in timer records **wall time**,
including blocking and overlapping inclusive calls. Never treat these figures as
CPU shares or compare instrumented CPU with the uninstrumented baselines.
Profiles include runtime setup/cleanup around the 60-second idle window. Async
resume counts are not logical request counts. The following are synchronous calls:

| Headless Fleet operation | Calls |
| --- | ---: |
| Mesh protocol validate | 366 |
| Mesh response validation | 86 |
| Mesh guard accept | 43 |
| Observer owner projection | 86 |
| Observer native-document admission | 82 |
| Mesh current queries | 0 |
| Mesh event-loop iterations (`_run_once`) | 5,190 |
| Fleet project-changed checks | 1,206 |

Mesh response validation is entered both during composition and guard admission;
the count alone does not prove either independent boundary can be skipped. JSON
schema traversal (`descend`, `evolve`) and native tree validation are prominent
nonblocking profile entries. The transport recursive `tree` function records
150,468 visits; that is recursion work, not 150,468 frames.

The local owner profile records 31 native collections, 31 attachment collections
and 124 bounded native command invocations. Source inspection matches this roughly
four-command-per-cycle path. The owner still samples at a fixed 2000 ms cadence.
The command-launch and validation floor survives an empty or unchanged roster.

The desktop profile records 21 desktop scans, 30 attachment cached reads and 49
binding jobs. Fleet already checks prepared dependencies before a full projection;
1,206 project-changed checks are not 1,206 full projection rebuilds. Headless mode
still runs cheap unsupported desktop callbacks. Profiling does not establish that
each scan/job is unnecessary; it identifies work to audit for stable inputs.

Mesh `within_deadline` and Reader's subscription wait both poll at up to 100 ms.
Several concurrent waits and their callback cycles produce frequent event-loop
iterations even without changing facts. Loop iterations are not OS wakeup counts,
and waiting in epoll is not busy CPU. Nonetheless timer/callback churn is a
concrete candidate to reduce while retaining BOOTTIME expiry, cancellation,
started-frame bounds, source silence and post-resume revocation.

[Excluded instrumentation attempts](excluded-instrumentation.json) record harness
failures, not producer failures: independent cProfile instances collided on
CPython 3.14's process-wide tool ID, thread CPU clocks were inappropriate for
process-wide events, and a bridge wrapper import shadowed its earlier pathlib
reference. Those profiles and failed readiness cases are excluded. Corrected runs
have four complete nonempty profiles, empty child stderr and current-state/cleanup
success. Final short native smoke checks the final output-admission logic.

## Next pass, before implementation

1. **Mesh scheduling:** measure how much repeated deadline/Reader polling can be
   consolidated into fewer wakeups. Preserve BOOTTIME and all existing absolute
   IO/deadline/cancellation guarantees; do not simply relax a timeout to win CPU.
2. **Receipt-only work:** count and attribute repeated validation/reconstruction
   across one admitted frame versus independent public boundaries. Reuse owned
   checked state only where mutation, expiry and cross-thread ownership remain
   explicit. Current Fleet has no repeated Mesh current calls to optimize.
3. **Observer native/desktop floor:** investigate stable-input work and native
   command consolidation. Slower polling is a separate explicit freshness tradeoff,
   not a transparent optimization. Empty fleets still need discovery of new sessions.

Start with one isolated prototype and a longer matched comparison. Keep native
truth, partial/unknown states, original receipt times and stale authority rules.
No new wire/API change is proposed by this diagnostic pass. Native control-mode
attachment, transport replacement, Agent/Plus changes and managed rollout are
outside it.

## Reproduction and validation

Create a JSON array of absolute installed package/dependency roots (Observer,
Mesh, attrs/jsonschema/referencing/rpds as needed). The source test helper path is
added separately; production runtime imports come from those explicit roots.

```sh
rtk proxy /usr/bin/python3.14 -I -B scripts/profile-idle-mesh --runtime-paths /private/runtime-paths.json --output /new/empty --sessions 0 --seconds 60
rtk proxy /usr/bin/python3.14 -I -B scripts/profile-idle-mesh --runtime-paths /private/runtime-paths.json --output /new/two --sessions 2 --seconds 60
rtk proxy /usr/bin/python3.14 -I -B scripts/profile-idle-mesh --runtime-paths /private/runtime-paths.json --output /new/twelve --sessions 12 --seconds 60
rtk proxy /usr/bin/python3.14 -I -B scripts/profile-idle-mesh --runtime-paths /private/runtime-paths.json --output /new/profile --sessions 2 --seconds 60 --profile --desktop
```

New output directories are mandatory. Profile mode is qualified only on CPython
3.14. CPU comes from `/proc/PID/stat` self/reaped ticks and actual monotonic elapsed
time; live CPU uses systemd `CPUUsageNSec` deltas. Subprocess/server inclusion is
listed above. Temporary SSH keys are never copied into acceptance evidence.
Standalone script lint/format, JSON/checksums, links, frozen-path comparison and
native runs are checked. Full production runtime suites are not required to infer
a performance result from this diagnostic-only change; hosted source CI has its
separate status. No release, graphical or deployment acceptance is claimed.

## Hosted checkpoint and retained integration concern

The [CI checkpoint](ci-checkpoint.json) binds Observer `aed331e` run 38526645393
and Mesh `94a7858` run 38526750779. Mesh passes. Observer's canonical source gate
passes, then its integration gate reproduces the same grouped-refresh success
test failure seen in the previous preparation pass: a `stale_scope` control
association revocation. The [original failed log](observer-ci-first-failure.log.gz)
is retained. Product runtime, tests and dependency pins are unchanged by this
diagnostic pass. No source or test relaxation is made to turn this green.

The cause remains unresolved; it is not established whether fixture synchronization
or runtime scheduling owns the race. Investigate it before implementing timer or
refresh scheduling changes. This is a separate correctness concern from the
successful idle fixture measurements. The report is retained on the profiling
branch rather than promoted as a fully green integration checkpoint.
