# Design review

Date: 2026-10-07. Primary-led review of the documents and inspected extraction
baseline. This is not an independent agent review or runtime acceptance report.

## Disposition

Proceed to G0 contract/fixture work. The reviewed architecture has no remaining
unresolved ownership blocker: passive core, local publisher, fleet/desktop reader,
write client and UI have explicit responsibilities. Exact wire schema and native
proof deliberately remain implementation gates. Do not skip from this design to
frontend migration or managed promotion.

The two largest corrections are conservative remote freshness proof and a
separate native Rofi adoption gate. Persistent streams improve transport reuse;
they do not make buffered metadata current or make an inactivity-driven UI live.
Initial native collection remains polling, with push delivery to shared readers.

## Findings and resolutions

Severity here denotes the consequence of implementing the tempting shortcut.
“Resolved in design” means the specification addresses it, not that code exists.

| ID | Severity / finding | Resolution in this design | Required proof |
| --- | --- | --- | --- |
| R01 | High: whole-module extraction imports mutation, terminal or close behavior into the core | Narrow read interfaces and pure public facade; writable modules remain separate | G0 import audit; G1 command allowlist; G5 independent writes |
| R02 | High: exporting fleet inventory as an owner source causes recursive joins and wrong provenance | Only fixed owning-host publishers are SSH exports; aggregation is desktop-local | G3 scope/provenance and two-host topology |
| R03 | High: server replacement between separate native reads can mislabel rows | Bracket generation and per-session identity; ambiguous batches fail/retry within budget | G1 fast/legacy race exercises |
| R04 | High: frame arrival/heartbeat extends old remote facts | Matching bounded nonce response; remaining lease minus full RTT and margin; failed evidence stays failed | G0 independent clock fixtures; G3 delayed/buffered native SSH |
| R05 | High: shared owner attachments are presented as local Open or close authority | Independent desktop receipt/context and qualified join; no action handles | G3 native endpoint joins; G5 write revalidation |
| R06 | High: control-mode observer changes attachment or keeps sessions alive | Poll native reads initially; native event adapter excluded until a separate passivity gate | G1/G2 lifetime; optional G7 |
| R07 | High: service absence/warming is silently mapped to fresh direct collection or empty roster | Explicit access mode; null warming/typed error; no autostart/fallback | G2 read-client behavior; G4 foreground absence |
| R08 | High: “read migration” silently changes the released inventory/lifecycle contract | Old canonical facade remains; old inventory is explicitly fresh/direct; new wire versions are distinct | G4 independent legacy consumer; G5 action parity |
| R09 | High: native process cleanup kills ordinary tmux/SSH or another service | Only owned observation/bridge children, private masters and incarnation-owned endpoints | G2/G3 stop and rollback |
| R10 | High: dropped/late frames, route changes or persisted cache resurrect positive facts | Incarnation/sequence/scope guards, immediate uncertainty, full resync and fresh proof | G2 restart; G3 route, suspend and replay |
| R11 | Medium: daemon is presented as a complete fix for lingering Refreshing | Separate ticket outcome and callback adoption; continuous typing requires native UI proof | G4 actual interaction and visible notice timing |
| R12 | Medium: unbounded viewers/subscribers/hosts amplify polling and buffers | Source-owned cadence; admission, frame/control/storage caps; explicit prepared-service capacity | G2/G3 capacity with owned-child counters |
| R13 | Medium: refresh completes on an old job, obsolete desktop scan or partial success | Post-acceptance sample requirement; scoped child tickets and proof; failed result preserves per-source successes | G2/G3 refresh epoch/deadline tests |
| R14 | Medium: leases renewed by desktop scans, route reports or collection finish | Sample-start lease and independent owner/desktop/transport clocks; failure invalidates current claims | G0/G2 receipt transitions; G3 joins |
| R15 | Medium: read tests are treated as graphical/deployment acceptance | Separate direct/service/network/GUI/managed gates and exact artifact evidence | G1–G6 evidence ledger |
| R16 | Medium: frame timeout is shorter than heartbeat cadence | Two-second started-record/probe deadlines; ten-second transport-silence bound | G2/G3 idle watch and trickled-frame tests |
| R17 | Medium: remote publisher dies after logout or desktop context is inherited incorrectly | Explicit user-manager lifetime; private captured desktop instances; no implicit lingering/global display import | G2/G3 boot/logout/context acceptance |
| R18 | High: healthy SSH conceals a failed Mesh recheck and perpetuates obsolete route authority | Explicit catalog health; retained catalog historical; no new attempts/current fleet positives until revalidation | G3 invalid-provider transition and recovery |
| R19 | Medium: inherited monotonic timeouts omit elapsed gaps despite BOOTTIME leases | BOOTTIME operation budgets; late work rejected and epochs advanced after resume | G1–G3 simulated clock/pause recovery and runner audit; optional physical sleep |

R03 comes from source inspection: the baseline fast inventory probes generation
before list/options/panes and does not end with a generation bracket. This is an
extraction hardening requirement, not a reproduced incident or a fix made to
released Tmux Plus. G1 must audit equivalent legacy-path behavior too.

## Adversarial walkthrough

| Scenario reviewed | Expected transition and why |
| --- | --- |
| Remote frame waits longer than its lease before arrival | Candidate/historical only. No matching fresh proof means no positive extension. |
| Probe response takes 1.8 seconds and advertises 1 second remaining | Translate remaining to zero; useful names do not make attachments current. |
| A frame trickles bytes forever | Two-second absolute started-frame deadline disconnects it; each byte cannot reset the budget. |
| No frames are sent for a healthy idle period | Three-second heartbeats fit inside the separate ten-second silence bound. |
| Same snapshot repeatedly served after native failure | Current health remains failed; requests and heartbeats cannot renew the sample. |
| Refresh arrives while an older job runs | Wait for one eligible successor; do not complete the request from pre-request work. |
| Remote refresh returns with a successful child result but no verified view | Ticket awaits matching proof or ends failed/deadline; displayed fleet facts remain uncertain. |
| Desktop scan finishes after owner name/count/route changes | Reject obsolete input signature; coalesce a new scan within ticket deadline. |
| Reader buffers old publisher data across a restart | New incarnation guard drops it; persisted descriptors begin stale. |
| Selected Mesh route/host disappears during SSH setup | Epoch mismatch cancels the late publication; removed hosts are not targets. |
| 33rd subscriber or 17-owner prepared catalog | Typed admission/capacity state; no silent subset or extra collection. |
| Service is killed while native tmux has `destroy-unattached` enabled | Observer has no attached client and no tmux ownership; ordinary lifetime remains native. |
| User types continuously while refresh finishes | No live-update claim until native input-change delivery passes; prepared startup can pass separately. |
| A destructive confirmation is open when selection/roster changes | Confirmation retains its exact target and action code revalidates it. |
| Window title resembles a remote session but evidence conflicts | Unknown viewer; no focus/close authority from title or attached count. |

## Review-driven refinements

The first drafting pass was tightened in the following places:

1. Defined outgoing queued versus already-started records and control priority;
   32 subscribers with maximum-sized frames must still fit a declared total cap.
   Bounded incoming documents and owned SSH children are measured separately.
2. Added a first prepared-service capacity of 16 owners, retaining the existing
   direct CLI/Mesh limits. This is explicit admission behavior, not a hidden
   truncated roster; larger capacity needs its own resource acceptance.
3. Made refresh results truthful for mixed success and required post-request work.
   Remote child acceptance is causal; no cross-host timestamp comparison is used.
4. Allowed valid negative/failure evidence to invalidate a positive immediately
   without pretending it can renew positive evidence. Bounded advertised leases
   and nonregressing counters are part of independent validation.
5. Separated started-frame deadlines from transport silence so the proposed
   two-second record budget does not break a three-second heartbeat cadence.
6. Extended the native consistency audit beyond server generation to full session
   identity, and kept source hardening in the producer gate.
7. Kept write extraction out of the critical path for prepared reads. G6 can
   select accepted G3/G4 while the existing lifecycle implementation remains.
8. Required explicit publisher availability across login/logout and separate
   desktop environment handoff. A successful SSH query does not establish
   persistent background-service availability.
9. Defined catalog health across periodic Mesh failures. Healthy transport does
   not keep an invalid authority current; local owner diagnosis stays independent.

## Remaining implementation decisions

G0 must freeze exact wire fields/codes, declared extension policy, clock/namespace
representation, refresh-scope syntax, message priority/admission and package
layout. The semantic choices above are settled; these details require executable
schemas and independent fixtures, not another speculative framework.

G1–G3 must establish actual native passivity, supported tmux/tool versions,
lease/remote-proof correctness, tuning/resource viability, desktop contexts and
installed recovery. G4 must establish actual Rofi input behavior and visible
latency. Native events and process co-location remain optional measured changes.
No claim that Agent Observer/Plus is already migrated or that Observer is live
on Snap/Starship follows from this design.

## Documentation checkpoint verification

Check all internal document links/anchors, JSON syntax and recorded measurement
summaries, whitespace/fences and consistency of gate/decision IDs. Review package
boundaries against current source and canonical contracts. Confirm this task
changes only the new repository and preserves the Tmux Plus released checkout.
Runtime tests, commits, publishing and chezmoi application are outside this
checkpoint. The final task report records the actual checks completed.
