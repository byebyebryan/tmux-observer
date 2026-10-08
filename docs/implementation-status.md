# Implementation status

Updated: 2026-10-07. Goal: Deliveries A–E, with reviewed commits as work progresses.
The design/backlog baseline is commit `a4fba75`.

Latest continuation: clean source `3f79975` passed seven installed native manual
SSH/window cases, including ambiguity, rename and owner replacement. Its
[desktop-inclusive ten-minute profile](evidence/2026-10-07-native-remote-desktop-normal-g3-partial.json)
stayed below the selected 96 MiB fleet ceiling (82.49/82.40 MiB), but Snap combined
CPU failed the unchanged 5% target at 5.74% (Starship 2.40%). This failure remains
recorded; optimization and a clean rerun are required. Cached RPC p95 was
5.77/3.28 ms and cached CLI p95 47.92/36.95 ms, separate from Rofi rendering.
Actual SSH capacity, physical sleep, frontend migration and managed rollout
remain open.

| Delivery | State | Evidence |
| --- | --- | --- |
| A: standalone producer | Accepted: T01–T05; G0/G1 passed | Pure API, exact bundles, independent reader and 14 native/installed cases; [latest G1 evidence](evidence/2026-10-07-native-collector-utf8-g1.json) |
| B: owner service | Accepted: T07–T09; G2 passed | Bounded tickets/stdio and 11 installed/native cases; [latest G2 evidence](evidence/2026-10-07-native-owner-utf8-g2.json) |
| C: fleet service | In progress: T10/T11 source and T12 scheduler/CLI/context units | Shared aggregate, independent desktop jobs, causal grouped refresh, prepared CLI and explicit context handoff; native fleet G3 pending |
| D: Rofi client | Planned; T06 native mode interaction prototype passes, production integration unresolved | [Native experiment](rofi-interaction-probe.md); idle/active-input adoption and exact selection observed with version-pinned mode prototype; no frontend migration accepted |
| E: managed rollout | Planned | None |

Pure validation and `collect --host-id ID` are implemented and accepted for
the Delivery A scope. Owner service is accepted in isolated candidate scope; fleet,
GUI migration and managed deployment remain pending. Source, installed/native,
graphical and managed evidence remain separate gates.

The collector rejects generic connection errors as absence. Fast and legacy
paths check final generation and full-reference roster within one 2-second
BOOTTIME budget, with at most one identity-race retry. Native argv/format queries
have a read allowlist; stdout/stderr and owned descendants are bounded. Only the
pending option is read in the default profile. Optional user options/panes remain
explicit direct capabilities.

G0 evidence: `uv run --extra dev ./scripts/check` passed on CPython 3.13.7,
including 8 hand-assembled fixtures read without importing producer validation.
The wheel installed and imported in an isolated environment; all packaged
contract bytes matched the source bundles. Validation covers identity, partial
coverage, unaccepted/warming receipts, sample-start leases, mismatched clocks,
future/delayed remote proof, independent desktop evidence and refresh outcomes.
This evidence establishes the wire boundary, not native passivity or service
behavior. The separate fleet stream envelope makes sequence/gap/resync explicit.

T04 source evidence adds native simulations for generation/references/absence,
legacy fallback, profile coverage and fixed default-server environment. Owned
process tests cover output caps, UTF-8, deadlines, descendant cleanup and a
synthetic BOOTTIME suspend jump. An isolated tmux 3.7c smoke read returned complete
absence and one complete metadata sample in about 50 ms. Full native comparison,
passivity/race cases and installed direct CLI subsequently passed T05.

G1 reviewed producer source is `6a6c412`. The evidence records the tested wheel
digest and 12 owned native/artifact cases. Separate native reads confirmed full
identity/metadata, optional panes and null-versus-empty options. Repeated reads
preserved roster, attachment counts, windows and hooks. Native legacy fallback,
rename, disappearance, server restart/reused IDs and live-empty/absent distinction
passed. The installed CLI ignored an ambient alternate socket, returned typed
invalid-context failure and treated missing tmux as unsupported. Test cleanup
targeted only disposable sockets. Physical suspend remains untested; the source
clock-jump test establishes late-output rejection, not hardware sleep recovery.

Delivery A review: read/format allowlist has no lifecycle or format-job execution;
absence excludes permission failures; both native paths bracket generation and
full-reference roster; all accepted samples use one start-based BOOTTIME budget;
installed output was consumed by the independent schema/semantic reader. No
downstream frontend/service workaround was needed. This closes G1 and permits
T07; T06 remains an early frontend experiment before networking completion.

T07 source foundation adds one-job ownership, 2-second cadence/budget, 1-second
minimum spacing, start-based leases, distinct attempted/accepted counters,
unchanged-sample renewal, failure/history retention and expiry without scheduling.
Hints coalesce into one successor, spaced from the actual native start. Stopped
or mismatched job results cannot update a new publisher. Source gate now passes
42 test methods. These state tests do not establish live multi-reader sharing,
socket ownership, refresh tickets or daemon recovery; T08/T09 own those gates.

T08 endpoint primitives add a held publisher lease, private parent/socket modes,
same-UID peers, conservative abandoned-socket recovery and noncollecting bounded
exchange. Reads reject wrong host, UID, publisher, clock domain or request nonce.
Endpoint tests verify duplicate admission preserves the original socket, a live
unleased endpoint is never replaced, symlink/permission rejection, cleanup inode
ownership and oversized/incomplete responses. The source gate passes 48 methods.
The concrete owner loop and bounded fan-out now pass synthetic-source Unix
integration tests. Twenty probes share one attempt; watch/probe stream ordering
and malformed-request isolation pass. Valid near-cap documents exercise partial
frame preservation, one queued replacement/gap, nonce-reply protection and a
2-second stalled-reader cutoff. Source gate passes 55 methods. Sequence is per
connection; reads/control replies do not create global stream gaps. CLI/stdio
bridge and native sharing/recovery evidence remain the next T08/T09 work.

T08/T09 completed with owner-only stdio export, prepared read/refresh CLI and a
candidate user unit. Fragmented near-cap stream records, replay fencing, fixed
scope, client EOF and missing-service failure passed. Tickets require a native
attempt admitted after the request, coalesce on one eligible successor and retain
terminal outcomes for ten minutes. Admission caps at 64 tickets/1 MiB; terminal
lookup causes no collection. Source gate now covers 64 test methods.

G2 reviewed candidate source is `f61359e`; the evidence records its installed wheel
digest. A disposable systemd user unit with owned TMUX_TMPDIR observed the default
server despite an ambient alternate TMUX context. Twelve watchers and twenty
probes shared one attempt and preserved roster/attachments/windows/hooks. The
installed bridge echoed a fragmented probe nonce; EOF left the publisher alive.
Refresh completed post-request work, repeated terminal lookups did not collect,
and duplicate publishers preserved the held lease. Watchers held no session
alive; verified absence and restart/reused IDs were native cases. User-manager
restart changed publisher UUID and rejected old ticket lookup. Stop during an
owned blocked native read reaped descendants, removed only owned IPC and preserved
the native session. Missing tmux was unsupported with no current positives.

The measured owner cgroup used 11,112,448 bytes at one checkpoint; this is not
fleet capacity/peak acceptance. Reported query durations include independent
JSONSchema/semantic validation. Physical suspend remains untested; synthetic
clock-jump rejection is separate evidence. The unit/artifact were exercised in
temporary paths, not selected by chezmoi. This closes G2 and permits T10–T12.

T10 source is `5a31860`: the direct diagnostic client retains the released
inventory shape and 128-host Mesh limit, fixed ordering/aliases, strict provider
failure, bounded one-shot SSH and nonce-marked route reports. It does not read
prepared fleet state. Native local Snap diagnosis succeeded; the Starship route
was independently reachable. Full installed remote direct acceptance remains G3.

T11 source is `4808f76`: one owned non-PTY SSH bridge, first-byte/silence/control
bounds, held source epochs and matching send-based probes. Remote push frames
are candidates; only the matching probe's full snapshot renews conservative
local validity. Heartbeats/replays/delays cannot renew membership. Failure
invalidates immediately while retaining historical data. Owned stdio relays
exercise fragmentation, output caps, silence, child cleanup and clock jumps.
Review reopened T08 to publish every accepted unchanged receipt without changing
view revision; the source regression verifies publication before the 3-second
periodic heartbeat. The installed/native G2 tool was rerun against `f61359e`
and all 11 cases passed after that change. Actual two-host transport acceptance
remains pending.

T12 adapters now cover a local Unix subscription with same-UID/same-clock
absolute expiry, a prepared IPC facade with context/incarnation guards and a
display-only desktop scan. The scan contains no launch/focus/close code or handles.
Local client PID joins bracket tmux generation and creation time against exact
owner inputs. Niri capture/process child reads are bounded; malformed launch
metadata is unknown. Twelve inherited display-presence regressions and new join,
cached-read and import-boundary tests pass; the source suite has 100 methods.
Fleet scheduling, aggregate refresh tickets, user-manager desktop handoff and
two-host installed/native G3 are the next T12 work. No Rofi/chezmoi migration has
occurred.

T12 now has fleet projection and scheduling source. `1f46ba6` separates current
owner authority from desktop acceptance and rejects old context/input results.
Review reopened T11: `76221b2` invalidates remote leases on sequence gaps and
rejects regressing source counters/encoding clocks. `8246b25` groups parent refresh
requests over one child per owner; later requests require a successor, remote
completion requires post-request matching proof, and lost ticket notifications
use one bounded cached lookup. Desktop work waits for requested owner outcomes;
an obsolete join requeues rather than completing the ticket.

`d4bc721` adds the shared fleet loop, four concurrent remote setup slots,
independent Mesh/report/desktop workers, retry backoff, retained-document admission
and fixed-context IPC. Queries do not submit jobs. Source integration tests use
real private Unix endpoints with synthetic owners/scans, including cached sharing,
actual-start refresh ordering, missing-owner failure and desktop replacement.
Prepared CLI access and read-only watch framing are implemented after that commit.
Native two-host transport, desktop truth, normal/capacity resource measurements,
candidate context units, environment handoff and installed G3 remain unaccepted.
Rofi and chezmoi checkouts are unchanged by this work.

The current source gate covers 131 test methods. CLI tests additionally exercise
an explicitly launched fleet subprocess, missing cached endpoints, near-cap
fragmented output, incarnation replacement, trickled input and a stdout pipe
already full before the first write. Watch shutdown drains only already validated
output within its existing budget and accepts no buffered input after EOF.
Live read-only preflight confirmed Starship's Mesh selects `snap`, and that its
selected SSH route reaches Snap (`80H1VV3`) with ordinary strict host-key policy.
This is route connectivity evidence, not installed fleet G3 acceptance.

The candidate fleet template and explicit prepare/start/stop context operations
now capture a bounded private environment per desktop. They do not alter global
manager environment or enable old boot-bound instances. Scope conflicts, unsafe
files/FIFOs, registry contention and capacity fail explicitly. Stop preserves
other contexts and does not address native sessions or owner units. The source
gate passes 137 methods. Review also corrected the prepared RPC facade's default
deadline to the planned 250 ms; the owner/probe budgets remain independent.
Installed systemd environment parsing is now covered by a separate four-case
[context acceptance](evidence/2026-10-07-native-context-t12.json) at clean source
`31d6c68`. The exact wheel/template ran in a disposable user unit: literal quoting,
restart, scoped stop with child reaping, and the actual installed fleet entry point
with its captured context passed. A native finding corrected new-unit startup:
`reset-failed` may fail before a unit is loaded, while the following start must
succeed. The source gate passes 138 methods. This component evidence does not
close two-host, native source, desktop truth, resource or managed G3 acceptance.
See [service contexts](service-contexts.md).


The first two-host installed/native baseline at `3455a27` passed 14 included
functional/measurement cases with one exact wheel on both hosts; see
[partial G3 evidence](evidence/2026-10-07-native-fleet-g3-partial.json). Independent
native identities and conservative expiry, both SSH directions, causal refresh,
headless desktop failure, native failure on live transport, owner replacement,
delay/trickle/wrong-nonce faults, Mesh failure/recovery and scoped stop passed.
The ten-minute idle window started no new SSH connection. Warm cached RPC p95 was
6.26 ms on Snap and 5.50 ms on Starship; installed cached CLI p95 was 43.75/37.62 ms.
These are prepared-read measurements, not Rofi frame or visible notice acceptance.

Background resource acceptance **failed/pending**. Snap owner/fleet/owned bridge
mean CPU was 4.66/6.41/0.36 percent of one core; Starship was 2.39/3.01/0.14 percent.
Each endpoint exceeds the combined 5 percent target. Observed fleet cgroup RSS
plus the opposite endpoint's owned inbound bridge also exceeds the 64 MiB target.
The fault relay adds a Python process and is included, so a production-layout
profile still needs separation from relay overhead; transient RSS peaks and
encrypted SSH overhead remain unmeasured. Native reads were roughly 20 commands
per sample, revealing an unintended legacy fallback that is under investigation.
G3 stays open; no consumer or managed artifact has been selected.


The resource investigation reopened T04: under the fixed C locale, tmux's
read-client output replaced metadata tab delimiters with underscores, causing
an unintended legacy fallback and potentially changing Unicode metadata. The
read prefix now forces UTF-8 with `-u` while retaining the C locale for diagnostic
classification and the explicit default server. This changes no native options,
hooks or attachment/lifetime ownership.

Reviewed source `84b5767` passes 138 source methods and clean-source G1/G2 reruns.
The expanded G1 has 14 native/artifact cases, including exact Unicode names and
five native commands for a simple batched sample (previously twenty). The installed
CLI independently preserves Unicode under a C locale. All eleven installed owner
sharing, refresh, restart, absence and stop/reap cases pass after the correction.
The latest evidence links above record each wheel digest; prior acceptance files
remain historical records. Post-correction two-host CPU/memory/resource acceptance
was then rerun at `5eacd1e`, after the fleet stopped rebuilding unchanged
projections on every 50 ms tick. Freshness, source cadence and per-query validation
remain required.

The [clean two-host profile](evidence/2026-10-07-native-fleet-optimized-g3-partial.json)
passes all fourteen included cases. Native reads fall to 1,485/1,480 commands over
ten minutes, from 5,940/5,920. Cached RPC p95 is 4.03/4.15 ms; installed cached CLI
p95 is 40.92/35.53 ms on Snap/Starship. Plain installed bridges replace the fault
relay before measurement. Snap started one additional SSH connection during the
profile; Starship started none. These numbers do not establish encrypted wire
overhead, graphical timing or capacity.

Mean combined CPU meets the normal target: Snap 4.82 percent and Starship 2.66
percent of one core. Each includes its owner/fleet cgroups and the opposite
endpoint's bridge serving its outbound fleet connection. Fleet cgroup sampled
peak RSS is 61.46/60.37 MiB; the associated opposite-endpoint bridge adds about
18 MiB throughout the profile. The 64 MiB fleet/owned-children memory target still
fails. Peak fleet samples contain three processes, so further investigation must
identify the actual child and parent footprint before changing process choices.
G3 remains open for memory, declared capacity, native desktop truth/replacement,
physical sleep/wake and the other explicitly recorded limits.

At `f11de93`, the [explicit fixture dispatch diagnostic](evidence/2026-10-07-rofi-feed-dispatch-t06.json)
adopts a revision while idle in 52/57 ms and during sustained typing in 49/30 ms
on Snap. The selected full fixture reference is preserved in both phases; filter
and caret remain intact. Native during-input captures show revision 3. The
[completion-only comparison](evidence/2026-10-07-rofi-view-dispatch-t06.json)
still shows revision 2 during sustained typing, despite the prepared revision 3.
This identifies event dispatch as a material UI latency issue. It uses private
Rofi symbols in a temporary diagnostic library, so it accepts neither a supported
integration nor T14/G4. All 142 source tests pass; no Rofi or managed candidate
has been selected.

Follow-on source `fd531c4` also reuses the desktop scheduler's input hash between
source/health events, with owner lease boundaries invalidating that hash. Frames
and desktop-result admission still perform current-time validation. Source checks
pass 143 tests, including expiry, disconnect, changed-owner and publication-order
regressions. A dirty-source two-host functional investigation passes all thirteen
included cases. Clean installed source `c413094` is being profiled separately;
its tool records owned process footprints at each sampled service memory peak.
The [clean installed profile](evidence/2026-10-07-native-fleet-input-cache-g3-partial.json)
has now passed all fourteen included cases. It records at least ten minutes on
each host, 1,485 native commands per endpoint and no new SSH connections in the
measurement window. Cached RPC p95 is 3.64/3.99 ms and installed cached CLI p95 is
40.51/35.55 ms. Combined mean owner/fleet/associated remote-bridge CPU is
4.40/2.43 percent of one core on Snap/Starship.

Memory remains unaccepted. The conservative sum of fleet and associated bridge
sampled maxima is 67.23/77.79 MiB, exceeding the initial 64 MiB target. The Starship
fleet peak contains a 27.32 MiB fleet process, 10.95 MiB SSH child and 20.69 MiB
Python child. The headless worker's process layout identifies the latter as Mesh
CLI work; the retained record contains process names, not raw argv. The opposite
endpoint's associated bridge adds about 18.84 MiB. This is an explicit process
cost, not foreground network latency. Resource budgets/process choices require
review, and declared capacity remains separate from these two-owner samples.

Clean installed source `fd47581` now passes nine [native local desktop cases](evidence/2026-10-07-native-desktop-t12.json)
on Snap. Independent native UID/hostname/clock, session identity and tmux client
reads join an actual owned Kitty window to the complete reference. Live switching,
rename, owner replacement, actual owned compositor-proxy socket inode replacement,
endpoint loss and headless context isolation pass. Viewer/service stop preserves
session creation times, windows, hooks and attachment counts. The previous session
after switching loses its positive but remains unknown on conflicting original
argv; this does not claim absence from conflicting evidence. The ordinary Niri
endpoint was unchanged, and owned fixture/viewer cleanup was verified.
See [desktop acceptance scope](native-desktop-acceptance.md). This closes those
local T12 cases, not G3: remote manual SSH truth, capacity, physical sleep/wake,
memory and other recorded native/managed limits remain open.

T06's clean [native mode prototype](evidence/2026-10-07-rofi-native-mode-t06.json)
at `4a2ca8b` loads through installed Mode ABI 7 with no preload. Both fixture
variants adopt idle publication in 45/26 ms and active-input publication in
28/50 ms while preserving exact selection, filter and caret. Inspected native
captures show the new notice. This closes the early interaction experiment for
the installed Rofi 2.0.0 build. Private script-factory/view hooks remain explicit
dependencies requiring a reviewed production integration; T14/G4 and end-to-end
ticket/notice timing remain open. Source checks pass 143 tests.

Clean source `ef94ebe` also passes seven functional [installed capacity cases](evidence/2026-10-07-installed-capacity-t12-partial.json):
sixteen current owners, thirty-two shared watchers, explicit admission failures,
logical queue bounds, a near-cap complete aggregate and scoped stop. The fixture
uses synthetic facts/catalog and real installed local stdio bridges, with no
native tmux or SSH process. Its result is `failed_resource_target`: sampled
fleet/bridge RSS reaches 307.65 MiB before SSH costs, exceeding 256 MiB. Maximum
readers and large frames were separate phases, so their simultaneous maximum load
and full native capacity remain open. See [capacity scope](installed-capacity-acceptance.md)
and [resource decision review](resource-design-review.md). Source checks pass 143
tests and include the new tool; no budget has been silently raised.

The user subsequently selected review and validation of 96/768 MiB fleet budgets
for the current Python design. The [recorded decision](resource-design-review.md#selected-direction)
preserves the original failed results and all owner/CPU/freshness/logical bounds.
Future profiles must name the selected candidate ceiling and retain their scope
limits. Existing headless/local-bridge samples fitting those ceilings do not close
normal native desktop work, simultaneous maximum-reader/frame load or actual
SSH capacity acceptance.

The clean `15d3203` [selected-budget fixture rerun](evidence/2026-10-07-installed-capacity-reviewed-t12-partial.json)
passes seven included functional cases and records a 307.01 MiB sampled
fleet/bridge peak against the selected 768 MiB candidate. Its `passed_partial`
result retains the explicit no-SSH/synthetic and separate-load-phase limits;
it does not close full native capacity. The initial failed evidence is unchanged.

Clean source `4792174` passes fifteen [two-host functional cases](evidence/2026-10-07-native-fleet-membership-g3-partial.json)
with the same installed wheel on Snap/Starship. Native Mesh host removal/restore
and equivalent route replacement require new connections and post-change proofs
while preserving native generation and publisher identity. Both private fixture
directories were absent after cleanup. Warm RPC p95 is 4.34/4.37 ms and installed
CLI p95 is 41.82/38.48 ms; this run does not repeat the background profile.
Physical suspend has a [concrete acceptance preparation](native-suspend-acceptance.md),
including read-only power-interface preflight, wake/supervisor requirements and
separate clock/receipt/native-survival evidence. No host suspend was executed.
Remote qualified/manual desktop truth, actual SSH capacity with simultaneous
near-cap readers, desktop-inclusive resource profiles and physical sleep/wake
remain the next producer gates. Consumer migration and managed rollout remain
pending.
