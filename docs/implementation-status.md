# Implementation status

Updated: 2026-10-07. Goal: Deliveries A–E, with reviewed commits as work progresses.
The design/backlog baseline is commit `a4fba75`.

| Delivery | State | Evidence |
| --- | --- | --- |
| A: standalone producer | In progress: T01–T04 established; G0 passed, G1 pending | Pure API, exact bundles, independent reader, 32 test methods; narrow direct collector and owned native smoke |
| B: owner service | Planned | None |
| C: fleet service | Planned | None |
| D: Rofi client | Planned; early T06 probe to follow contract fixtures | None |
| E: managed rollout | Planned | None |

Pure validation and `collect --host-id ID` are implemented. Native producer
acceptance, service, GUI migration and deployment are not accepted by this checkpoint. Source, installed/native,
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
passivity/race cases and the installed direct CLI still need T05 acceptance.
