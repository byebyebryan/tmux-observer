# Implementation status

Updated: 2026-10-07. Goal: Deliveries A–E, with reviewed commits as work progresses.
The design/backlog baseline is commit `a4fba75`.

| Delivery | State | Evidence |
| --- | --- | --- |
| A: standalone producer | In progress: T01–T03 established; G0 source contract gate passed | Pure API, three exact bundles, independent schema/semantic reader, 17 test methods with adversarial subcases; native collection pending |
| B: owner service | Planned | None |
| C: fleet service | Planned | None |
| D: Rofi client | Planned; early T06 probe to follow contract fixtures | None |
| E: managed rollout | Planned | None |

Pure observation/service/fleet validation is implemented. Native collection,
service, GUI migration and deployment are not accepted by this checkpoint. Source, installed/native,
graphical and managed evidence remain separate gates.

Current source audit: inherited generic “error connecting” classification must
not establish native absence. Fast/legacy collection must add final generation
and full-reference checks within one bounded BOOTTIME read budget.

G0 evidence: `uv run --extra dev ./scripts/check` passed on CPython 3.13.7,
including 8 hand-assembled fixtures read without importing producer validation.
The wheel installed and imported in an isolated environment; all packaged
contract bytes matched the source bundles. Validation covers identity, partial
coverage, unaccepted/warming receipts, sample-start leases, mismatched clocks,
future/delayed remote proof, independent desktop evidence and refresh outcomes.
This evidence establishes the wire boundary, not native passivity or service
behavior. The separate fleet stream envelope makes sequence/gap/resync explicit.
