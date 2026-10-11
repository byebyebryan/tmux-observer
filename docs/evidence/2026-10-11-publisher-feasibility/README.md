# Cached publisher feasibility evidence

2026-10-11. Accepted **research feasibility**, not a production publisher, new
SDK API, release or deployment. The [plan](../../publisher-extraction-plan.md)
and [final review](../../publisher-extraction-review.md) define the decision.

## Accepted result and inputs

[The final report](feasibility.json) records **17 explicit passes**, zero
failures/errors/skips, plus **six independent Tmux profile cases** with their
corpus/input digests. All prototype Python files, the reused native fixture,
released CLI and copied candidate CLI have recorded SHA-256 digests.

| Input | Exact accepted research input |
| --- | --- |
| Python | CPython 3.14.8, isolated private environments, `-I -B` |
| Observer | Released 0.6.0a6 wheel, SHA-256 `232e604ab64c99657852b884720afaefdbcd45be00a56a797793b402e36ff640` |
| Mesh SDK | Released 0.1.0a13 wheel, SHA-256 `62b42bc76e7d79d95d89c41ee6f73c5e0169d24e2f1ac911c151c13f1f2b6f07` |
| Compatibility bridge | Released 0.1.0a10 wheel, SHA-256 `c9fecd77e3ea181d43447784824616232874cfc9ead12a30460d0682bdc3684d` |
| Dependencies | Exact five wheels in [the accepted a13 input record](../2026-10-11-mesh-sdk-adoption/mesh-a13-inputs.json), cp314/x86_64 |
| Candidate | [Study code](../../../studies/publisher/README.md), outside production package discovery |

The runner verifies installed wheel payloads: 84 Observer files, 49 Mesh a13
files and 36 Mesh a10 files. The baseline environment also uses the same checked
Observer a6 payload. Mesh a13 is pinned to source `d9cdac4`; the current Mesh
handoff at `9fbcd3a` leaves `src/mesh_plus`, `pyproject.toml` and `contracts`
unchanged relative to that input. The WSS study is not adopted here.

The copied CLI adds a trusted Python factory mapping. Its distinct digest is
recorded separately from the released CLI. Nothing patches an installed SDK file.
This experiment cannot establish that a13 exports the proposed API: it does not.

## Executed coverage

| Area | Result |
| --- | --- |
| Ownership | Generic publisher executes with native/reference packages fenced out for synthetic Tmux and Agent inputs; this does not certify native Agent integration. |
| Lightweight authority | Real `mesh list --json` executes in a fresh process with native publisher, state SDK and jsonschema imports forbidden and isolated XDG paths. |
| Factory dispatch | Both logical hosts invoke the Observer-owned factory through the copied CLI; default and omitted-domain calls retain the reference implementation. Supplied factory failure/wrong binding rejects without fallback. |
| Fixed SSH path | A private localhost sshd runs the actual `mesh-plus bridge --source tmux_default --stdio` command through its owned executable and source descriptor. |
| Native admission | Host, UID, kernel clock, request, publisher, sequence, revision and emitted-time controls reject. Negative stream fixtures pass pure native validation before exercising stream guards. |
| Proof | Nonce admission precedes a new cached read; original receipt/digest preservation, wrong nonce at the receiver, expired evidence and same-counter lease renewal are checked. |
| State and identity | Exact native reconstruction, complete four-part session identities, warming/historical/empty state, and independent partial-host profile cases pass. |
| Recovery | Owned rename/update, owner outage/restart, new publisher recovery and disconnect revocation pass. |
| Compatibility | The a13 reader with the explicit Observer profile reads both the a10 and a13 factory-free remote reference CLI as well as the candidate publisher. |
| Data ownership | Mutating a retained source frame or barrier cannot alter an already emitted publication. |
| Cancellation | Repeated active-read cancellation, cancellation during connection acquisition and guard-construction failure retire admitted channels; owned watch iterators close. |
| Passivity and cleanup | Owned references/generation components/hooks/global options/attachment counts are preserved before the deliberate empty-server transition; no control client appears. Fixture sockets/root/parent processes retire. |

Native acceptance uses **two disposable default-server namespaces on one physical
host**, two exact a6 owner processes and an actual localhost SSH connection.
Catalog revision and route tokens are synthetic captured inputs. This is not a
Snap/Starship deployment or production Host Mesh routing test. Only owned sessions
are created, renamed or stopped. Read-only ordinary-server reference/hook hashes
match before and after; their values and terminal contents are not published.
Native requests from the candidate are only cached `status` and `watch`; the
existing owners collect on their own schedules.

## Validation and review corrections

The unchanged production source gate, `uv run --extra dev ./scripts/check`,
passes **404 tests**, lint/format and 57 immutable evidence-file checks.
The study is outside that gate and passes its separate runner, Ruff check and
format check. No production source, package metadata, lock, contract, unit or
consumer implementation changes in this pass.

Earlier exploratory runs are not acceptance: two negative fixtures initially
failed native validation too early (lease cap and inconsistent remaining time).
They were corrected to valid native frames that reach the intended guard. A
later CLI check used unsupported `mesh --help`; it was replaced with an actual
isolated catalog read. Review also added explicit frame/barrier ownership and
cleanup checks at the two connection-acquisition failure windows. The report
binds the final corrected code only.

## Limits and later gates

There is no resource soak, installed service recovery, managed cohort change,
graphical check or physical suspend test in this evidence. Study runtime of about
five seconds is test duration, not a latency or CPU acceptance result.

The generic wrapper deep-copies each admitted frame and watch barrier, inspects
the native profile, constructs a digest and validates the resulting envelope.
Watch also inspects the frame to bind its epoch. Native validation and profile
reconstruction add work; several validations were already present in the reference
path. This study measures no comparative CPU/RSS cost. A later exact-package
resource gate must compare normal and declared-capacity operation against the
[accepted a13 budgets](../2026-10-11-mesh-sdk-adoption/README.md#final-frozen-producer-input).

Mesh must first accept a public helper and factory seam. Observer must then
accept its source/factory against that immutable input. A new shared bridge needs
separate selected Agent compatibility, and Plus/managed adoption needs independent
headless/package/resource/recovery/rollback evidence. The current a6/a6/a13/a10
selection remains accepted and unchanged.
