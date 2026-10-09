# Tmux Observer 0.2.0a1 component boundary release

This delivery implements B0–B4 and accepts the frozen native, action, consumer and
resource gates of B5. Native observation remains passive and host-local; it
imports no networking, compositor or write client. Networking consumes Host Mesh
and carries owner-only subscriptions. The Niri adapter matches accepted native
references and optional endpoint-local client associations to current windows.
The separate `tmux_observer_actions.public.ActionClient` performs explicit,
independently guarded operations without requiring an Observer daemon or Rofi.
The prepared public client imports no collector, transport loop or action client.
Tmux Plus now consumes those facades and owns presentation and user intent.

The runtime freeze is `d10ba29e506365a91c90e094deb28c128523edc2`; wheel SHA256
is `aab6540a8de50830c502619f30a564964e3d09a48694dce48132fb194d461345`.
Independent repeated builds match. The 152-member wheel contains 74 Python
modules in three package roots and six executable contract bundles: observation,
service, fleet, local attachments, desktop and action v1. Existing observation,
service and fleet schemas remain unchanged. Local associations are optional,
scope/lease-bearing and never exported in remote owner delivery. Descriptor
format 2 covers all three roots and six bundles; older format 1 remains valid
for the historical two-root artifacts.

The [immutable descriptor](evidence/2026-10-08-boundary-b5-field/observer-candidate.json)
retains `built_unaccepted`; acceptance is external. Review/tag commits may add
documentation after the runtime freeze. The full source gate passes 328 tests;
[runtime CI](https://github.com/byebyebryan/tmux-observer/actions/runs/37879561013)
passes. Frozen matching frontend `c6bece1` passes 287 source tests and thirty
installed CLI cases across both hosts. Its
[release record](https://github.com/byebyebryan/rofi-tmux-plus/blob/main/docs/tmux-plus-0.8.0a1.md)
records 21 native Snap picker cases and inspected screenshots separately.

The exact [native evidence](evidence/2026-10-08-boundary-b5-field/) passes:

- Fourteen collector and eleven association cases on each host, including identity,
  disappearance, generation replacement, PID/UID guards and passive teardown.
- Eight headless action cases per host and four actual SSH actions; native effect,
  viewer outcome and uncertain results remain distinct, with no automatic retry.
- Nine native desktop and seven current window-action cases on Snap. Starship
  receives no foreground input. Owned windows/processes are removed and prior
  focus restored; ordinary tmux references, generations and hooks are preserved.

The [ten-minute ordinary-session profile](evidence/2026-10-08-boundary-b5-field/normal.json)
passes the unchanged five-percent combined CPU ceiling: Snap 4.3229%, Starship
2.6156% of one core, including associated bridges. Fleet/associated-bridge sampled
RSS is 56.25/75.80 MiB against 96 MiB, with owners below 64 MiB. Warm RPC p95 is
2.96/1.71 ms against 50 ms; CLI p95 is 52.95/40.99 ms against 250 ms. Both runtimes
use managed system Python 3.14.7. Immutable validated receipts, tree traversal and
projection reuse remove redundant work while preserving every bound, independent
wire validation, current scope/identity/lease checks and sampling cadence.
Earlier failures remain recorded. Workload/runtime variation prevents attributing
the full historical difference to code, and CPU means are not instantaneous bounds.

The [capacity fixture](evidence/2026-10-08-boundary-b5-field/capacity.json) passes
eleven cases at 497.26 MiB against 768 MiB. Sixteen synthetic logical owners,
fifteen actual SSH links and thirty-two readers run on two physical endpoints;
enabled local association profiles contain no PIDs. This proves the declared
fixture, not sixteen native hosts, capacity CPU or unsampled transient peaks.
Always-on hosts are the accepted scope. Physical suspend and passive native-event
experiments remain optional follow-ups.

Publication, scoped managed selection and verified recovery/paired rollback/
reselection are still independent B5 gates. The installed pair remains Observer
0.1.0a1 / Tmux Plus 0.7.0a2 until their managed record establishes otherwise.
