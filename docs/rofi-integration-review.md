# Rofi prepared-client integration review

Date: 2026-10-08. This is a production-boundary review of the accepted T06
prototype, before T13/T14 implementation. It changes no frontend, launcher,
service, managed artifact or acceptance dependency. Physical G3 sleep/wake remains
deferred on both hosts.

## Decision and evidence

Use a first-party, explicitly version-pinned native mode as the proposed T14
notification boundary. Keep it in Tmux Plus; Observer remains independent of
Rofi. Preserve the script-mode renderer and existing navigation/action policy
behind that boundary, with a prepared IPC model replacing observation jobs only
after G3 is accepted. Do not ship the experimental preload or rely on inactivity
events to establish updates during continuous typing.

This is an implementation direction, not acceptance of a production integration.
The [T06 native experiment](rofi-interaction-probe.md#native-mode-prototype)
already establishes fixture adoption during idle and active input on Snap, with
filter/caret/full-reference retention and view-arrow callbacks. It does not prove
service-ticket handling, pending-action safety, mode destruction/re-entry or
artifact compatibility on another Rofi build.

The [current inspection](evidence/2026-10-08-rofi-integration-review.json) finds
identical x86_64 Rofi `2.0.0-dirty` binaries and Mode headers on Snap and Starship:
package `rofi 2.0.0-1`, executable SHA256
`4f8dcd3a87d4c41af3e7c5f3ab4891a0926f21ab659072e5471e7332cf30a1ca`.
All seven private symbols actually requested by the prototype are exported on
both hosts. An isolated local compile with `-Wall -Wextra -Werror` produces the
same library bytes as the prior T06 artifact. No mode was loaded and no new
graphical test ran; these facts do not establish Starship GUI acceptance or
production runtime safety.

## Findings that implementation must close

| Finding | Required production behavior |
| --- | --- |
| Mode ABI 7 and a version string do not pin private factory/view behavior. The prototype's version check is in its harness. | A launcher verifies the selected Rofi binary against the accepted integration descriptor before loading the mode. The descriptor records architecture, binary/header/source/library digests and build dependencies. Missing symbols or an unsupported binary produce a bounded visible startup failure. |
| The prototype notices inode/mtime changes using `stat`; it accepts an environment-supplied feed path and silently ignores a missing file. | Use an owned per-picker runtime directory, bounded regular files, checked ownership/mode and no symlink following. Notification data can request a read-only redraw; it cannot supply a command, session action or authoritative observation. Malformed, missing or replaced notification state has an explicit bounded outcome. |
| File changes alone cannot detect a dead/stalled watcher or an expired owner/desktop lease after the last update. | Couple notification delivery to owned watcher lifetime and schedule relevant expiry with local BOOTTIME. Re-read and validate prepared state on expiration or watcher loss. Cached delivery and watcher activity renew no owner/viewer facts. |
| The current picker callback 28 is a timeout path using the old model and wall-clock presentation state. | Give callback 28 an explicit read-only prepared-state adoption path. Background adoption must not invoke direct collection, request refresh, confirm an action or start services. Compare Observer leases with its local clock; preserve wall-clock activity labels separately. |
| The prototype delegates synchronous script callbacks and borrows script display state while a GLib timer is active. | Bound/coalesce pending notification work, reacquire view/state after callbacks, remove the timer and owned watcher on destruction, and test cancellation, re-entry and mode switching. Preserve the delegate's allocation ownership. |
| A new row model can retarget confirmation or lose selection even when the service correctly publishes it. | Preserve complete references, the selected view, filter/caret, and immutable pending action intent. Resolve highlighted identity against the new model; native write revalidation remains independent. |

The seven private dependencies are `script_mode_parse_setup`,
`rofi_view_get_active`, `rofi_view_get_mode`, `rofi_view_get_completed`,
`rofi_view_maybe_update`, `rofi_view_trigger_action`, and
`key_binding_get_action_from_name`. The prototype also compiles against the
installed Mode layout in `mode-private.h`. Treat these as accepted-build
dependencies, not a portable public notification API. A package update requires
a rebuilt artifact and renewed native interaction acceptance before selecting a
new integration tuple.

## Ownership and data flow

Observer owns source facts, clock domains, health, remote proof, viewer receipts,
bounded refresh tickets and their terminal lookup. Its accepted public client
facade supplies cached reads; the CLI remains a separate diagnosis client.

Tmux Plus owns the picker model, presentation snapshots, saved context, ordering,
navigation and pending actions. A per-picker client watch can notify that model;
it subscribes to the existing shared fleet and creates no collectors or remote
connections. Keep one latest notification rather than an unbounded event queue.
Scope the watch to its captured desktop context and reader incarnation. Restart,
gap and unavailable outcomes cause fresh scoped validation and honest UI state.
Use the public `tmux-observer-client watch` CLI once per picker for that watch;
ordinary redraws use the supported in-process cached facade. The launcher owns
the stream/child lifetime. Do not import the private `_watch` implementation or
launch a new CLI for every redraw.

Do not copy the experimental callback command from an arbitrary environment into
a production mode. The launcher constructs fixed argv for its selected, verified
artifact and owns the helper lifetime. The native mode only wakes the established
read-only callback; metadata cannot choose another callback or execute an action.
Keep the existing prepared initial frame and native `-selected-row` launch path.

Background renewal remains quiet. Alt+R alone admits an explicit bounded refresh
ticket and retains its publisher/ticket identity. Adoption checks that ticket's
terminal result even when no row material changed or a notification was missed.
Completion, failure, deadline and stale scope clear the matching notice; an
unrelated renewal or another request cannot clear it. Service absence/warming is
visible and never silently falls back to a fresh native/SSH read.

The wakeup mechanism must cover both material changes and time-driven invalidation.
Its signal is not authority: each callback still consumes and validates a current
prepared view and applies owner/viewer expiry at read time. A terminal refresh
result and a replaced reader require notification even when session rows compare
equal. A stalled watch must not leave Open/Attached positives current indefinitely.

## Implementation order after producer acceptance

1. **T13 fresh CLI compatibility.** Pin the accepted Observer artifact and adapt
   `InventoryService` to the explicit fresh/direct facade. Preserve the canonical
   v1 schemas, argv, host selection, options/panes, exit/error behavior and
   `--with-viewers`. Non-OK host rows contain no sessions. Existing lifecycle
   implementation and native target validation remain independent.
2. **T14 prepared model and startup.** Introduce the cached facade through public
   imports, map health/expiry explicitly, and retain existing presentation/saved
   state. Startup prepares a useful frame without native/SSH collection or an
   implicit refresh/service start. Prove bounded absent/warming/error outcomes.
3. **T14 notification lifetime.** Add the owned watch, one-latest notification,
   reader/context fencing and BOOTTIME expiry handling. Consume refresh tickets
   independently of material row revisions. Make callback 28 read-only before
   attaching automatic delivery to it.
4. **T14 native integration artifact.** Replace fixture environment inputs with
   the fixed launcher contract, harden feed/lifetime checks, package the native
   mode separately from Observer, and validate the selected Rofi/artifact tuple.
   Rebuild and reaccept on relevant Rofi changes; no live compilation at launch.
5. **G4 native acceptance.** Exercise actual service-driven idle/typing updates,
   refresh terminal notices, exact selection/view/filter/caret, pending intents,
   watcher/service/context failure and mode lifetime. Record callback adoption
   and visible rendering separately. Snap GUI proof and Starship GUI status stay
   separate; current binary equality is not graphical acceptance.
6. **T15 selection and rollback.** Publish accepted artifacts, pin producer and
   frontend/native-mode digests together, then perform scoped chezmoi rollout and
   exact installed/runtime/recovery/rollback checks. Unsupported Rofi must fail
   visibly before selecting an unsafe mode; restore the prior accepted artifact
   through the reviewed rollback path.

Do not implement steps 1–6 around the deferred producer gate. This review finishes
an independent preparation task and preserves the delivery dependencies in the
[implementation backlog](implementation-backlog.md).

## Acceptance additions for G4

| Trigger | Evidence required |
| --- | --- |
| Binary/version/ABI/header tuple differs; a private symbol is absent | Bounded visible failure before mode use; no direct collector, refresh, action or service start |
| Watcher exits, stalls, loses its reader, or feed state disappears/is malformed | Timely unavailable/expired view and revoked viewer positives; owned helper cleanup |
| Owner/desktop validity expires with no later material update; clock advances across sleep | BOOTTIME-driven invalidation; no liveness-based renewal or stale Open/Attached membership |
| Refresh becomes terminal while session rows remain equal, or a notification is skipped | Matching ticket lookup clears its notice with the recorded terminal outcome |
| Automatic update while filtering, changing views, or confirming an action | Full-reference/intent retention, caret/filter preservation and independent action revalidation |
| Escape, mode switch, destruction or re-entry while callback/feed work is pending | No use of released state, duplicate timer/watch, leaked child or replacement of ordinary sessions |

Use the existing G4 timing targets: 100 warm samples for a reported p95, frame
creation separate from native useful-view appearance, and terminal ticket result
separate from visible notice removal. The prototype's individual callback times
are not a production redraw-latency distribution.
