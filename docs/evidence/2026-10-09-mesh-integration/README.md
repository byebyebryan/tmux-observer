# Mesh migration candidate evidence

The source migration is reviewable; promotion is pending. Every descriptor
retains `built_unaccepted`. Gate reports establish only their stated scopes.

| Component | Version | Source |
| --- | --- | --- |
| Mesh Plus | 0.1.0a4 | `2cc12accb331db7ee65ab426da09576a907b291c` |
| Tmux Observer | 0.6.0a1 | `9e5a8752b6f4715969ab4fd669951cbdf6a87219` |
| Tmux Plus | 0.12.0a1 | `dac43deab6847f58b432fe9b6ff0fbd7a6f85db8` |

[The exact tuple](tuple.json) records wheel/bundle hashes, Python ABI,
dependency inputs, gate state and remaining acceptance.
[Observer](observer-candidate.json) and [frontend](frontend-candidate.json)
descriptors preserve full source/payload manifests. Their wheels are independently
repeatable, as is the managed frontend bundle. This is assembly evidence.

[Source gates](source-gates.json) report 380 Observer tests, seven locked bundles
and 45 independent cases; 293 Plus tests; and Mesh's 56-test core gate with zero
skips. A pre-existing one-second deferred-session fixture failed in an earlier
run and passed both isolated and whole-gate retries without runtime changes.
The final gate passes. Review regressions cover late acknowledgements and a
ready owner replacement incorrectly completing a ticket from its old epoch.

[Installed native acceptance](installed-native.json) checks all 83 Observer
runtime modules before exercising cached reads, one shared Mesh reader,
post-request refresh confirmation, retained unknown metadata after catalog loss,
and native passivity/outage/restart/complete-empty over disposable servers and
real localhost SSH. All four integration tests pass without skips. These are two
logical hosts, not deployed Snap/Starship transport acceptance.

[Installed frontend checks](installed-plus.json) compare all 30 descriptor
payloads, validate its exact Observer pin and verify the native Rofi ABI.
[Whole-tuple parity](installed-tuple-parity.json) compares installed payload bytes
against all eight wheels, including compiled `rpds-py`, and Mesh modules/schema
resources against the frozen source. The dependency wheels are recorded in
[runtime-wheels.json](runtime-wheels.json), for CPython 3.14 on x86_64 Linux.

The owned ten-minute resource probe is recorded separately in
[owned-resource.json](owned-resource.json). Its fixture has nine disposable
sessions per logical host, a real SSH bridge, no desktop scanner and a fixed
catalog. It includes all observed fleet/bridge children and local owner children;
RSS sampling can miss peaks and reaped-child CPU can conservatively count twice.
It excludes ordinary desktop/authority CLI cost, the remote owner/SSH server
budget and declared capacity. A probe pass does not close those promotion gates.

Snap is unattended with screens off. DMS exclusive fade-to-DPMS layers caused
the graphical input guard to refuse typing. The final a4 graphical gate is
pending. Retained `superseded-a2-picker-*` reports are earlier artifacts: Mesh
warm-frame p95 153.1 ms and legacy 164.1 ms both missed 150 ms. The diagnostic
skipped timing and refused input; it is not graphical acceptance. No threshold
or focus guard was weakened. Superseded resource reports are not final-tuple
acceptance either.

Python 3.14.7 and the Rofi executable digest match on Snap and Starship. This
read-only comparison does not install a candidate or establish Starship GUI
behavior. Tmux services retained their original running processes. Concurrent
Agent/Mesh source and managed work was preserved; the public Agent Mesh
environment lacks the Tmux package and source, so it is not yet a Tmux bridge.

Promotion still requires final Snap graphical/timing acceptance, ordinary
two-host resources, declared capacity, public artifacts/CI, shared launcher and
source reconciliation with both domains verified, and serial installed
selection/recovery/rollback. Physical suspend and Starship foreground input
remain excluded. See the [rollout plan](../../mesh-integration.md#candidate-rollout).
