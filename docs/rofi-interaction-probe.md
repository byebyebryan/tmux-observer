# Early native Rofi interaction experiment

T06 ran on Snap on 2026-10-07 with installed Rofi `2.0.0-dirty` (Arch package
`2.0.0-1`). [Captured evidence](evidence/2026-10-07-rofi-interaction-t06.json)
includes callback logs and native Rofi screenshots before and after navigation.
The owned process used isolated configuration/cache and synthetic references;
no Tmux Plus deployment, service or lifecycle action was involved.

The fixture published revision 2 and changed “Refreshing fixture” to “Ready
fixture revision 2”. Both timer-only and input-change configurations preserved
the final filter/caret: typing `al`, moving one character backward and inserting
`z` produced `azl`, confirmed through native custom-input callback and screenshots.
Right/Left callbacks adopted the new revision and changed/restored the fixture
view. Initial remembered-row selection was supplied through `-selected-row`.

Automatic adoption **is not accepted** by this experiment. The input-change
configuration produced zero callbacks during more than two seconds of continuous
typing; it displayed the old refresh notice until navigation. Its first adoption
was about 2.9 seconds after fixture publication, on the later view callback.
The timer-only variant adopted the update near the first typing event, but neither
case ran a timer callback during the measured initial idle interval. One timer
delivery after interaction is insufficient proof of idle or continuous updates.

The installed build did not expose `ROFI_INPUT`; the custom-input callback's
argument provided the filter/caret check. Selection changed to the first filtered
row during typing, which is distinct from preserving exact identity across a
background redraw. That latter behavior needs an additional focused T14 test.
Screenshots were inspected: the input-change variant still showed the old notice
before navigation, and both final views showed the new notice and `azl` filter.

Rofi's [event configuration documentation](https://davatorium.github.io/rofi/current/rofi.1/)
describes inactivity timeout and input-change actions. The
[2.0.0 view source](https://github.com/davatorium/rofi/blob/2.0.0/source/view.c)
routes those actions through the view and uses a GLib timeout. These interfaces
are investigation inputs, not evidence that a particular Wayland build performs
the needed callback/redraw under every interaction state.

T14 must resolve actual adoption and refresh-notice timing before UI migration.
Investigate the installed Wayland event path and test a supported notification
or native mode integration if script callbacks cannot supply the guarantee. Do
not promise that a prepared-read service alone fixes the visible latency. Owner
and fleet producer work can proceed independently.

The probe first tried a normal window; this Wayland build exposed a layer surface
instead. Input was only sent while the owned PID was the sole Rofi process and
Rofi was the sole exclusive keyboard surface on the focused output. Competing
display-sleep surfaces caused the probe to stop without typing. The desktop was
woken for the authorized test; ordinary tmux/agent sessions were preserved.


A later X11 comparison with the installed `-x11` option could not establish an
owned Rofi surface in the current desktop context. The probe stopped before
sending input and cleaned its process; this does not accept or reject X11 timer
behavior. The optional comparison flag is retained for a verified X11 desktop.
Input guards now require a sole owned Rofi process in both surface forms and
reject competing exclusive layers even when a normal window is focused. The
[upstream backend option](https://github.com/davatorium/rofi#usage) is documented;
no launcher backend change is selected by this investigation.

## Private view-dispatch investigation

Two optional diagnostics build a temporary library and preload it only into the
owned fixture process. Nothing is installed or selected for ordinary Rofi use:

```sh
uv run --extra dev scripts/probe-rofi-interaction --view-wakeup-experiment --output /tmp/rofi-completed-view.json
uv run --extra dev scripts/probe-rofi-interaction --feed-wakeup-experiment --output /tmp/rofi-feed-dispatch.json
```

The first calls `rofi_view_maybe_update` only when Rofi reports a completed view.
The second also dispatches the fixed fixture callback after an atomic feed-file
replacement, independent of the inactivity timer. Both use private Rofi 2.0
symbols; they are diagnostic experiments, not supported frontend dependencies.
The library ignores callback child processes and is removed with the private
directory. It synthesizes no keyboard input. The probe's guarded test input still
requires the sole owned Rofi process and exclusive keyboard surface.

The source of the hypothesis is the pinned
[theme-action path](https://github.com/davatorium/rofi/blob/2.0.0/source/view.c):
theme actions mark a view completed, whereas `rofi_view_maybe_update` processes
completion. The
[Wayland reload path](https://github.com/davatorium/rofi/blob/2.0.0/source/wayland/view.c)
calls that update function. Native comparisons must establish behavior; this
source interpretation alone cannot establish the installed event path.

The strengthened feed experiment first publishes while idle, then publishes
another revision after several typing/backspace cycles. Read-only checkpoint
callbacks record the selected full fixture reference before each publication;
the automatic update callback supplies the after-reference. Later custom-input
acceptance checks filter and caret preservation. Publication/input timestamps,
callback adoption, references and captured native views remain separate evidence.
An implementation for T14 still needs a reviewed, versioned integration with a
supported mode boundary or accepted Rofi fix; the preload is not a rollout choice.
