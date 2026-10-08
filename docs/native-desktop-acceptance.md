# Installed local desktop acceptance

Run on Snap after the source gate:

```sh
uv run --extra dev scripts/accept-native-desktop --output /tmp/tmux-native-desktop.json
```

The tool builds and installs one wheel into a private environment, then runs an
installed owner and the production fleet/scanner against two disposable default
tmux sessions. It clears ambient tmux and Python import overrides and uses private
preferences/cache. A missing Mesh lookup is explicitly injected to isolate this
local desktop test; it establishes neither native Mesh absence nor remote routing.
The owner/fleet processes here are separate from managed unit/template acceptance.

An owned Unix socket relays only Niri's native read-only `Windows` request to the
actual Snap compositor. A separate direct Niri query and native tmux client roster
prove that the owned Kitty PID/window contains the exact native client attached to
the complete session reference. Source UID, hostname, boot/time namespace, server
generation, creation times, attachment/window counts and hooks are compared with
independent native reads. Returned fleet frames pass the independent reader.
No keyboard input, ordinary session action or compositor-socket mutation occurs.

The cases cover initial known absence, confirmed local presence, live client
switching, rename, owner loss/replacement, desktop endpoint loss/replacement,
headless context isolation and native session survival after viewer/service stop.
Switching must confirm the current reference and revoke the old positive. A
conflicting original attach argv may leave the old row unknown; that conflict
cannot establish an open viewer on the previous session. The result records this
distinction rather than claiming absence from conflicting evidence.

Socket replacement holds the previous owned inode until the new endpoint is bound,
so the test exercises a real inode change without relying on filesystem reuse.
It proves rejection of the old desktop epoch; it does not cover inode-reuse
ambiguity or restart the ordinary compositor. All proxy threads, owned processes
and the private native server must stop before the fixture directory is removed.

The output remains `T12-native-local-desktop-partial`/`passed_partial`. Actual
remote manual SSH matches/conflicts, Starship graphical truth, declared capacity,
physical sleep/wake, resource targets and Rofi/managed rollout need separate
evidence. This tool is a candidate test and does not activate ordinary services.

Clean installed source `fd47581` passed all nine included cases on Snap with
tmux 3.7c and Kitty 0.49.2. The [captured evidence](evidence/2026-10-07-native-desktop-t12.json)
records the installed wheel digest, independent native source identity, exact
client/window/reference join, final frame and preserved native facts. The previous
row after client switching correctly remained unknown because its original attach
argv conflicted with the current native client; the current reference was confirmed
open. The owned fixture directory and viewer processes were absent after completion.
