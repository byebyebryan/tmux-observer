# CPU performance pass

2026-10-09. The fleet bookkeeping pass is accepted as Observer 0.4.0a1 / Plus
0.10.0a2. Its fixed bookkeeping fixture improved about 50%, while comparable
ordinary Snap profiles moved from 4.9048% to 4.4701% of one core. Different
working desktops prevent treating that ordinary difference as causal savings.
This pass targets whole-service work rather than enlarging resource budgets.

## Baseline and remaining work

A separate, uninstrumented sixty-second sample of the selected ordinary Snap
processes measured owner/children 1.6216%, fleet/children 2.6887% and the incoming
bridge serving Starship 0.3333%. That physical-host total is 4.6436%; it is not
the release harness's logical-reader associated-bridge accounting. Fleet self
CPU was 2.1000%, with its main thread 1.5166% and desktop worker 0.5667%.
SSH self CPU was 0.0333%, already included in fleet accounting.

Short nonblocking stack samples repeatedly land in structural/schema validation,
JSON processing, local attachment delivery and process reads. Missed samples
make those samples directional attribution, not precise CPU percentages.
The current owner normally invokes tmux four times each two-second cycle.
Those batches contain 24 subcommands with nine sessions, including two pending
annotation subcommands per session. Remote C3 scans remain every three seconds;
unchanged Mesh still starts its public CLI every fifteen seconds.

## Decisions and execution

1. Add a fixed document-pipeline benchmark that includes owner state/delivery,
   framing, bridge validation and reader admission, alongside the existing fleet
   fixture. Run the same input/harness/interpreter against the frozen baseline
   and candidate; record hashes, counts, output equality and CPU separately.
2. Reduce structural traversal allocations and consolidate freshly decoded
   structural checks with immediate semantic admission. Raw bytes must still
   pass framing, pre-parser depth/node bounds, duplicate-key/numeric/Unicode
   checks, complete tree bounds, schema, scope and encoded-size limits.
   Public dictionary validators continue checking caller-owned mutable inputs.
   Private checked admission must be constructed by the actual decoder/checks,
   never by a public bypass flag or a caller's claimed revision.
3. Review outgoing checked-frame encoding and native command batching against
   the measured pipeline. Reuse only producer-owned checked state/bytes; changed
   clocks, receipts, envelope variants and capacity still get their own guards.
   Native sharing must retain both membership/incarnation brackets, original
   deadlines and the independently usable roster when attachments fail. Keep
   only changes with measured benefit and manageable failure semantics.
4. Review Mesh's supported public interface. The current contract offers list
   and report-route, without a change subscription. Do not import provider
   internals or poll private files to invent notification authority. Record the
   disposition if avoiding CLI launches requires a separately accepted provider
   extension. Fresh remote C3 matching remains unchanged in this pass.
5. Freeze an exact producer/consumer pair after source review; independently
   accept native passivity/recovery/actions, ordinary two-host resources, declared
   capacity and Snap graphical behavior. Publish immutable artifacts, apply only
   owned chezmoi targets, verify both hosts, exercise serial paired rollback and
   preserve ordinary sessions/hooks plus unrelated source/live drift.

Two-second native cadence, ten-second source leases, three-second remote proofs
and desktop scans, freshness/uncertainty semantics and all seven wire contracts
remain fixed. Readers and heartbeats start or renew no native work. Existing
96/768 MiB and 5% resource ceilings remain hard gates. The objective is a measured
whole-service decrease; a synthetic percentage alone does not establish it.
Physical suspend remains optional under the always-on scope. Only Snap receives
foreground input; Starship is in active use.

## Review risks

| Risk | Required protection |
| --- | --- |
| Mutable/exotic Python values defeat a reused structural check | Public validators retain complete checks; exotic containers retain their defensive fallback; decoded plain values get semantic checks before callbacks |
| Faster traversal changes occurrence/depth/byte limits | Differential/adversarial boundary tests, cycles, duplicate strings/keys, malformed numbers and nested independent size limits |
| Checked input weakens scope, ordering or proof | Existing adverse admission/provenance/replay/expiry tests; raw network and local inputs remain untrusted |
| Optional native collection invalidates the primary roster | Independent failure/deadline tests and native acceptance before enabling sharing |
| Mesh optimization loses policy or route changes | Public provider contract only; preserve explicit polling bound unless a separately reviewed extension is accepted |
| Synthetic timing is presented as whole-service savings | Separate fixed pipeline attribution from ordinary installed two-host profile |
| Deployment acceptance overlaps peer rollback | Await each operational phase; serialize recovery and paired rollback |

## Checkpoints

| Checkpoint | Exit evidence | State |
| --- | --- | --- |
| CP0 | Reviewed design, full-path baseline and work attribution | In progress |
| CP1 | Structural/decoded admission savings with public/adverse regression gates | Pending |
| CP2 | Outgoing/native/Mesh review and measured implementation or explicit disposition | Pending |
| CP3 | Frozen producer, independent pinned consumer, native/resource/capacity/Snap UI | Pending |
| CP4 | Published artifacts, scoped both-host deploy/recovery/rollback/actions and preserved source drift | Pending |
