# Resource design decision

The initial memory targets are design candidates. Installed measurements now
show that the current Python/SSH process layout exceeds them. CPU, cached-query
latency, logical caps and source freshness remain independent requirements.
This review records alternatives and the selected candidates for validation;
it does not establish acceptance of a replacement budget.

## Measured facts

| Profile | Observed cost | Evidence and limits |
| --- | --- | --- |
| Normal two-host fleet and associated bridge | Snap 67.23 MiB, Starship 77.79 MiB | [Ten-minute clean profile](evidence/2026-10-07-native-fleet-input-cache-g3-partial.json); conservative sum of sampled maxima, includes owned Mesh work and the opposite endpoint's bridge |
| Normal combined owner/fleet/bridge CPU | Snap 4.40%, Starship 2.43% of one core | Same profile; meets the 5% target; does not establish capacity CPU |
| Desktop-inclusive normal fleet and associated bridge | Snap 82.49 MiB, Starship 82.40 MiB | [Clean manual-viewer profile](evidence/2026-10-07-native-remote-desktop-normal-g3-partial.json); below the selected 96 MiB ceiling, but one-second RSS sampling can miss transient peaks |
| Desktop-inclusive combined owner/fleet/bridge CPU | Snap 5.74%, Starship 2.40% | Same profile; Snap fails the unchanged 5% ceiling; exact failed artifact retained |
| Sixteen synthetic installed owners and local bridges | 307.65 MiB sampled fleet/bridge peak | [Clean capacity fixture](evidence/2026-10-07-installed-capacity-t12-partial.json); includes fifteen plain bridges, omits actual SSH costs; fleet worker includes fixture imports |
| Optimized desktop-inclusive normal profile | Snap 80.88 MiB / 4.66% CPU; Starship 75.91 MiB / 1.96% CPU | [Clean ten-minute rerun](evidence/2026-10-07-native-optimized-normal-g3-partial.json); meets selected 96 MiB and unchanged 5% CPU targets in this measured profile |
| Sixteen logical owners over fifteen actual SSH links, with maximum readers/frames | 501.24 MiB conservative fleet/SSH/associated-bridge sampled peak | [Clean SSH capacity profile](evidence/2026-10-07-installed-ssh-capacity-t12-partial.json); below 768 MiB, with synthetic facts/catalog on two physical hosts |

The normal Starship peak contains a 27.32 MiB fleet, 10.95 MiB SSH child and
20.69 MiB Mesh CLI child. Its associated bridge adds approximately 18.84 MiB.
The sixteen-owner fixture separately confirms that bridge processes multiply;
it does not extrapolate native maximum load from a single SSH connection.
RSS accounting includes each owned process, including remote bridges attributed
to the originating fleet. Shared-page/PSS reinterpretation, excluded dependency
work and slower authority renewal cannot be used to pass these RSS targets.

## Alternatives

1. Keep the current standard-library Python core and persistent SSH design.
   Review candidate budgets of 96 MiB for the normal two-host fleet/children and
   768 MiB for the declared sixteen-owner/maximum-subscriber profile. These are
   proposed ceilings, not measured acceptance: normal desktop work, simultaneous
   near-cap readers, retained documents and actual fifteen-link SSH capacity still
   require measurement. The owner target and 5% normal combined CPU target remain.
2. Keep 64/256 MiB targets and reduce process footprint. A smaller native stdio
   bridge may remove much of each remote Python process cost, but adds a runtime
   artifact/dependency and a new framing, scope, deadline and cleanup acceptance
   boundary. Mesh/native desktop transient costs still need treatment. Cadence
   reductions alone cannot remove sampled process peaks.
3. Reduce the prepared-service owner limit and remeasure. Four cached owners
   would cover the present two-host fleet with room for growth, but changes the
   planned sixteen-owner capacity. It does not solve normal two-host peak memory
   by itself. The released explicit direct CLI's 128-host limit stays compatible.

Recommendation: review the first option for the initial prepared-read delivery,
with honest supported ceilings established only after the remaining profiles.
It preserves passive observation, conservative validity and the small deployment
dependency surface. Retain the initial failed results and record the selected
decision separately from its later native acceptance. No proposed number changes
logical queue/document caps, authority leases or the foreground deadline.

Physical suspend/wake remains an independent gap. Freezing a process or injecting
a clock jump does not prove host sleep. Prepare isolated fixtures and verified
wake/recovery steps before scheduling any whole-host suspend that would interrupt
ordinary desktop/network work.

## Selected direction

On 2026-10-07 the user selected review and validation of 96/768 MiB budgets for
the current Python design. Use these candidate fleet ceilings in the next normal
and declared-capacity profiles. Preserve the original 64/256 MiB failures and
their exact artifacts. The owner ceilings, normal combined CPU target, clock and
freshness rules, query deadline and logical queue/retention caps remain unchanged.

The existing headless two-host samples are below 96 MiB, and the installed local
bridge fixture is below 768 MiB. Neither observation closes the missing native
desktop/resource or actual SSH capacity profiles. Report the selected target and
measurement scope explicitly with each new evidence file.

Clean source `ab69e9d` subsequently passed the selected normal and declared
logical-capacity measurement profiles above. The owner ceilings, normal CPU
target, RPC deadlines and logical bounds also held. The earlier failed profiles
remain unchanged. These measured profiles validate the selected direction for
the initial Python design; sample intervals can miss transient peaks, and the
capacity facts/catalog are synthetic despite actual SSH/process costs. They do
not establish physical sleep/wake, sixteen physical native hosts or managed
rollout. G3 retains those separate acceptance boundaries.
