# Accepted catalog bound fix, 2026-10-10

Snap and Starship select Mesh **0.1.0a7**, Observer **0.6.0a2** and Tmux Plus
**0.12.0a2**. This closes the shared library catalog's file-check/read race and
the stale current-selection documentation and managed-source publication gaps.
The [previous accepted rollout](../2026-10-10-mesh-rollout/README.md) remains
historical evidence for its own frozen tuple.

## Fix and frozen inputs

Library config and health reads now parse bytes from the same checked regular
file descriptor. Actual reads stop at four MiB plus one overflow-detection byte,
so growth after `fstat` cannot bypass the limit. A pathname replaced after open
cannot redirect the parser to a different file or FIFO. Five added regressions
cover both growing inputs, pathname replacement, captured parser bytes, exact
limit/missing-file semantics and the maximum bytes read.

[Release inputs](release-inputs.json) and [dependency inputs](mesh-inputs.json)
bind the exact source revisions, deterministic wheels and native bundle.
[Downloaded release bytes](published-downloads.json) match those frozen hashes.
[Exact-source CI](exact-source-ci.json) passes all three projects. The complete
source gates pass 96 Mesh, 382 Observer and 293 Plus tests.

Independent producer acceptance passes [96 installed native/SSH tests](mesh-installed-native.json)
with the preceding Observer package, and [67 standalone tests](mesh-installed-standalone.json)
with neither Observer installed. The paired Observer passes
[five installed Mesh/native integration tests](observer-installed-native.json).
The [Host Mesh compatibility review](authority-compatibility.json) passes all 82
SSH Plus regressions using the candidate authority. `authority.py` has a
reviewed private captured-byte parser extension; default process reader/writer
semantics remain compatible. This report explicitly records that the extraction
is no longer byte-identical. The [compatibility review harness](authority-review.py)
requires the recorded baseline and candidate authority hashes before running
regressions; invoke it with the exact installed SDK and `--backend mesh-plus`.
The [21 frozen wire inputs](wire-preservation.json)
remain byte-identical; no schema lock was regenerated.

## Independent operational acceptance

The [600-second two-host profile](normal-summary.json) reads ordinary default
servers, native associations and actual desktop/process matches passively.
Two-second sampling and ten-second leases retain their existing values.

| Endpoint | Combined CPU | Fleet plus associated bridges | Owner RSS |
| --- | ---: | ---: | ---: |
| Snap | 3.675% | 83.430 MiB | 25.008 MiB |
| Starship | 2.425% | 82.129 MiB | 24.832 MiB |
| Existing limits | 5% | 96 MiB | 64 MiB |

Both endpoints pass 100 warm cached RPC/CLI queries. Native references,
generation, hooks and attachment counts survive owned service teardown.
RSS is sampled and can miss transient peaks. Mesh byte/proof counters remain
unmeasured; zero fields in the private full report do not imply zero traffic.

The [capacity gate](capacity-summary.json) passes all eleven cases within its
partial physical scope: sixteen synthetic logical owners on two physical hosts,
fifteen actual strict SSH links, thirty-two readers and explicit overflow
outcomes. Sampled combined peak RSS is
**696.000 MiB**, below 768 MiB.
This establishes transport capacity, not native truth on sixteen physical hosts.

The [installed headless picker gate](headless.json) passes seven cases using the
exact managed bundle's frame command and callbacks. Its 100 warm-frame p95 is
**90.206 ms**, below the unchanged 150 ms target. The report retains
the untimed warmup and proves no collection or SSH from cached rendering, bounded
outage behavior, explicit refresh settlement, native passivity and cleanup.
The [first unchanged candidate timing run](headless-first-failure.json) narrowly
missed p95 at 150.140534 ms. Its seven behavioral cases passed. A serial
[preceding-tuple comparison](headless-baseline.json) and unchanged candidate
repeat followed; all reports are retained. [Observed background scheduling](headless-scheduling-context.json)
showed independent kubectl activity, which was left running. This is contextual
evidence, not proof that it caused the first miss. The threshold, sample count
and warmup rule were unchanged. Graphical presentation/input and physical
suspend are optional and unrun.

## Managed selection, recovery and rollback

[Staged launchers](managed-staging.json) load both native facades with the exact
versioned SDK and dependency roots. [Managed operations](managed-operations.json)
verify complete installed payloads and seventeen controls on both hosts, fresh
Session v1 inventory, prepared desktop/local/remote evidence and new owner/reader
incarnations during recovery. Owner publication precedes desktop startup; its
current context determines the fleet unit.

SDK a7 installs at `.local/share/mesh-plus/0.1.0a7/python`. The original
`.local/share/mesh-plus/python` remains the exact a6 rollback input. Serial
rollback restores Observer 0.6.0a1 / Plus 0.12.0a1 and all prior controls, whose
launchers select retained a6. Both restored tuples pass fresh and cached reads.
Scoped reselection returns both hosts to a7 / 0.6.0a2 / 0.12.0a2 and repeats
installed acceptance. The private baseline archives/control bodies remain local.

[Shared-domain probes](shared-domain-probes.json) pass Agent and Tmux snapshot
and subscription over local IPC and remote SSH: ten checks per endpoint.
[Independent Agent verification](agent-installed-verification.json) also passes.
Its private reader, collector, writer and resident Mesh bridge stay separately
selected. [Preservation checks](preservation.json) confirm their package bytes
and process incarnations, unrelated managed files/modes, retained SDK a6 and
Starship's foreign source edits. An additional transient Agent cost unit became
active on both hosts during the run; it has no Tmux dependencies, was left
running, and is reported separately without assigning a cause. Only fourteen
explicit deployment targets were applied. The canonical managed-source history is published by fast-forward;
existing prerequisite commits and Starship's local changes are preserved.
