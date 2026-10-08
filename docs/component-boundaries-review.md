# Component boundary review

Date: 2026-10-08. Primary-led source and design review. No delegated review,
new runtime tests or native acceptance are claimed. The output is the
[component boundary design](component-boundaries.md) and its B0–B5 migration gates.

## Scope and disposition

The proposed split is sound with an explicit action client and prepared reader
coordinator. Networking, native observation, desktop association, actions and UI
have different authorities even when shipped together. Separating repository or
process names alone does not establish those boundaries.

Reviewed source baselines: Observer `2d43422` (runtime `d5a2e97`) and Tmux Plus
`36e0148` (runtime `388ee6e`, 0.7.0a2). The first-delivery acceptance and existing
wire contracts remain unchanged. This review recommends further extraction;
it does not reopen the whole accepted always-on delivery or accept its successor.

The Agent Observer reference is its [authority review](https://github.com/byebyebryan/agent-observer/blob/main/docs/codex-daemon-authority-review.md):
provider-native state must retain its source authority, launch/terminal metadata
cannot become current execution identity, common contracts must not inherit
consumer scaffolding, and direct/watch/cached projections must enforce the same
semantics. Tmux already owns its native session/attachment state; desktop matches
and action intent are separate domains. Agent Observer is not an edit target.

## Findings

Severity describes the impact of leaving the boundary unresolved during the next
extraction. Source facts, design risks and reproduced incidents are distinguished;
none of the hypothetical scenarios below is new live-host evidence.

| ID | Severity and evidence | Design resolution / gate |
| --- | --- | --- |
| BR01 | High: the four-way proposal leaves actions without an owner. Tmux Plus still routes and executes lifecycle, launch, focus and close. | Separate UI-neutral write client with native executor and routing/desktop action adapters; B3/B4. |
| BR02 | Medium: `tmux_observer.public` is side-effect-free, but exports Fleet protocol/validators as well as native/owner contracts. Purity does not equal domain separation. | Give native, delivery, prepared and desktop contracts explicit facades over shared low-level framing; B0. Preserve deliberate legacy exports until consumers migrate. |
| BR03 | High: `desktop.LocalClients` imports `Collector` and runs native generation/list-clients reads during matching. Owner and desktop-native facts have no extracted association contract. | Optional native local association profile with coverage, scope and receipt; no scanner-triggered collection; B1/B2. |
| BR04 | Medium: “Niri adapter” understates its inputs. Current matching includes terminal markers, process trees, live SSH/tmux argv and native client joins. Window titles alone are insufficient. | Explicit compositor/terminal/matcher roles; Niri is the first backend, not the domain model; B2. |
| BR05 | High, source-derived risk: the remote marker branch accepts valid launch reference plus live attach argv as confirmed; unlike the local branch it has no current native client-to-session join. A switched client can outlive its initial argv/reference. This was not reproduced remotely in this pass. | C3 distinguishes launch evidence from current association proof; stronger remote confirmation needs native proof, otherwise matching/unknown. Freeze the legacy confidence projection explicitly; B0/B2. |
| BR06 | High, confirmed code behavior: ordinary title-based focus returns the first matching Niri row; it does not check uniqueness. Passive matching is stricter and rejects duplicates. No incorrect live focus was exercised here. | Refined action contract independently revalidates compatible unique candidates. Record duplicate-focus tightening as an intentional legacy behavioral delta, not extraction parity; B3/B4. |
| BR07 | High: passive presence, successful focus, verified viewer handles and safe close are different claims. Close can affect session lifetime; action/transport failure may leave an effect. | Independent action handles/guards, native-effect versus viewer/transport outcomes, no uncertain redispatch, owned cleanup and close-versus-kill proof; B3. |
| BR08 | Medium: mandatory native `Session.pending` is interpreted from the Plus-specific `@rofi_tmux_plus_pending` annotation. It is passive, but not a generic tmux phase. | Explicit bounded annotation/profile ownership and legacy projection. No provider phase or registration repair in the core; B0/B1. |
| BR09 | High: moving native client PIDs into a public feed could turn local/reusable identifiers into cross-host or durable identity. Compositor IDs have the same problem. | Full session references, source/boot/PID scope, process incarnation checks, desktop epochs and local-only detailed association profile; B1/B2. |
| BR10 | High: new association facts add another freshness dependency. Quiet delivery, UI cycling, route health or desktop scanning cannot renew it. | Independent receipts and input signatures including association changes; invalidate positives on expiry/failure/context change; B1/B2/B4. Preserve the 0.7.0a2 browse renewal repair. |
| BR11 | Medium: Fleet code imports the desktop implementation and its public context is desktop-shaped. Current unsupported desktop state already preserves owner rows; headless inventory is not shown broken. | Separate coordinator from transport and inject optional desktop observation. Prove import/install and owner behavior without Niri; do not add another daemon merely to rename the boundary; B0/B2. |
| BR12 | Medium: migrated prepared reads coexist with old frontend collectors, caches and mixed observation/action modules. Some are compatibility/test seams; their presence is not proof that browse invokes them. | Trace active entry points, move consumer-facing clients to narrow facades, remove duplicate active paths only after parity, and keep the old executable as a compatibility client; B4. |
| BR13 | Medium: native association sampling and finer contracts may add collection or projection cost. Prior Snap normal CPU was near the accepted ceiling. | Coalesce source work, preserve bounds and separately remeasure idle CPU/RSS/source lag/query latency; B1/B5. No cadence changes in this design. |
| BR14 | Low: several original design headers say no implementation exists; the current status summary records the original a1 frontend while specialized operations records identify a2. | Clearly label first-delivery baselines, link the current operations record and identify this refinement as design-only. Do not edit historical evidence or immutable descriptors. |

## Checked source and contract evidence

- [Pure public facade](../src/tmux_observer/public.py) and
  [shared validators](../src/tmux_observer/_validation.py): native, Service and
  Fleet validators share one pure namespace; passive viewers reject action handles.
- [Native collector](../src/tmux_observer/collector.py) and
  [models](../src/tmux_observer/_models.py): generation/reference brackets,
  bounded metadata and the launch-client pending marker.
- [Desktop native join](../src/tmux_observer_client/desktop.py): local
  generation/list-clients/generation reads, 512-client cap and full reference checks.
- [Desktop scan](../src/tmux_observer_client/_desktop_scan.py): unique qualified
  matches, current local PID join, remote launch-reference branch, bounded process
  evidence and explicit unknown reasons.
- [Desktop input signature](../src/tmux_observer_client/_desktop_input.py),
  [fleet coordinator](../src/tmux_observer_client/fleet.py) and
  [prepared facade](../src/tmux_observer_client/public.py): context/epoch receipts,
  shared scans, per-context IPC and no reader-triggered collection.
- [Tmux Plus action router](https://github.com/byebyebryan/rofi-tmux-plus/blob/36e014851c84f5b72d6b454a3e994828e492eea0/rofi_tmux_plus/lifecycle_service.py),
  [local lifecycle/focus](https://github.com/byebyebryan/rofi-tmux-plus/blob/36e014851c84f5b72d6b454a3e994828e492eea0/rofi_tmux_plus/lifecycle.py),
  [remote lifecycle](https://github.com/byebyebryan/rofi-tmux-plus/blob/36e014851c84f5b72d6b454a3e994828e492eea0/rofi_tmux_plus/remote_lifecycle.py)
  and [viewer inspection/close](https://github.com/byebyebryan/rofi-tmux-plus/blob/36e014851c84f5b72d6b454a3e994828e492eea0/rofi_tmux_plus/viewer_service.py):
  actions retain their own Mesh/native validation; ordinary focus has a first-title
  fallback; strict viewer operations use stronger guards.
- [Released Tmux Session v1](https://github.com/byebyebryan/rofi-tmux-plus/blob/36e014851c84f5b72d6b454a3e994828e492eea0/docs/TMUX_SESSION_V1.md):
  inventory is fresh, ordinary and verified Open are distinct, terminal launch is
  local spawn, and close has separate survival/handle checks.
- [Native tmux switch-client implementation](https://github.com/tmux/tmux/blob/3.7c/cmd-switch-client.c):
  the existing client can be assigned a different session. This supports BR05's
  possibility; it does not demonstrate a wrong remote match on Snap or Starship.

The installed acceptance already proves useful prepared observations and native
passivity within its recorded scope. It does not prove the proposed association
profile, stronger remote binding, extracted action client or duplicate-focus policy.

## Adversarial review

| Scenario | Required result and owning boundary |
| --- | --- |
| Session renamed while its terminal title lags | Native identity survives; desktop association may become unknown until reconciled. No name-based retarget; C1/C3. |
| Server replaced and session ID/name reused | Old reference and dependent viewer matches invalidated; actions reject the old target; C1/C3/C5. |
| Local client switches sessions but launch marker stays unchanged | Current native join wins over launch intent; input changes revoke old association; C1/C3. |
| Remote client switches sessions while its initial SSH/tmux argv persists | Launch evidence cannot assert a current end-to-end binding; retain only justified qualified presence; C3. |
| Two terminals have the same session/host title | Observation reports ambiguity; new action policy does not focus the first match or silently create another viewer; C3/C5. |
| PID/window ID reused or Niri socket replaced | Validate process/compositor incarnation; revoke old context; no durable numeric identity; C3/C5. |
| Native association read fails while session roster is healthy | Owner metadata remains useful; native join becomes unknown; no fabricated detached count; C1/C3. |
| Niri absent, unsupported or scanner fails | Native owner facts and native-only actions remain usable; Open membership is unknown; C1/C3/C5. |
| SSH streams cached frames or heartbeats after the source lease expires | Historical metadata only; networking cannot renew native or desktop facts; C2/C4. |
| Mesh revision/route changes during a scan or action | Reject obsolete join/result or action target; do not redispatch to a new host; C3/C4/C5. |
| Picker cycles after quiet owner renewal and old presentation expiry | Read current prepared facts, preserve filter/action/reference and persist renewed frame; no collection; C4/UI. |
| Pending confirmation receives a reordered/new view | Target stays frozen; execution revalidates it rather than using the new selected row; UI/C5. |
| Native action succeeds but response or terminal attachment fails | Retain confirmed/uncertain effect independently of viewer outcome; no automatic retry; C5. |
| No rows exist and user requests Create | Explicit host/config and action inputs suffice; no fake reference or service autostart; C5. |
| Another source fails or the displayed roster is capped | An independently healthy exact action target is validated directly; aggregate failure does not authorize or blanket-reject it; C5. |
| A read-only consumer imports contracts with adapters unavailable | Pure validation and cached read path work without native, desktop, transport-loop or write implementations; B0/B4. |
| Multiple pickers/readers request refresh | Shared source scheduling and coalesced bounded tickets; UI count does not multiply collection or SSH; C2/C4. |

These are future acceptance cases, not tests added or run in this pass. Native
association and action proof uses disposable sessions/windows and independent
native reads. Graphical acceptance is Starship-only; physical suspend is optional.

## Decisions and implementation gates

Resolved in design: action ownership, native-versus-desktop evidence ownership,
optional local client associations, distinct contract domains, independent leases,
qualified matching, current-binding requirements, ambiguity rejection in the new
action policy, explicit compatibility projection, and staged extraction without
extra daemons or a generic adapter framework.

B0 still must freeze executable schemas, local-only transport/profile selection,
process-race guards, concrete write request/result encoding, errors and the legacy
mapping of behavioral tightening. These are bounded implementation decisions;
the design does not pretend those APIs already exist. B1–B5 must supply their
own source/native/installed/GUI/resource evidence before managed selection.

No terminal registration protocol, remote client binding scheme, native event
adapter, alternate tmux socket, general compositor framework or physical-host
capacity expansion is included. A future remote binding mechanism must preserve
passivity; naming it is not a substitute for proving it.

## Documentation validation

Check local links, unique heading anchors, fenced examples, source attribution,
unchanged canonical contract digests, intended-path diffs and whitespace. This
pass introduces no new executable examples or machine schema. Runtime tests are
not rerun to imply acceptance of a documentation-only design.

The documentation gate passed over ten Observer and three Tmux Plus documents:
local links/heading anchors and locally mapped cross-repository source links,
balanced fences, whitespace and three shell examples parsed without execution.
All 26 Observer and 102 Tmux Plus canonical contract files are byte-identical to
their pre-review HEADs. Only README/design documentation is changed; no source,
service, package descriptor or installed artifact is modified. External HTTP
availability and graphical/native behavior are not established by that gate.
