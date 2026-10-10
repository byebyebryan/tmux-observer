# Accepted Mesh rollout, 2026-10-10

Snap and Starship now select Observer **0.6.0a1**, Tmux Plus **0.12.0a1** and
shared Mesh **0.1.0a6**. The fleet explicitly selects Mesh; the host-local passive
collector and public native facades retain their existing boundaries. The user
accepted headless picker frame/callback testing for this wiring migration.

## Frozen releases

[Release inputs](release-inputs-tree.json) bind the complete source revisions and
artifact hashes. Each artifact was rebuilt deterministically, downloaded again
after publication, and [verified](published-downloads.json). Later documentation
commits do not change these released bytes.

| Component | Frozen source | Artifact SHA-256 | Source gate |
| --- | --- | --- | --- |
| [Mesh 0.1.0a6](https://github.com/byebyebryan/mesh-plus/releases/tag/v0.1.0a6) | `74b9e54c1fc433aaeb5db29683faf65f6b61016a` | `d5989b80b84bca8f6bb14062e8f75a133978666336dd27c833338a50c8748b3f` | 91 tests |
| [Observer 0.6.0a1](https://github.com/byebyebryan/tmux-observer/releases/tag/v0.6.0a1) | `1931d733c6fd22892024f79e98e0f7995c4a2cb3` | `b904ae3f27916e001460ca62d6f15f64075a30020ef309af37867d625a31fda8` | 382 tests |
| [Plus 0.12.0a1](https://github.com/byebyebryan/rofi-tmux-plus/releases/tag/v0.12.0a1) | `07c261986f9480b78d7a92a068be940ecf2cad33` | bundle `515bea9e6b07d5665e9363e6b32445dfb7162586baddb892c35cf6d8948f21a8` | 293 tests |

Exact-source CI passed for [Mesh](https://github.com/byebyebryan/mesh-plus/actions/runs/38032875510),
[Observer](https://github.com/byebyebryan/tmux-observer/actions/runs/38033047189)
and [Plus](https://github.com/byebyebryan/rofi-tmux-plus/actions/runs/38034114051).
The separate installed gates passed [91 Mesh/native/SSH tests](mesh-final6-tree-installed-final-observer.json)
and [five Observer Mesh/native tests](observer-tree-installed-native.json).
The [dependency inputs](mesh-final6-tree-inputs.json) freeze all five additional
wheels; managed deployment targets Python 3.14 on x86_64.

## Acceptance

The [600-second ordinary two-host profile](normal-tree-summary.json) includes
native client associations, desktop/process matching, all owner/fleet workers,
and the corresponding remote bridges. Neither sampling cadence nor lease was
relaxed: native sampling is two seconds and leases are ten seconds.

| Endpoint | Combined CPU | Fleet plus associated bridge RSS | Owner RSS |
| --- | ---: | ---: | ---: |
| Snap | 3.956% | 83.363 MiB | 21.359 MiB |
| Starship | 2.369% | 82.331 MiB | 23.996 MiB |
| Unchanged limits | 5% | 96 MiB | 64 MiB |

One hundred warm queries per endpoint met cached RPC/CLI deadlines. Native
references, generations, hooks and attachment counts survived; owned services
and processes cleaned up. RSS is sampled and may miss transient peaks. Mesh
byte/proof counters were not instrumented in this resource harness: historical
zero counters are explicitly unmeasured. The summary hashes the private full
report, which retains detailed process measurements.

The [headless picker gate](headless-tree.json) passes seven cases using the
actual installed frame command and callbacks: ready rows/filtering, explicit
refresh settlement, bounded outage behavior, and no collection or SSH triggered
by cached rendering. The 100 warm frames have **124.256 ms p95**, below the
existing 150 ms target. The untimed warmup is reported separately. Frozen bundle
bytes/modes and disposable native state were preserved; caches stayed outside
the package tree.

The [declared capacity gate](capacity-tree-summary.json) passes all eleven cases
within its explicitly partial physical scope: 16 synthetic logical owners on
two physical hosts, 15 real strict SSH links, 32 readers, explicit 33rd-reader
and 17th-owner capacity outcomes, a complete 918,324-byte aggregate, bounded
nonreader retirement, and healthy query deadlines. Peak sampled fleet/bridge
RSS was **693.707 MiB**, below 768 MiB. This establishes transport capacity,
not native truth on 16 physical hosts.

Earlier exact-tuple resource failures remain documented in the
[integration ledger](../../mesh-integration.md) and original dated evidence.
The accepted SDK avoids redundant JSON safety walks and repeated schema work
for bit-identical JSON; current native/proof/receipt/expiry checks still run.
Observer's checked JSON copies retain independent nested ownership. No frozen
wire lock, canonical catalog authority, action guard or native validity rule
changed.

## Managed operations

[Managed reports](managed-operations.json) record installed bytes, recovery,
paired rollback and reselection on both hosts. The installed gate verifies 178
Core members, 343 frontend payloads plus its manifest, 175 shared SDK/dependency
members and all 17 controls. Owner startup is enabled; the desktop service owns
the current fleet context. Fresh Session v1 reads and cached prepared frames
have healthy local/remote owner, desktop and association evidence.

Recovery restarts the owner, waits for current native publication, starts the
desktop service, discovers its active fleet instance, and restarts that reader.
The desktop service requires the owner: restarting the owner stops the desktop
service, retires its fleet and removes the context capture. Restoring that
explicit owner is therefore part of recovery. Both endpoints acquired new
owner publishers and reader incarnations while preserving native references.

Serial rollback restored Observer 0.5.0a1 / Plus 0.11.0a1, all 173 Core and 322
frontend/archive members and 17 prior controls on each endpoint. The legacy
pair passed current local/remote leases, fresh inventory and prepared frames.
Reselection applied only the reviewed package roots and controls, then repeated
owner/desktop readiness and installed acceptance. Both endpoints finished on
the new Mesh tuple. Private rollback archives and control bodies are retained
locally and excluded from this published record.

[Final shared CLI probes](shared-domain-probes.json) pass both native domains,
local resident/owned IPC and remote SSH, snapshot and subscription, plus source
configuration/package checks: ten checks per endpoint. Owned temporary bridges
were reaped. The separate [Agent installed gate](agent-installed-verification.json)
also passes, including exact private reader/bridge artifacts, kernel endpoint
ownership and a cached native read. Agent keeps its independently selected
reader/collector/writer and private Mesh a4 resident bridge; only the shared
public CLI and Tmux fleet select SDK a6.

[Preservation](managed-preservation.json) confirms all 4,806 Snap and 2,533
Starship Agent package files, Agent collector/bridge PIDs and start timestamps,
five unrelated managed files, and the existing `.claude` mode match the baseline
captured immediately before this rollout. An independent Agent collector
promotion occurred earlier during candidate testing and is not attributed to
these operations. Unrelated source edits and target drift were preserved.

Graphical input/visible presentation and physical suspend remain optional and
unrun. The graphical harness's earlier refusal under DMS exclusive input is
retained in the original record; it does not block the accepted headless scope.
