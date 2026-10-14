# Tmux preparation certification and actual pipeline qualification

2026-10-14 UTC. Decision: **certify the optional owner preparation facade; retain
ReadGuard in the production Fleet worker**. Source and private candidate
acceptance do not change published or managed selections.

## Exact inputs

[Inputs](inputs.json) bind the wheel hashes and committed sources. A is freshly
downloaded released Observer a7 / Mesh a15. B is private Observer a8 built from
`c2efc484df80480a05aa1bb54e5caa55b7f0638d` / corrected Mesh a18 built from
`c1b6820a0d92f53cd1b728689ce5f8c39253715f`. C uses exactly B's installed wheels
with a harness-only PreparedReadGuard constructor injection. There is no production
preparation selector. The [Observer descriptor](observer-a8-candidate.json)
remains `built_unaccepted`; this receipt records the separate accepted scopes.
Later harness/test/doc commits do not alter packaged runtime bytes.

Both candidates were built in new directories, installed in an isolated environment,
and checked for runtime source/wheel/installed parity. Baseline wheel hashes match
the preceding release receipts. No old wheel was overwritten. The first Mesh a18
trial failed closed: metadata said a18, while runtime `__version__` said a16.
The [Mesh correction receipt](https://github.com/byebyebryan/mesh-plus/blob/tmux-preparation-20261014/docs/evidence/2026-10-14-tmux-preparation/README.md)
preserves that rejection and the distinct corrected candidate hash.

## Certification and correctness

The [owner API](../../mesh-preparation.md) promises generation-static rules matching
TmuxMeshProfile. Seven dedicated tests compare full current rows on all six
frozen Mesh fixtures at encoded time, intermediate time, receipt expiry and far
future; verify identities, receipt health rules, import laziness and deterministic
purity; and preserve mutation isolation, semantic binding retirement, heartbeat
expiry, gap/resync and failed-replacement teardown. Synthetic rule-only DTO cases
are not claimed as native wire acceptance.

[Native certification](native-certification.json) uses the actual installed
pipeline: one owned local IPC owner and one owned localhost SSH owner. Nine
publications match full legacy/prepared current rows at the same actual clock and
time. Mutation of exported snapshots cannot change prepared results. Stopping the
remote owner revokes its current validity; teardown disconnects both guards and
joins/closes owned resources. Real sessions, options, hooks and attachment counts
are preserved; only disposable fixture sessions are renamed.

[Source log](observer-source-final.log.gz): 404 core tests and canonical
contracts/lint/format. [Installed report](observer-installed.json) and
[log](observer-installed-final.log.gz): 42 Mesh tests, including the seven new
preparation cases and owned native/SSH tests; no skips. The installed report's
own check-mesh harness hash is distinct from the pipeline harness hash in each
native/counter/timing case. Mesh separately passes 145 core and 34 optional WSS
source tests; installed Mesh passes 145 core tests without optional WSS.
Frozen contracts, fixture baselines, Mesh schema bytes and authority are unchanged.

CI at Observer `02d8c58` passed. The first CI attempt at `e08c79b` failed in the
pre-existing grouped-refresh success fixture with a stale control association;
all preparation tests passed. [Original failure](observer-ci-attempt1-failed.log.gz)
is retained. Twenty targeted repetitions then passed without changing the test
or runtime. Root cause remains unresolved; a green rerun does not establish that
this intermittent failure is fixed. Keep association revocation strict and
investigate separately if it recurs. Final branch/main CI status is in the final
[checkpoint receipt](checkpoint.json).

## Work and timing

[Untimed counter audit](audit-cases.json): A/B/C each exercise actual Mesh admission,
Observer native-document admission and Fleet projection. All have **zero Mesh
current queries**, including the diagnostic prepared variant. B and C each perform
ten owner projections and ten native document admissions in this audit. Natural
publication counts vary, so do not infer an exact frame-work comparison from A/B/C.

The worker admits Mesh frames and queues raw replacements. MeshOwnerState then
reconstructs native owner documents for Observer's prepared Fleet composition.
Replacing its guard does not remove these steps. Preparation compiles unused rules.
Avoid removing native admission or sharing a guard across threads to force a gain.

[Timing cases](timing-cases.json) and [block summary](timing-summary.json): 40 fresh
native cases in ten ABBA blocks, without counter instrumentation. Two requested
updates rename both hosts; each update has a fixed 2500 ms actor window followed
by exactly one readiness RPC and the requested cached-read burst. All cases pass
semantic markers and exact requested RPC counts. There are no adaptive readiness
polls inside timing; counter/certification cases use readiness polling separately.

| Comparison | Read burst per update | Blocks | Coordinator CPU reduction range |
| --- | ---: | ---: | ---: |
| A to B (package tuple) | 4 | 2 | -2.82% to +38.61% |
| B to C (preparation only) | 1 | 4 | -11.62% to +2.10% |
| B to C (preparation only) | 16 | 4 | -18.92% to +14.02% |

These are variable block observations, not confidence intervals or a performance
claim. Natural source/proof cadence and publications can vary even with matched
actor windows and requested cached RPC work. Coordinator process CPU includes
foreground RPC/oracle, Fleet, Mesh worker and local bridge; excludes child owners,
remote bridge and SSH CPU. PSS is one post-timing coordinator checkpoint;
peak RSS includes startup. Neither measures total reader memory or whole-tree CPU.
There is no consistent diagnostic preparation gain and no evidence to switch Fleet.
The raw summary scope text mentions variable readiness polls; that applies to the
audit mode. Timing cases record `actorWindowMs: 2500`; the final orchestration
wording distinguishes these modes.

## Reproduction and next boundary

Install the exact four wheels in separate baseline/candidate environments with the
recorded dependency versions; never let PYTHONPATH select source for installed
acceptance. From this Observer checkout:

```sh
rtk proxy /candidate/bin/python scripts/check-mesh --installed --artifact /artifacts/candidate.json --report /new/installed.json
rtk proxy /candidate/bin/python -I -B scripts/qualify-mesh-preparation --prepared --certify --reads 4 --updates 2
rtk proxy /candidate/bin/python scripts/compare-mesh-preparation --baseline /baseline/bin/python --candidate /candidate/bin/python --output /new/audit --audit
rtk proxy /candidate/bin/python scripts/compare-mesh-preparation --baseline /baseline/bin/python --candidate /candidate/bin/python --output /new/timing
```

Absolute environments and new output directories are required. Native gates own
private tmux namespaces, local IPC and authenticated localhost SSH fixtures. No
Agent, Plus, SSH Plus or chezmoi modifications; no release, deployment, ordinary
session use, GUI, physical suspend, real LAN/tailnet, WSS native comparison or
production resource claim. Further adoption requires a real repeated-current
consumer and an independent measured win. The current production path is complete
without that adoption; do not create downstream work merely because the API exists.
