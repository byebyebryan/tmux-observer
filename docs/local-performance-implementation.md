# Attachment-driven local Kitty implementation

2026-10-08. Active goal following the user-selected
[local performance scope](local-performance-design.md). Commit reviewed
checkpoints as work progresses. Ordinary sessions and SSH masters are preserved;
foreground acceptance uses Snap while Starship remains in active use.

## Contract and source review

The released default adapter schedules full process/window matching every three
seconds in `src/tmux_observer_client/fleet.py`. Its local native association
input already contains current client PIDs, process birth identities and full
session references. The current matching policy walks terminal descendants.
Native receipt changes do not need to repeat that work for stable clients.

The existing C3 desktop receipt describes a fresh capture and expires after ten
seconds. Fleet v1 requires current C3 evidence for its known `localViewer`
positives. Keep these semantics and the frozen contract bundles intact. Fleet
v1 explicitly permits bounded extensions, so add a separately versioned
`localBindings` extension on the local host rather than reinterpret a known
desktop lease. An old consumer can ignore that extension and sees conservative
legacy viewer state.

The new `bindings-v1` boundary publishes retained display associations, not
fresh desktop presence. It carries local host/publisher/server/context/clock
scope, independent owner and native-association expiry bounds, preparation time,
and complete per-session coverage. Each resolved association preserves its
original discovery time. Native renewal can update the dependency receipt but
cannot update that discovery time. No process IDs, window IDs, raw captures or
action handles cross this boundary.

Only a current complete local client sample can support a retained positive or
the zero-client case. Count disagreements between independently sampled owner
and client inputs remain unknown. Failure, expiry, missing coverage, changed
source/context and ambiguity revoke current claims. Positive retained bindings
project as qualified display observations in the new frontend; they never
become C3 `confirmed` facts. Native `Attached` remains independent.

Discovery follows each new client's bounded parent chain to a uniquely matching
Kitty compositor window, with process-incarnation and opening/closing capture
guards. It need not traverse every terminal descendant. A retained binding is
keyed by client process incarnation within its full source/context scope; the
client's current session is a separate mapping. Bootstrap discovers existing
clients. New unresolved clients receive at most three settling attempts, spaced
at least one second apart. An explicit desktop refresh permits rediscovery.
Normal snapshot/watch reads do not schedule either operation.

Remote desktop matching remains on its existing independent schedule and
fresh-capture contract. Its cost must be reported separately: local savings do
not establish remote savings. Kitty tab/internal-window relocation without a
native client change is an accepted limitation. Focus/close retain independent
current target validation in the action package.

## Checkpoints

| Checkpoint | Work and acceptance | State |
| --- | --- | --- |
| LP0 | Source review, bounded design, contract choice and ordinary-session constraints | Reviewed design |
| LP1 | Pure bindings contract, independent fixtures/reader, immutable old bundles; bounded new-client discovery/cache | Contract accepted at source; discovery/cache pending |
| LP2 | Prepared fleet integration, receipt-only renewal without discovery, independent remote schedule, explicit refresh/recovery | Pending |
| LP3 | Tmux Plus consumes qualified retained bindings with local expiry/watch guards; native/action authority unchanged | Pending |
| LP4 | Frozen artifacts, native open/close/switch/bootstrap acceptance, local and normal-fleet CPU/update measurements, Snap GUI | Pending |
| LP5 | Publish accepted pair, scoped chezmoi selection/recovery and rollback checks on both hosts | Pending |

Source, packaged, installed/native, measured and managed acceptance remain
separate. Record exact artifacts and failed evidence without upgrading a passing
source test into runtime acceptance. Physical suspend is outside this always-on
pass.

### LP1 contract checkpoint

`bindings-v1` has twelve independent valid/invalid fixtures and a reader that
imports no product implementation. The existing six contract bundles are
unchanged. Pure validation accepts old discovery times with current independent
native receipts, and rejects expired/extended dependencies, detached positives,
unsupported absence, duplicate identities and action handles. The source gate
passes 329 tests, all contract readers, compile, Ruff and whitespace checks.
This accepts no native discovery, consumer projection, artifact or deployment.
