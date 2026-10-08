# Installed fresh direct acceptance

Run from Snap after the source gate:

```sh
uv run --extra dev python scripts/accept-native-direct --output /tmp/native-direct.json
```

The tool installs one wheel on Snap and Starship, using the existing private
default-server/unit fixture. It stops both owned observer services before the
direct checks. Actual installed `tmux-observer-client snapshot --access direct`
invocations must collect independently, without activating a service.

The public Host Mesh catalogs are copied to private preferences. The configured
SSH executable adds only an isolated remote HOME, TMUX_TMPDIR and PATH before
executing actual strict, non-PTY SSH. The installed collector is exposed under
its default `$HOME/.local/share/tmux-observer/bin/tmux-observer` path in that
private HOME. The client uses its production command renderer and public CLI;
there is no remote-executable injection into DirectInventory. Ordinary provider
preferences, route history, home directories and native servers remain untouched.

The independent acceptance reader checks actual output bytes. Legacy success
and failure shapes are validated against the unchanged canonical Tmux Session
v1 schemas, after verifying the whole bundle against the extraction baseline.
Separate native queries establish full references, names, attachment/window
counts, geometry, hooks and explicitly set options. Rename is a fixture operator
action and must preserve the full reference while fresh reads expose the new name.

Checks include both directions, selected local/remote hosts, casefold resolution,
explicit panes/options, stale revision and unknown-host refusal, present/broken
versus absent Mesh, reached-host executable absence, no service activation and
native passivity. The direct 128-host bound remains source-tested; this native
fixture has two hosts. This gate does not establish cached-service freshness,
physical sleep, Rofi rendering or managed endpoint selection.

## Review findings

The initial native check found a real producer compatibility defect: local host
rows omitted the required legacy `route` field. Complete and failed rows now
include `route: null` for local or unknown routes. The source regression uses
unchanged pinned schema bytes and their original bundle manifest.

Expanded native checks also exposed the frozen legacy text restriction: its
option values cannot be empty strings. The released Tmux Plus public validator
rejects the same native empty-option response. The fresh legacy facade now emits
a typed `operation_failed` envelope for this unrepresentable profile; it neither
publishes malformed success JSON nor converts empty strings to absence. Installed
core `collect` is checked separately and preserves `""` versus `null`, as required
by Observation v1. No legacy contract/schema bytes or frontend behavior were
changed. Any future widening of that legacy contract is a separate compatibility
decision with its own bundle/pin review.

The tool retains failed investigation outcomes outside the committed acceptance
records. Only a clean committed source result can establish this native checkpoint.

Clean source `6bb0594` passed all 24 installed/native cases with one wheel on both
endpoints; see [native direct evidence](evidence/2026-10-07-native-direct-t10.json).
The default full-fleet CLI used one fresh SSH connection per invocation; selected
local and invalid selection/revision cases used none. Both owned observer services
stayed inactive. Native roster, attachment/window counts, geometry, hooks and
option snapshots matched before/after the operator rename cases. Both fixtures'
units, owned children, sockets and backing directories were removed. This closes
the independent T10 native direct checkpoint. Revised G3 follows the
[always-on scope](always-on-acceptance.md); physical sleep/wake is optional and
consumer/managed gates retain their independent requirements.

## Migration review: local-only aliases

The T13 frontend review reproduced a missing-producer case in which a valid
casefold FQDN was rejected as `unknown_host`, although the released Tmux Plus
local identity accepts it. The direct client now preserves that alias selection.
Short-host and all-host requests perform no DNS lookup. A non-short local
selection resolves its optional FQDN in an owned, bounded child; failure,
overflow or its two-second/whole-operation deadline refuses collection rather
than guessing a host. Cached reads and owner/fleet service paths do not call it.

Source checks pass 188 tests. The installed direct harness now also selects the
actual local FQDN on each endpoint with Mesh absent and checks deduplication,
full native generation/session/creation identity and no SSH. These two new cases
and the existing 24 cases must pass on the revised frozen artifact before its
direct-client checkpoint is accepted. The earlier native result remains evidence
for its original artifact; it is not silently relabelled as a new-wheel run.
