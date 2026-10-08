# Always-on fleet acceptance scope

Decision: 2026-10-08, explicit user direction. Snap and Starship are expected to
remain on. Routine whole-host sleep/wake is a nice-to-have, not a prerequisite
for G3, frontend migration or managed deployment. This supersedes the original
physical-suspend requirement in those gates.

Snap must remain awake during active work. Starship is remote with no validated
unattended wake/recovery path: the earlier RTC dry run established permission,
not hardware wake or network recovery. This pass uses simulations and changes no
host power state or alarm. The [physical procedure](native-suspend-acceptance.md)
is retained for an optional future test with a confident recovery path.

## Required recovery behavior

Always-on hosts can still lose connectivity, stall, restart or deliver queued
data late. The implementation retains BOOTTIME budgets and conservative leases.
Native passivity, installed bytes, both-direction SSH, desktop truth, capacity,
resource/query budgets, frontend behavior and managed recovery retain their
independent evidence requirements.

| Case | Required behavior | Evidence |
| --- | --- | --- |
| Peer silent; old heartbeat arrives after expiry | Remote remains historical; local owner and viewer remain usable | Composed owner/fleet simulation with independent owner clocks |
| Reader callbacks withheld for 30 seconds | First prepared frame immediately rejects both expired owners and Open membership, before scheduler/proof processing | Composed production owner/fleet simulation |
| Old native, desktop or matching probe result arrives after the gap | Reject late work; preserve full historical references | Same simulation, then fresh collection/proof/desktop readmission |
| Complete matching reply queued in a real child pipe across the gap | Reject before draining expired input; reap only the owned relay child | Production transport with a disposable local relay process |
| BOOTTIME advances while normal process polling stays short | Reject late native work against its BOOTTIME budget | Existing process-runner clock-jump simulation with an owned child |
| SSH disconnect, scope/restart/nonce faults, Mesh changes | Independent sources and reads continue; require guarded resync and new proof | Existing two-host [fleet evidence](evidence/2026-10-08-final-candidate-fleet.json) |
| Native session/viewer truth and service resources | Preserve ordinary sessions and meet selected budgets | Other same-wheel records in [current status](implementation-status.md) |

The composed tests call the production prepared-frame path with withheld
callbacks and explicit independent clock values. They use synthetic native
samples, not tmux or physical power. The pipe test exercises a real child and
kernel buffering with a simulated elapsed deadline, not an actual SSH network.
Together with existing awake-host tests, these establish the revised operating
scope; they do not establish physical suspend or hardware wake.

## Repeatable frozen-wheel check

```sh
uv run --extra dev python scripts/accept-simulated-recovery \
  --artifact /path/to/candidate.json --output /tmp/simulated-recovery.json
```

The coordinator verifies the descriptor and matching checkout payload, stages
the frozen wheel without rebuilding it, installs in a disposable environment,
verifies every packaged runtime/data/license file and import origin, and runs
the four selected simulations against that installed runtime. It records
source and harness provenance separately, returns failure on any failed case,
and removes its private installation and owned relay. It has no power operation
or ordinary-service activation path.

## Recorded acceptance

Clean harness `791df63` passes 186 source methods and all four
[installed simulations](evidence/2026-10-08-always-on-simulated-recovery.json).
They consume the existing `3beab8a` frozen wheel
(`b511fb12304b7693879f7fb878ddacd1c32f1afa6e4ccf2738d34405f24a4b84`),
verify all 64 payload files and installed import origins, and complete owned
cleanup. Packaged production code is unchanged. Together with the existing
same-wheel awake-host evidence, this closes revised T12/G3 for always-on hosts.
T13/T14 may proceed against that accepted producer. Physical sleep/wake remains
optional and unverified; G4 and deployment keep independent acceptance gates.
