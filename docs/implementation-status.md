# Implementation status

Updated: 2026-10-07. Goal: Deliveries A–E, with reviewed commits as work progresses.
The design/backlog baseline is commit `a4fba75`.

| Delivery | State | Evidence |
| --- | --- | --- |
| A: standalone producer | Accepted: T01–T05; G0/G1 passed | Pure API, exact bundles, independent reader, 32 test methods and 12 native/installed cases; [G1 evidence](evidence/2026-10-07-native-collector-g1.json) |
| B: owner service | In progress: T07 state/scheduling foundation | Deterministic receipt/job/hint tests; IPC and native G2 acceptance pending |
| C: fleet service | Planned | None |
| D: Rofi client | Planned; T06 experiment completed, automatic adoption unresolved | [Native experiment](rofi-interaction-probe.md); filter/caret preserved, continuous-input/idle timing not accepted |
| E: managed rollout | Planned | None |

Pure validation and `collect --host-id ID` are implemented and accepted for
the Delivery A scope. Service, GUI migration and deployment are not accepted by this checkpoint. Source, installed/native,
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
