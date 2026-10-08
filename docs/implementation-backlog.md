# Implementation backlog

Date: 2026-10-07. This is the frozen planning baseline; current implementation and
acceptance are tracked in [implementation status](implementation-status.md).
This turns the [implementation gates](implementation-plan.md) into
reviewable work packages. Gate acceptance remains defined by that plan and the
[validation plan](validation-plan.md).

## Recommended delivery sequence

| Delivery | Tasks | Usable result | Review boundary |
| --- | --- | --- | --- |
| A: standalone observation | T01–T05 | Direct local CLI and pure contract usable without services or Rofi | G0/G1 accepted before sharing collection |
| B: prepared local data | T07–T09 | One local publisher serving many read clients, with bounded refresh outcomes | G2 native service acceptance |
| C: prepared fleet data | T10–T12 | Shared local/remote owner views and endpoint-local desktop observations | G3 two-host native acceptance |
| D: Rofi client | T13–T14, informed by T06 | Prepared startup, remembered context, Open/Attached and honest refresh feedback | G4 compatibility and native GUI acceptance |
| E: managed rollout | T15 | Exact accepted bundles selected on Snap/Starship, with rollback | G6 installed/runtime evidence |

T06 is an early frontend-risk experiment, runnable after T02 with fixture data.
It does not migrate the live frontend or establish Observer/service acceptance.
T16 (lifecycle extraction) and T17 (native events) follow separately; neither
blocks the prepared-read delivery. Do not treat numeric gate order as a requirement
to finish G5 before G6.

The first implementation batch should cover **Delivery A** and end with review
and native producer acceptance before beginning a daemon, SSH transport or frontend
migration. It can contain several small commits. Reviews are technical acceptance
checkpoints; an authorized implementation loop can continue after each passes
without treating every delivery as a new permission request.

## Package and artifact layout

Start with one Python 3.11+ distribution and standard-library runtime code,
following the existing setuptools/check conventions. Reuse the source MIT license
and retain inherited notices. Do not introduce multiple package publications,
a general adapter framework or a new network server for the first delivery.

Proposed responsibilities, created only when their task needs them:

```text
contracts/
  observation-v1/        owner facts and direct output
  service-v1/            owner IPC, stream ordering, receipts and refresh
  fleet-v1/              fleet views, context and authority health
src/tmux_observer/
  public.py              pure supported models/validation exports
  _wire.py               strict bounded JSON primitives
  _clock.py              Linux clock-domain and BOOTTIME helpers
  _process.py            internal bounded read-process execution
  _tmux_wire.py          native metadata parsing
  collector.py          default-server read-only collector
  cli.py                explicit direct/service CLI
  service/              owner scheduler, receipts, IPC, tickets and bridge
src/tmux_observer_client/
  public.py              supported cached read facade and validation
  direct.py              explicit fresh fleet composition
  mesh.py                Host Mesh access/validation
  ssh.py                 owner subscriptions and conservative remote proof
  desktop.py             passive endpoint-local viewer adapter
  fleet.py               shared aggregate and source/context epochs
  cli.py                direct/cached fleet diagnosis and refresh status
tests/                   meaningful wire, identity, clock and transition cases
scripts/                 source checks and isolated acceptance tools
packaging/               candidate unit/config templates, added at G2/G3
artifacts/               candidate descriptors, revision and digest
docs/evidence/           bounded, versioned acceptance results
```

The exact internal file split can stay small. Stable public exports, contract
bundles and CLI boundaries are the compatibility surface; private modules are
not consumer APIs. `tmux_observer.public` imports no native collector/service.
`tmux_observer_client.public` can perform selected local cached IPC, but imports
no collector, background network loop or write implementation. CLI dispatch loads
direct/network/native paths only for explicitly selected operations.

## Tasks and dependencies

Task states below describe the planning baseline. “Owned paths” identify the task's
change boundary, not authorization to edit every repository immediately.
Each task produces a focused reviewable patch plus its applicable evidence.

| Task | Owned paths / responsibility | Depends on | Acceptance result |
| --- | --- | --- | --- |
| T01: foundation | Observer `pyproject.toml`, `LICENSE`, extraction manifest, `scripts/check` | Reviewed design | Baseline/reuse provenance pinned; package and check entry point work |
| T02: executable contracts | Observer `contracts/*`, pure public types and wire validation | T01 | Exact schemas/semantics, bounds, errors and fixtures frozen; no native imports |
| T03: independent reader | Observer acceptance reader and independently assembled raw/semantic fixtures | T02 | Reader rejects invalid wire, identity, receipt, scope and replay cases; G0 closes |
| T04: direct collector | Observer `_process`, `_clock`, `_tmux_wire`, `collector`, direct CLI | T03 | Narrow passive implementation; generation/identity bracketing and bounded retries |
| T05: native producer acceptance | Observer isolated collector acceptance tool/evidence and candidate artifact | T04 | Independent native comparison, absence/race/passivity and packaged CLI proof; G1 closes |
| T06: early Rofi interaction prototype | Observer `scripts/probe-rofi-interaction`, fixture feed and evidence; temporary preferences/owned GUI process | T02 | Actual Rofi preserves filter/caret/selection while adopting an update; limitations recorded |
| T07: source scheduler | Observer owner receipts, fixed configuration, BOOTTIME scheduling/epochs | T05 | Warming, unchanged samples, failure, expiry and suspend transitions are correct |
| T08: owner IPC and bridge | Observer private endpoint, bounded framing/fan-out, read CLI, stdio bridge, candidate unit | T07 | Snapshot/watch/probe reads share samples; ownership/slow-reader/stop rules hold |
| T09: refresh and service acceptance | Observer bounded tickets/status, native multi-reader/lifetime evidence, candidate artifact | T08 | Post-request work, coalescing, terminal lookup and native sharing/recovery pass; G2 closes |
| T10: explicit direct fleet reader | Observer client `mesh`, `direct` and direct CLI | T05; T09 before G3 acceptance | Host Mesh/fresh one-shot behavior works independently, preserving legacy policy |
| T11: persistent remote observation | Observer client `ssh`, scope/proof/recovery state and fault-relay tests | T09, T10 | One selected owner watch per host; buffered/delayed/replayed input cannot renew positives |
| T12: fleet/desktop service acceptance | Observer client `desktop`, `fleet`, cached facade/CLI, context units and two-host evidence | T11 | Independent desktop receipts and catalog health; cached fleet works without Rofi; G3 closes |
| T13: old CLI compatibility | Tmux Plus inventory facade, accepted artifact dependency and compatibility checks | T12 | Released Tmux Session v1 remains fresh/direct with unchanged public behavior |
| T14: Rofi observation client | Tmux Plus picker/model/launcher reader integration and isolated GUI acceptance | T12, T13, T06 | Prepared startup, selection/views, pending targets and ticket feedback pass; G4 closes |
| T15: publish/select/rollback | Producer artifact descriptors; chezmoi `.chezmoiexternal.toml` and scoped unit/config/launcher templates | Accepted T12/T14 | Exact published/managed/installed tuple, host recovery and rollback; G6 closes |
| T16: lifecycle client extraction | Separate write package and Tmux Plus action compatibility facade | T14; separate follow-up | Independent exact-target/write/close acceptance and old contract parity; G5 closes |
| T17: optional native source events | Isolated source-adapter experiment and evidence | T09; separate follow-up | Passivity and measurable benefit established, or polling retained; G7 only if passed |

## Delivery A: first implementation pass

Implement T01–T05 in this order. Keep the released Tmux Plus checkout unchanged
until its producer dependency is accepted.

**T01 — establish the extraction baseline.** Record source
`407ae58ba422ba88fed7da2f9d845ff274830f0e`, canonical Tmux Session v1/Host Mesh v1
bundle digests, reused source paths and MIT notices in a checked manifest. Add
minimal build/check scaffolding. Verification covers installed pure imports and
packaged contract files, not just running from the checkout.

**T02 — resolve the remaining contract decisions in executable form.** Define
exact direct output, source/clock identity, receipt fields, nullability, versioning,
extensions, error codes, refresh scope and queue/admission rules. Distinguish
native observation identity from a service publisher's incarnation. Agree the
service/fleet envelopes now so later code does not invent its own semantics;
no native producer or running service is required to validate these fixtures.
Define fixed default-server selection under inherited tmux/environment settings
explicitly, so source context cannot silently change between clients and service.

**T03 — independently exercise that boundary.** Assemble invalid raw byte streams
and semantic cases without round-tripping the producer serializer. Cover stale
versus empty, mismatched source/reference, new publisher, expired receipt, gap,
nonce reuse and conservative cross-clock expiry. The independent reader must not
call producer-private projection/helpers to decide expected outcomes. Shared pure
types are useful; a second wrapper over the same validator is insufficient proof.

**T04 — extract the read path narrowly.** Move pure metadata/parsing and bounded
execution first, then the collector. Audit both fast and legacy inventory paths.
Add generation checks around the batch, full-reference consistency checks and
one retry inside the original deadline. Reads have an allowlist and cannot start
a server, attach clients, set options or dispatch lifecycle methods. Legacy
optional pane metadata/user-option queries remain explicit direct capabilities.

**T05 — close native and artifact acceptance.** Compare the candidate with separate
native reads. Exercise missing CLI, no server, rename, disappearing sessions,
server restart/reused IDs, malformed metadata and attachment/lifetime neutrality.
Use synthetic cases for impossible-to-force identifier conflicts and label them
as synthetic. Accept the installed direct CLI and its exact candidate digest.
Exercise default-server context selection with an owned test environment as well
as ordinary invocation; collecting a different native source cannot be accepted
merely because its metadata has valid syntax.
Record native versions, scope and remaining limits before beginning T07.

Delivery A is complete when an independent client can consume correct local
metadata with tmux present or absent, without importing Rofi or running a daemon.

## Early frontend risk: T06

Schedule this after the executable fixture shape exists, before finishing the
networking implementation. Use a fixture-backed prepared view and owned Rofi
process on Snap, with isolated preferences/cache. Exercise actual idle callbacks,
continuous typing, view arrows, caret/filter preservation and exact selection.

Record callback invocation, model adoption and visible notice/update separately.
Do not implement the final consumer migration or infer end-to-end service proof
from the fixture. If continuous-input updates fail, record the limitation and
resolve the frontend approach before committing to that UI promise in T14.
The producer work can still proceed independently.

## Deliveries B and C: implementation focus

For B, implement the receipt/scheduler state before its socket server. This gives
IPC one coherent state to publish. Then add shared reads/streams and bounded
refresh control. Native multi-reader and restart/stop acceptance finishes the
delivery; subscribers never create independent collectors.

For C, keep direct fleet diagnosis distinct from the prepared-service path.
Implement Host Mesh association and persistent owner transport before desktop
joins. Matching probes prove remote remaining validity; arrival and heartbeats
alone cannot. Fleet composition rejects old route/source/context epochs and
treats failed Mesh authority explicitly. Desktop scanning uses those accepted
inputs with its own receipt and contributes no focus/close handle.

Accept Snap reading Starship and Starship reading Snap with a remote down,
publisher restart, delayed/trickled input and a replaced desktop context. The
user-selected [always-on scope](always-on-acceptance.md) requires simulated
callback gaps, expiry and late/buffered result rejection; physical sleep/wake is
an optional follow-up and cannot block T12/T13/T14/T15.
Measure foreground queries separately from source lag and background cost. The
initial 16-owner/32-subscriber service limits are new cached-service capacities;
the old direct CLI/Mesh limits stay compatible.

## Deliveries D and E: migration and selection

First prove the old CLI facade still satisfies its canonical contract with fresh
direct reads. Then replace Rofi's observation jobs with the accepted cached facade.
Keep saved context, presentation snapshots, ordering, filter and action intent
in Tmux Plus. Preserve independent write revalidation and exact pending targets.

Background renewals stay quiet. A requested refresh refers to a bounded ticket;
its terminal state is queryable even if the UI missed a notification. Missing,
warming or failed services have bounded visible outcomes rather than hidden
direct collection. Use T06 results and native GUI tests to close actual adoption
and notice timing; frame-generation timing alone is insufficient.

After the source/candidate/GUI gates pass, prepare exact published artifacts and
scoped managed changes. Bring up owner publishers, then fleet readers, then select
the Rofi candidate. Check bytes, host scope, user-manager lifetime, desktop context,
native recovery and rollback on each endpoint. The user's 2026-10-08 scope assigns
production GUI acceptance to Starship; Snap is in active use and receives headless
checks only. The earlier Snap T06 prototype retains its own distinct scope.

## Review and evidence record

Keep one compact status record per delivery: task states, source/candidate ID,
checks, native/installed/GUI evidence links, findings, limits and next gate.
Each implementation task gets a focused patch; each completed delivery gets a
producer acceptance review before downstream migration. A downstream finding
reopens the task owning the defect rather than creating a frontend workaround.

Review traceability:

| Design-review concern | Implementing tasks |
| --- | --- |
| Passive boundary, native identity races and lifetime (R01/R03/R06/R09) | T02, T04–T05, T08–T09; T17 if attempted |
| Provenance, remote freshness, epoch/replay and Mesh authority (R02/R04/R10/R18) | T02–T03, T10–T12 |
| Independent viewer facts and action authority (R05/R14) | T02, T12–T14; T16 separately |
| Explicit access, compatibility and truthful refresh (R07/R08/R11/R13) | T02–T03, T09, T13–T14 |
| Capacity, timing domains and service lifetime (R12/R16/R17/R19) | T02, T04, T07–T12, T15 |
| Evidence levels and managed acceptance (R15) | T05, T09, T12, T14–T15 |

Source checks belong in each task that changes executable behavior; native
acceptance belongs at the relevant delivery gate. Do not add tests that merely
repeat assignments, rerun broad checks without a new reason, or classify a
planned/native-not-run case as passed.
