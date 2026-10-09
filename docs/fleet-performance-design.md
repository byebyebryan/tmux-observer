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
| FP0 | Design/source review; reproducible fixed-input baseline and function/counter attribution | In progress |
| FP1 | Checked input/accounting, unchanged Mesh, facts versus receipt work; adverse scope/expiry/capacity regressions | Pending |
| FP2 | Remote proof scheduling and remote viewer disposition; fixed-input before/after comparison | Pending |
| FP3 | Frozen producer native/recovery/resource/capacity acceptance; independent pinned consumer and Snap GUI | Pending |
| FP4 | Published paired artifacts; scoped both-host bytes/readiness/recovery/rollback and preserved source drift | Pending |

Use identical synthetic input streams for causal function-work comparisons;
measure ordinary ten-minute native fleet separately. Report owner, fleet,
associated bridge, viewer jobs, proofs, wire payload and CPU independently.
Native ordinary-session/generation/hook preservation and query deadlines remain
required. Preserve failed/partial evidence and exact runtime identities.
