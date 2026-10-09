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

Physical suspend/wake remains unverified but is optional under the user-selected
[always-on scope](always-on-acceptance.md). Freezing a process or injecting a clock
jump does not prove host sleep. Any optional physical follow-up needs isolated
fixtures and confident wake/recovery before interrupting desktop/network work.

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

On 2026-10-08 one [frozen final-candidate wheel](evidence/2026-10-08-final-candidate-artifact.json)
at clean source `3beab8a` passed both resource profiles. The
[desktop-inclusive normal profile](evidence/2026-10-08-final-candidate-normal.json)
records Snap/Starship fleet-plus-associated-bridge peaks of 84.00/57.83 MiB and
combined owner/fleet/associated-bridge CPU of 4.9763%/1.9494%, over at least 600
seconds each, with zero new observer SSH starts. Snap's CPU headroom is narrow;
the mean is not a bound on instantaneous CPU. The
[SSH capacity profile](evidence/2026-10-08-final-candidate-capacity.json) records
a 500.02 MiB conservative sampled peak and ten healthy near-cap queries within
250 ms, including installed decoding/validation. It uses sixteen synthetic
logical owners on two physical endpoints, fifteen actual SSH links and thirty-two
readers. One-second normal and 100 ms capacity RSS sampling can miss transient
peaks; no sixteen-physical-host or capacity-CPU claim follows.

The intervening [frozen-wheel CPU failure](evidence/2026-10-08-frozen-normal-g3-failed-cpu.json)
and [capacity deadline failures](evidence/2026-10-08-optimized-3a-capacity.json)
remain recorded alongside this later pass. The selected direction is validated
within the measured scope. Revised G3 is accepted for always-on hosts with the
[clean frozen-wheel recovery simulations](evidence/2026-10-08-always-on-simulated-recovery.json);
physical sleep/wake is optional. Consumer migration and managed rollout retain
separate gates.

## Boundary extraction CPU review, 2026-10-08

The boundary extraction adds the passive native client-association profile. Its
normal acceptance now reads both endpoints' actual default-server clients and
matching desktop windows, rather than an unattached private fixture. The
unchanged five-percent target remains a promotion gate.

The [latest ten-minute profile](evidence/2026-10-08-boundary-b4/normal-socket-failed-cpu.json)
uses frozen Observer `2cebf8c`, preserves eight ordinary sessions per endpoint,
and sends no graphical input. Snap measures 6.3647% combined owner/fleet/associated
bridge CPU; Starship measures 2.9777%. Sampled fleet/associated-bridge RSS is
82.01/59.33 MiB against 96 MiB, and owner RSS is 26.89/24.15 MiB against 64 MiB.
One hundred validated warm queries per endpoint meet the existing deadline.
Native session references and hooks survive owned-service teardown. The candidate
fails the selected CPU gate and remains unpublished and unselected.

Read coalescing, prepared projection reuse, dependency-stamp reuse, bounded wire
check reuse and fixed read-only Niri socket requests are implemented and tested.
They preserve the two-second owner cadence, existing leases and independent
validation boundaries. The measured result is lower than the preceding 7.2507%
Snap profile, but the runs also contain ordinary desktop changes; this comparison
does not isolate each optimization's contribution.

Two concrete resource directions remain:

1. Review an eight-percent normal combined CPU ceiling for the current Python
   implementation, then validate the exact frozen candidate against that selected
   ceiling. This is eight percent of one core, not eight percent of the whole
   machine. Keep 96/64/768 MiB, query deadlines, logical caps, cadence and freshness
   unchanged. Preserve every failed five-percent record. This proposed budget
   has not been selected or accepted.
2. Retain five percent as a hard promotion gate and continue implementation and
   resource measurement. Further optimization must preserve all passive/native,
   framing, scope, deadline and cleanup requirements; it cannot silently slow
   renewal, subtract instrumentation or omit associated process costs.

Recommendation: review the first direction for this standard-library Python
delivery. The second remains valid if its lower CPU ceiling is a product
requirement. Functional/native/graphical acceptance and paired rollback are
independent of this pending resource decision.

The user asked for the CPU cause rather than selecting a higher ceiling.
Five percent therefore remains required. The subsequent
[system-Python profile](evidence/2026-10-08-boundary-b5/normal-system-python-failed.json)
uses Python 3.14.7 and frozen runtime `ae8df6e` on both hosts. It measures
5.2673%/2.8990% combined CPU and 81.57/81.63 MiB fleet/associated-bridge RSS.
Warm query deadlines pass. Its final exact-roster assertion rejects two
ordinary sessions added on Starship during active use; all original references
remain present in a later independent read. Preserve this failed run and
remeasure with the corrected addition-tolerant preservation harness. These
results improve on the earlier UV-interpreter candidate, but changes in runtime
and active workload prevent assigning the full difference to code changes.

### Why a small session picker has a measurable background CPU cost

The picker is backed by two always-running components per endpoint. The owner
renews native session facts every two seconds and independently samples the
optional client-association profile. The fleet maintains two owner subscriptions,
checks independent leases, prepares the aggregate view and performs current
process/window matching for the desktop adapter. Those jobs continue with the
picker closed so opening it can read prepared state.

The system-Python profile attributes Snap's 5.2673% to 1.8287% local owner,
3.2937% local fleet/children and 0.1449% associated remote bridge. These figures
sum to about 53 ms CPU per second, across all counted processes, on one core.
They measure CPU work rather than elapsed network waiting. The fleet still
performs repeated decoding, semantic validation, copying, hashing and output
encoding; desktop joins also read bounded process trees and recheck incarnations
against opening/closing window captures. This is more work than a single
`list-sessions` call, and some repeated checking of unchanged state is avoidable.

Networking does not appear to be the leading issue in that run: there are zero
new Observer SSH starts during measurement, about 3.1 MiB owner payload received
per endpoint over ten minutes (roughly 5 KiB/s), and only forty Mesh catalog reads
and four route reports per host. Native collection uses approximately 1,188
read-only command processes per endpoint over ten minutes, about two per second.
The older forty-five-second instrumented diagnostic separately identifies
thousands of tree checks and repeated input hashes; its inclusive function
timings cannot be summed or treated as attribution for the new runtime.

The selected optimization direction is to eliminate redundant local work with
immutable prepared data and coalesced bounded reads. It preserves independent
incoming-wire validation, current identity/namespace/lease checks and the
existing sampling cadence. The current immutable-receipt candidate remains
subject to a fresh ten-minute profile. No higher ceiling, slower freshness or
instrumentation subtraction is accepted. A future native event source would
need its own design: tmux hooks or an attached control client change the native
server/client state and do not automatically satisfy passive observation.

The clean [immutable-receipt profile](evidence/2026-10-08-boundary-b5/normal-immutable-failed-cpu.json)
finishes at 5.3614%/2.8556% combined CPU, with memory, warm-query deadlines,
baseline native reference/generation/hook preservation and cleanup passing.
The function saving does not establish lower whole-service CPU in this run;
ordinary remote payload is also larger. It fails Snap's existing CPU ceiling
and remains unselected. The next measured hot path is the full tree traversal,
which still checks every incoming and outgoing document independently.

The [tree-check candidate](evidence/2026-10-08-boundary-b5/normal-tree-failed-cpu.json)
measures 5.0971%/2.6546% combined CPU. Native reference/generation/hook
preservation, memory, cached-query deadlines and cleanup pass. Snap remains
above the five-percent ceiling. A subsequent clock-isolation correction and
field-name traversal optimization require their own frozen acceptance. No failed
profile is rounded, relabeled or promoted as passing.
