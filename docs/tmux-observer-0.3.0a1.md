# Tmux Observer 0.3.0a1 local Kitty retention

Local discovery now follows new native client incarnations to a uniquely matching
Kitty window, rather than repeatedly walking every terminal tree. Existing
clients bootstrap once; session switches reuse the match with the current full
reference. Kitty close revokes it through native detach. Unresolved clients
receive at most three settling attempts. Explicit Refresh permits rediscovery.
Local-only readers have no periodic desktop matching job. Remote matching and
network subscriptions retain their existing independent schedules.

The additive `bindings-v1` contract carries qualified retained display evidence
with a current native lease and original discovery time. It does not extend C3
fresh-capture leases or supply window/action authority. Unknown, failure, expiry,
changed publisher/context and count disagreement remain explicit. Kitty
tab/internal-window relocation without a native client change is an accepted
limitation. Actions independently resolve and validate current targets.

Runtime freeze `5a4aec9c7f4208d47dd35816c1350a61538d0076` builds wheel SHA256
`e98051a8f93373790082df8aeae462c63498b2bc9c7454eca62aec146c5b6945`
identically twice. The 172-member wheel contains 77 Python modules in three roots
and seven contract bundles. Existing six bundles and nineteen action modules are
byte-unchanged. Descriptor format 3 adds explicit bindings coverage; old formats
remain verifiable for rollback. The [descriptor](evidence/2026-10-08-local-performance/core-candidate.json)
retains `built_unaccepted`; acceptance is recorded independently here.

The full source gate passes 356 tests and [runtime CI](https://github.com/byebyebryan/tmux-observer/actions/runs/37891286820).
The [native records](evidence/2026-10-08-local-performance/) pass eleven
attachment, ten Snap binding lifecycle, four simulated recovery and eleven
installed capacity cases. Local and actual SSH action checks pass. Thirty
installed frontend CLI cases pass on Snap/Starship with the exact 0.9.0a1
consumer. All fixtures are removed; ordinary native references, generations,
hooks and SSH masters are preserved. Starship receives no foreground input.

The [isolated local fixture](evidence/2026-10-08-local-performance/native-bindings-snap.json)
uses two sessions/one client for 120 seconds: 1.568% combined CPU (owner 0.699%,
fleet 0.868%), versus the previous wheel's 3.025% on a sequential run of the same
fixture. It performs zero rediscovery or periodic desktop jobs; warm RPC p95 is
0.719 ms. This is a fixture comparison, not controlled causal attribution or
ordinary-fleet CPU savings.

The [ten-minute ordinary two-host profile](evidence/2026-10-08-local-performance/normal.json)
passes the unchanged five-percent combined ceiling: Snap 4.9048%, Starship
2.9832%, including associated bridges. Snap has little margin. Both endpoints
perform zero local rediscovery; independent remote C3 jobs continue. Fleet and
associated-bridge sampled RSS is 69.35/56.84 MiB against 96 MiB; owners remain
below 64 MiB. Capacity peaks at 496.77 MiB against 768 MiB for sixteen synthetic
owners/fifteen real SSH links/thirty-two readers. Capacity CPU and unsampled
memory peaks are not established. Physical suspend remains optional/unverified.

Failed timing/baseline diagnostics, the first failed fleet CPU gate and a
superseded interrupted profile remain separate records in the
[implementation ledger](local-performance-implementation.md). Profiling exposed
and fixed a scheduler regression that copied the full fleet on every quiet loop
to check topology. Full outgoing validation, mutable ownership and expiry guards
remain intact. Packaged/native acceptance does not establish managed selection;
that belongs to the paired chezmoi operation record.

The exact accepted wheel is published as
[0.3.0a1](https://github.com/byebyebryan/tmux-observer/releases/tag/v0.3.0a1)
and selected with Plus 0.9.0a1 on Snap/Starship. The independent
[paired managed record](https://github.com/byebyebryan/dotfiles/blob/main/docs/tmux-observer-local-performance-operations.md)
passes all installed bytes, leases/native parity, restart recovery, performed
rollback/reselection and guarded lifecycle checks. Ordinary references,
generations, hooks and unrelated desktop/Agent controls are preserved.
