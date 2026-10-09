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
| FP3 | Frozen producer native/recovery/resource/capacity acceptance; independent pinned consumer and Snap GUI | Pending |
| FP4 | Published paired artifacts; scoped both-host bytes/readiness/recovery/rollback and preserved source drift | Pending |

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
