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
| LP1 | Pure bindings contract, independent fixtures/reader, immutable old bundles; bounded new-client discovery/cache | Source accepted; passive Snap bootstrap diagnostic passed |
| LP2 | Prepared fleet integration, receipt-only renewal without discovery, independent remote schedule, explicit refresh/recovery | Source accepted; frozen/native acceptance pending |
| LP3 | Tmux Plus consumes qualified retained bindings with local expiry/watch guards; native/action authority unchanged | Source and frozen consumer accepted |
| LP4 | Frozen artifacts, native open/close/switch/bootstrap acceptance, local and normal-fleet CPU/update measurements, Snap GUI | Accepted; see 0.3.0a1 release record |
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

### LP1 discovery/cache checkpoint

The new adapter discovers only new client ancestry, brackets process identity
and compositor captures, and retains its discovery time through native receipt
renewals. Fourteen new cases cover bootstrap, detach/replacement, session
switching, count races, failure/expiry, three settling attempts, explicit
rediscovery, context/publisher change, late-result rejection, shared-process
ambiguity and process/window reuse. The source gate passes 343 tests and all
other required checks.

A passive diagnostic against Snap's current prepared owner/native-client inputs
resolves seven local associations and the one zero-client session, with no
unknown rows. Bootstrap performs one discovery job in 2.036 ms wall time; forty
successive preparations perform zero additional discovery jobs and average
0.377 ms process CPU per preparation. These are descriptive uncommitted-source
microbenchmarks with existing native clients, not a whole-service CPU profile,
frozen artifact acceptance or an open/close graphical test. Running services
remain on the previously selected pair.

### LP2 prepared fleet checkpoint

The fleet schedules retained local preparation from local native inputs and
bounded settling retries. A local-only reader has no periodic C3 desktop job.
Remote jobs retain their existing fresh-capture schedule and evidence classes;
their local legacy rows remain unknown. Explicit desktop refresh rediscoveries
use the same serialized adapter and preserve existing ticket/deadline behavior.
Context/clock replacement invalidates retained bindings independently. Reads
project only accepted prepared data and include binding expiry in their next
revalidation boundary.

Eight additional source cases cover independent C3/binding evidence, enclosing
scope/count/coverage guards, same-count client replacement, stale/late results,
mutable aliases, expiry despite renewed native deliveries, quiet renewal and
remote evidence compatibility. The full source gate passes 351 tests and all
other required checks.

An isolated Snap local-only fleet diagnostic publishes seven retained-open
rows, one unresolved row and one zero-client row from current installed native
owner inputs. Fourteen initial clients need one shared discovery; seven clients
without a resolved local window receive the remaining two settling attempts.
Discovery then stops at three jobs/twenty-eight client attempts while native
receipts continue renewing. There are zero periodic C3 jobs and no publisher
exceptions. The owned fleet endpoint/thread are removed. This eight-second
working-source diagnostic is not artifact, graphical or CPU acceptance.

The first diagnostic's assertion of zero additional discovery immediately after
bootstrap failed because it counted these legitimate unresolved-client settling
attempts. It is retained as a failed assertion, not reclassified as acceptance.
The follow-up distinguishes stable bindings from unresolved settling and shows
the latter stopping at its declared bound. Complete native open/close/switch,
explicit-refresh/recovery and resource gates remain in LP4.

### LP3 consumer source checkpoint

Tmux Plus projects local qualified retained associations independently of remote
C3 expiry. Context/watch loss and native lease expiry revoke them; receipt-only
renewal does not wake the picker or change discovery time. Five focused cases
exercise that behavior, invalid extension rejection without native fallback and
selection payloads containing no retained window/action authority. The complete
frontend source gate passes 292 tests. Its old accepted pin remains unchanged
until the producer's frozen artifact is accepted. A first system-interpreter
gate attempt failed because the required Observer dependency was unavailable;
the accepted gate uses the existing pinned frontend virtual environment.

### LP4 packaging source checkpoint

The candidate version is Observer 0.3.0a1. Descriptor format 3 includes all seven
contract bundles and the pure retained-contract module. Formats 1/2 remain
verifiable for rollback; neither can silently acquire retained payload. Existing
six bundles remain immutable. The source gate passes 352 tests, including new
descriptor coverage/compatibility checks. Frozen/native acceptance remains open.

### LP4 first frozen candidate and resource review

Runtime `b2d908e`, wheel `f542a0247f56dbebc374d18eff3ca2130d7375b470fce89b656a8ff263296f76`,
rebuilds identically and passes eleven installed attachment cases, four simulated
recovery cases and ten actual Snap local binding lifecycle cases. The latter
includes bootstrap, session switch without rediscovery, Kitty close/new client,
explicit terminal refresh, owner/reader replacement, compositor socket
incarnation and passive native generation/hooks. Warm read p95 is 0.952 ms.
Every owned fixture/unit is removed and ordinary sessions remain present.

Its isolated two-session/one-client 120-second profile measures 2.554% combined
CPU (owner 1.023%, fleet 1.531%) with zero periodic desktop jobs or rediscovery.
The prior selected 0.2.0a1 wheel on the same fixture measures 3.025% (owner
1.339%, fleet 1.686%) and 41 periodic desktop jobs. These are sequential working
desktop measurements, not controlled causal attribution; native owner code is
unchanged. The first timing assertion incorrectly included an independent schema
check per query. A separate baseline attempt failed because its diagnostics
assumed the new adapter attribute on the old artifact. Both failed records and
their cleaned follow-ups remain separate.

The ten-minute ordinary two-host profile fails the unchanged five-percent CPU
gate on Snap: 5.679% combined, versus Starship 3.066%. Memory/query/preservation
checks pass. During that profile both endpoints perform zero retained binding
discoveries; remote C3 continues its 197/198 scheduled jobs. This is not accepted
for publication or managed selection.

A passive main-loop diagnostic identifies repeated tree validation and deep
copies as substantial remaining cost. The next source checkpoint removes
duplicate tree checks inside an already checked Fleet envelope, projects only
the local owner for binding inputs, ignores remote renewals when caching local
binding keys, and avoids a second copy of already owned projection branches.
Public validators and outgoing reference/expiry semantics remain intact. Three
new regressions cover mutable branch ownership, independent remote inputs and
local dependency invalidation. The full source gate passes 355 tests. A new
runtime freeze and repeated native/resource acceptance are required.

The `01bad43` follow-up passes the same ten native local cases, simulated
recovery and eleven installed capacity cases (514,617,344-byte sampled peak,
sixteen logical owners/fifteen real SSH links/thirty-two readers). Its ordinary
profile is superseded before completion after a more precise diagnostic finds
the new desktop scheduler projecting all owners on every quiet loop just to
check for remote topology. The partial profile and cleaned interruption are
retained, not called a passing ten-minute gate. The corrected scheduler checks
the immutable host descriptions; a regression exercises one hundred quiet
ticks without projecting any native owner input. The full source gate passes
356 tests before the next freeze. No publication or managed selection occurs.
