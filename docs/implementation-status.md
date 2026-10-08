# Implementation status

Updated: 2026-10-07. Goal: Deliveries A–E, with reviewed commits as work progresses.
The design/backlog baseline is commit `a4fba75`.

| Delivery | State | Evidence |
| --- | --- | --- |
| A: standalone producer | Accepted: T01–T05; G0/G1 passed | Pure API, exact bundles, independent reader, 32 test methods and 12 native/installed cases; [G1 evidence](evidence/2026-10-07-native-collector-g1.json) |
| B: owner service | Accepted: T07–T09; G2 passed | 64 source test methods, bounded tickets/stdio, 11 installed/native cases; [G2 evidence](evidence/2026-10-07-native-owner-g2.json) |
| C: fleet service | In progress: T10/T11 source and T12 scheduler/CLI | Shared aggregate, independent desktop jobs, causal grouped refresh and prepared CLI; units/context handoff and native fleet G3 pending |
| D: Rofi client | Planned; T06 experiment completed, automatic adoption unresolved | [Native experiment](rofi-interaction-probe.md); filter/caret preserved, continuous-input/idle timing not accepted |
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
