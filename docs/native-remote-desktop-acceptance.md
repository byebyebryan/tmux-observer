# Installed remote desktop acceptance

Run on Snap with the actual captured Niri desktop and the ordinary strict SSH
route to Starship:

```sh
uv run --extra dev scripts/accept-native-remote-desktop --output /tmp/tmux-remote-desktop.json
uv run --extra dev scripts/accept-native-remote-desktop --with-profile --output /tmp/tmux-remote-desktop-profile.json
```

The fixture installs one exact wheel on both endpoints. Default tmux servers,
owner/fleet units, Mesh preferences and IPC paths belong to its private directory.
The Snap fleet runs the production scanner against the actual desktop; Starship
uses an independent headless context. Separate native tmux reads verify complete
references, names, attachment counts, windows and client PIDs. Returned fleet
frames pass the independent contract reader.

Two owned Kitty instances run literal `ssh -tt ROUTE` shells. Input attaches only
to the remote fixture's private default server and exact owned session ID.
[Kitty remote control](https://sw.kovidgoyal.net/kitty/remote-control/) uses each
instance's private same-UID mode-0600 Unix socket. Niri queries prove the actual
owned window/PID; process-tree reads prove its native SSH child. The tool sends
no global keyboard events and stores no terminal content, argv or environments.

Cases cover initial absence of a qualifying viewer, a unique matched manual
viewer, two ambiguous windows, recovery after closing only the duplicate, rename
and updated title, remote owner loss/replacement and viewer/service stop. Manual
matches remain display-only: observation records contain no action handles.
After rename, the old title must lose its positive. A complete scan may return
`none`, meaning no qualifying viewer for the current reference; transient obsolete
joins may be unknown. This does not mean the independent native client detached.

The optional ten-minute profile keeps one owned remote viewer attached and adds
actual desktop scanner work to the normal two-host profile. Every fleet-owned
child and its associated bridge on the opposite endpoint count against the
selected 96 MiB fleet candidate. Owner RSS retains its 64 MiB target; combined
owner/fleet/associated-bridge mean CPU retains the 5% one-core target. Raw samples
and separate per-service peaks remain in the result. One-second sampling can miss
transient peaks, and protocol byte counters exclude encrypted wire overhead.

Owned Kitty and SSH child incarnations must exit before private backing files
are removed. Unit/native cleanup preserves ordinary sessions and services and
restores the previously focused window when it still exists. This component test
does not establish Starship graphical truth, physical suspend, simultaneous
declared-capacity acceptance, Rofi latency or managed rollout.

Clean installed source `3f79975` passed the seven functional cases plus the
hundred-query and ten-minute collection cases in the [captured result](evidence/2026-10-07-native-remote-desktop-normal-g3-partial.json).
The result is `failed_resource_target`: conservative fleet/associated-bridge
sampled maxima were 82.49 MiB on Snap and 82.40 MiB on Starship, below 96 MiB;
combined CPU was 5.74% and 2.40%, so Snap exceeded the unchanged 5% ceiling.
The owner's sampled maxima stayed below 64 MiB. Neither endpoint started a new
observer SSH connection during the idle interval. RPC p95 was 5.77/3.28 ms and
installed cached CLI p95 was 47.92/36.95 ms; these are not visible Rofi latencies.
All owned windows, SSH children, units and fixture directories were removed.

The original failure remains evidence for that exact artifact. It motivates
optimizing the desktop join's final generation read without changing the cadence,
lease, scope, native generation bracketing or CPU ceiling; later results require
their own clean installed measurement.

The optimized clean source `ab69e9d` passed all nine included cases in the
[new ten-minute profile](evidence/2026-10-07-native-optimized-normal-g3-partial.json).
Both endpoints met the selected normal targets: conservative fleet/associated
bridge sampled maxima were 80.88/75.91 MiB, owner maxima stayed below 64 MiB,
and combined CPU averaged 4.66%/1.96%. No new observer SSH connection started.
Snap's counted native commands fell from 2,475 to 2,082 over the window while
the owner/desktop cadence and source budgets stayed unchanged. The independent
native functional cases, cleanup and profile sampling limits remain as described
above. This accepts the measured normal resource profile, not physical suspend
or the later frontend/managed gates.
