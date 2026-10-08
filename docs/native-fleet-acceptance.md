# Isolated two-host fleet acceptance

Run from Snap after the source gate:

```sh
uv run --extra dev scripts/accept-native-fleet --output /tmp/tmux-fleet-functional.json
uv run --extra dev scripts/accept-native-fleet --with-profile --output /tmp/tmux-fleet-profile.json
```

This tool installs one wheel on Snap and Starship and verifies equal wheel and
unit-template digests. It consumes each endpoint's public Host Mesh catalog,
then copies that catalog into private provider preferences and route history.
Actual strict, non-PTY SSH routes carry the installed owner-only stdio bridge.
No host-key bypass, shared SSH master, ordinary native server or provider history
is addressed. Task-created UUID directories, default tmux servers, user units and
bridge processes are verified stopped before their backing paths are removed.

The harness uses private owner/fleet sockets and an internal remote executable
injection to reach those isolated installed services. This is candidate acceptance,
not the production endpoint layout or managed artifact selection. The native
context/template handoff has separate evidence. Both fleet contexts here are
explicitly headless; they cannot establish Open here or native GUI behavior.

Independent native reads supply full references, attachment/window counts,
server generations, UID, native hostname and clock-domain identities. Returned
fleet frames pass the separately implemented contract reader. The conservative
remote expiry is independently recalculated from matching probe evidence.
Refresh, native failure on live SSH, owner stop/replacement, delayed/trickled
bytes, wrong nonces and present/broken Mesh recovery exercise actual two-host
transport. Fault relays change transport bytes/delivery only; they manufacture no
accepted owner sample. Roster, attachment counts, windows and hooks remain unchanged.

Each endpoint reports 100 warm cached RPC durations including validation and
100 installed cached CLI durations including process startup. These are not
Rofi-frame or graphical-open measurements. The optional profile collects at least
ten minutes of owner/fleet cgroup CPU, sampled process RSS, inbound owned bridge
CPU/RSS, native commands, Mesh calls, owner protocol payload/control bytes,
connection starts and queue counters. Profiler/control processes remain outside
the service cgroups. RSS is sampled once per second and can miss transient peaks;
SSH counters exclude encrypted wire overhead. These limits remain explicit.

The output says `G3-partial`/`passed_partial` even when every included case passes.
Physical sleep/wake, native desktop truth/replacement, declared capacity, transient
memory peaks, encrypted byte overhead, direct-facade compatibility, Rofi and
managed deployment still need their own evidence. A clean-source result is required
before checking an acceptance record into the repository; a dirty-source run is
an investigation result only.
