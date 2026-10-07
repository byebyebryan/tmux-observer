# Implementation status

Updated: 2026-10-07. Goal: Deliveries A–E, with reviewed commits as work progresses.
The design/backlog baseline is commit `a4fba75`.

| Delivery | State | Evidence |
| --- | --- | --- |
| A: standalone producer | In progress: T01 foundation established | Extraction manifest, source checks and isolated wheel/console import; contracts/native acceptance pending |
| B: owner service | Planned | None |
| C: fleet service | Planned | None |
| D: Rofi client | Planned; early T06 probe to follow contract fixtures | None |
| E: managed rollout | Planned | None |

No implemented observation API, native acceptance, service, GUI migration or
deployment is accepted by this foundation checkpoint. Source, installed/native,
graphical and managed evidence remain separate gates.

Current source audit: inherited generic “error connecting” classification must
not establish native absence. Fast/legacy collection must add final generation
and full-reference checks within one bounded BOOTTIME read budget.
