# Fleet change-driven work

2026-10-08. User-authorized goal after the local Kitty optimization. The selected
baseline is Observer 0.3.0a1 (`5a4aec9`) / Plus 0.9.0a1 (`98d2882`). Native,
desktop, owner and transport clocks remain independent. Snap alone may receive
foreground input; Starship remains in active use. No physical suspend, native
hooks/configuration changes or ordinary session/SSH cleanup.

## Review and intended changes

The baseline's local fixture measures 1.568% combined CPU versus a sequential
prior-wheel fixture's 3.025%. Its ordinary fleet measures 4.9048% Snap / 2.9832%
Starship; these are different working-desktop runs, not fleet savings. Snap's
owner uses 1.6051%, fleet and children 3.1532%, associated bridge 0.1465%. The
fleet figure includes SSH children and does not isolate transport CPU.

Source review finds repeated work at these boundaries:

| Work | Intended simplification | Preserved requirement |
| --- | --- | --- |
| Owner envelope admission and `RemoteState.receive` both validate the same frame | One checked admission path; standalone receive still validates | Untrusted wire always receives complete bounds/semantic checks |
| Capacity checks encode current/retained documents repeatedly | Account validated incoming bytes and cached immutable retained sizes | Capacity checked before retaining data; replacement cannot exceed pool |
| Owner, attachment and desktop receipt renewals dirty full projection/material hashes | Distinguish material dependencies from envelope/lease dependencies; reuse stable parts | Expiry, health/failure, context, publisher, generation and route changes invalidate immediately |
| Every Mesh reload recreates host descriptions | Preserve unchanged validated topology objects | Failed/present provider never becomes local-only; route/policy changes remain visible |
| Every accepted remote attempt can force an immediate probe | Immediate proof for material/scope/gap changes and explicit refresh; retain bounded scheduled proofs | A stream heartbeat never renews remote facts; matching nonce and send-based proof remain required |
| Periodic remote viewer discovery | Review supported candidates and cheap invalidation evidence before choosing implementation | Retained evidence cannot impersonate fresh C3 capture or action authority |

Keep the existing seven contract bundles, public validators, observation cadence,
proof/deadline ceilings, source failure semantics and action modules unchanged.
Never cache by a visible name/PID alone or assume a peer is current because SSH
is connected. Internal validated objects belong to the service; mutable public
results must not alias its retained data. Reads/subscribers schedule no jobs.

## Remote viewer review boundary

Local native attachments identify client incarnations. A remote owner count
cannot identify an endpoint-local SSH process. A manual SSH shell can switch
tmux sessions without replacing SSH. New tabs, process exec/reparenting,
same-count replacement, title ambiguity and publisher/generation/route changes
must therefore be reviewed explicitly. Common Kitty open/close alone cannot
justify reusing old `confirmed`/`none` C3 observations indefinitely.

Prefer bounded internal discovery caching with independent current evidence if
it can preserve existing C3 semantics. Otherwise a retained remote display mode
needs its own explicit contract and consumer acceptance; do not silently extend
old leases or weaken matching. Record the review disposition even if that
larger contract is deferred in favor of the independently useful fleet pass.

## Checkpoints and acceptance

| Checkpoint | Exit evidence | State |
| --- | --- | --- |
| FP0 | Design/source review; reproducible fixed-input baseline and function/counter attribution | Complete |
| FP1 | Checked input/accounting, unchanged Mesh, facts versus receipt work; adverse scope/expiry/capacity regressions | Complete; 367 tests and contract/style checks pass |
| FP2 | Remote proof scheduling and remote viewer disposition; fixed-input before/after comparison | Complete; frozen native acceptance pending |
| FP3 | Frozen producer native/recovery/resource/capacity acceptance; independent pinned consumer and Snap GUI | Complete within the declared always-on scope |
| FP4 | Published paired artifacts; scoped both-host bytes/readiness/recovery/rollback and preserved source drift | Complete |

Use identical synthetic input streams for causal function-work comparisons;
measure ordinary ten-minute native fleet separately. Report owner, fleet,
associated bridge, viewer jobs, proofs, wire payload and CPU independently.
Native ordinary-session/generation/hook preservation and query deadlines remain
required. Preserve failed/partial evidence and exact runtime identities.

## Implementation review and bounded result

The fixed stream has two owners, ten sessions each and 300 two-second cycles:
one local receipt, one remote candidate and matching proof each cycle, unchanged
Mesh reloads every seven cycles, negative desktop batches every two cycles and
two material renames per owner. The same harness on installed 0.3.0a1 and the
candidate uses the same Python 3.14 interpreter. Baseline process CPU is
4.138/4.229 seconds; candidate 2.069/2.124 seconds. Work counts fall from
750 to 303 input hashes, 450 to 153 projections and 300 to 3 material hashes.
Both produce revision 3. These synthetic bookkeeping results do not establish
whole-service CPU savings or network traffic reduction.

Repeating that harness on the frozen installed 0.4.0a1 wheel uses 2.088/2.091
CPU seconds with the same counts and revision. Its recorded runtime module
digests match the candidate descriptor exactly. The earlier development-tree
profiles remain available separately.

The separate unchanged-owner proof simulation uses installed baseline and
candidate wheels with two-second samples, fifty-millisecond receive ticks and
a five-millisecond proof RTT over 600 logical seconds. Matching proofs fall from
300 to 197; candidate stream frames renew no validity by themselves. Encoded
request/reply/push bytes total 949,837 versus 774,353 (18.5% less). These are
synthetic one-session application payloads, not encrypted SSH bytes or a working
desktop traffic measurement. Both runs retain the same 299 source pushes.

Admission returns a private checked document and byte sizes already calculated
by the complete wire validator. Capacity is reserved before copying retained
state. Standalone receives still validate dictionaries; scope, ordering, nonce
and proof deadlines remain mandatory after admission. Confirmed/header state
owns its copies. The decoder-owned input is borrowed only within the synchronous
admission/receive call, never retained as public or queued mutable state.

Confirmed payload comparisons create internal fact and desktop-input revisions;
they do not trust declared producer revisions. Receipt-only updates replace
small owned headers and binding receipts. Facts, visibility/health transitions
and actual expiry boundaries rebuild and hash the projection. Complete outgoing
frames and adapter results remain checked. Activity changes material but does
not invalidate desktop input. Native attachment incarnations still invalidate
that input, even with unchanged counts. Unchanged Mesh topology keeps its
descriptions and desktop epoch; route health timestamps update the scheduler's
Mesh snapshot without replacing a live association. Configured route, policy,
scope or provider failures still fence it.

Unchanged remote samples retain the scheduled three-second proof. They never
adopt candidate facts or renew translated expiry. Changed checked facts, gaps,
new scope and completed explicit refresh request immediate proof; the existing
matching nonce, two-second send-based deadline and safety margin remain intact.

Remote viewer retention is deferred deliberately. Fresh C3 matching currently
checks captured Niri windows, title/metadata, SSH arguments and process ancestry,
then revalidates process births and window identities. A remote attachment count
does not identify an endpoint SSH process. Manual SSH can switch sessions inside
the same shell; exec can change arguments without changing process birth; new
tabs or children can introduce competing evidence. Keeping old C3 `confirmed`
or complete-absence rows would therefore weaken the contract. A future retained
remote mode must name its weaker display evidence and independent invalidators,
then receive producer and consumer acceptance. Current remote scans and fresh
action-time checks remain unchanged in this pass.

The source gate passes 367 tests and all seven bundle/style checks. Runtime
`ad6073953c3e1f4237950fffc53b8e0a111120fa` builds Observer 0.4.0a1 twice with
SHA-256 `efb1e7b72e0128bf45c10803d366304f7b108aec5ac5aaf2fffafa4efb23d880`.
The later lockfile/harness/evidence commits do not replace that frozen wheel.
The two-host native fixture passes fifteen recovery/query/passivity cases;
its `passed_partial` result explicitly omits resource and graphical acceptance.
The independent four recovery simulations, eleven native binding cases and
seven actual remote desktop cases pass. Capacity passes eleven cases with
fifteen real SSH links and thirty-two readers; the conservative sampled
fleet/SSH/associated-bridge peak is 500.44 MiB against 768 MiB. Its partial label
preserves the synthetic-owner and two-physical-host limits. The current frozen
consumer is 0.10.0a1, independently pinned to all 78 runtime modules; 293 tests
and 23 Snap graphical cases pass. The [ordinary ten-minute profile](evidence/2026-10-09-fleet-performance/normal.json)
passes: combined owner/fleet/associated-bridge CPU is 4.4701% Snap / 2.4262%
Starship, under the unchanged 5% gate. Owner CPU is 1.8682% / 0.8013%; fleet
and children 2.4703% / 1.3004%; associated bridge 0.1315% / 0.3245%.
Fleet/children/associated-bridge sampled RSS is 81.39 / 79.71 MiB against 96;
owners remain below 64 MiB. One-second samples can miss transient peaks.

The actual profile has 205 / 198 matching proofs, zero new SSH connections,
199 remote desktop jobs each and zero local binding rediscovery. Remote owner
payloads are 3,345,213 / 2,957,202 bytes over at least 600 seconds each; these
are application payloads, not encrypted wire traffic. Native cadence and
query deadlines hold; ordinary references, generations and hooks survive.
Fleet CPU is lower than the previous ordinary run's 3.1532% / 1.8755%, but
working desktops/activity differ, so that comparison is not a causal savings
estimate. The controlled fixed-input result above establishes the bookkeeping
reduction.

## Final paired managed result

The selected pair is Observer 0.4.0a1 / Plus **0.10.0a2**. Frontend a1's immutable
tag retained the old CI filename even though its main-branch review fixed it;
that tag failed the download step. A2 includes the correction in frozen runtime
`1b45adad7488bc077b01b7e94a61fc2b2265abb4` and passes main/tag CI. Its packaged
frontend Python/native/Observer-pin bytes are identical to a1; Observer's exact
wheel, seven bundles, resource results and native acceptance remain unchanged.
Independent a2 wheel and managed Mod+G checks each pass all 23 Snap GUI cases.

Both endpoints select the published pair through seventeen scoped chezmoi
targets. Checks verify all 173 Observer members and 299 Plus files/manifest,
current local native bindings and independent fresh remote desktop evidence.
Owner/reader restart, paired rollback to 0.3.0a1/0.9.0a1 and exact reselection
pass. Installed full-reference lifecycle checks pass from both endpoints. Final
native, fresh and prepared views agree on nine Snap and ten Starship sessions,
with matching generations. Ordinary references/hooks and unrelated Agent/Kitty
controls survive. Starship receives no foreground input.

The initial a1 Starship recovery call overlapped Snap rollback and timed out;
serial recovery passed after the peer was steady. All final a2 recovery checks
are serialized and pass without relaxing readiness. Source reconciliation keeps
private Agent history and the unrelated Starship Kitty source edit; it publishes
only the isolated intended chezmoi selection and evidence. Physical suspend and
retained remote viewer contracts remain explicitly deferred.
