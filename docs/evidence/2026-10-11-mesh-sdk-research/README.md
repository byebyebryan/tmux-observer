# Mesh SDK integration feasibility

Checkpoint: 2026-10-11, following experiments started on 2026-10-10. Released
Mesh a11 can carry an Observer-owned pure Tmux profile while preserving the
a10 native projections and effective selections. The
[integration plan](../../mesh-sdk-integration-plan.md) defines implementation
and package, consumer and managed acceptance separately.

[The summary](summary.json) binds exact inputs, outcomes and limits;
[checksums](checksums.json) bind the archived probes and reports. No production
runtime, artifact pin, frozen contract or installed service changed.

## Inputs and experiments

[Artifact inputs](artifacts.json) are downloaded immutable release wheels with
verified hashes: Mesh 0.1.0a10 and 0.1.0a11, and Observer 0.6.0a5. Separate
temporary environments installed those wheels, jsonschema 4.26.0 and Ruff
0.16.6. All 83 Observer runtime Python members match the clean `3de61eb` harness.
The six Tmux oracle inputs come from Mesh's frozen Read examples, excluding WSS.

| Experiment | Outcome | Evidence |
| --- | --- | --- |
| A10 reference baseline versus a11 explicit owner profile | Six exact native projections and 18 effective selections equal; identical sample digest | [Baseline](baseline.json), [profile](profile.json) |
| Native and Mesh adversarial admission | Eight invalid cases rejected; empty required evidence yields zero positives | [Profile report](profile.json) |
| Pure callback boundary | Nine callback methods pass with file/process/socket I/O blocked; native implementations, Agent and Mesh reference integration imports blocked | [Profile report](profile.json) |
| Configured IPC with explicit profile | Poll, watch, disconnect revocation and complete owned retirement pass; `tmux_default` selector remains separate from native `default` receipt | [Profile report](profile.json) |
| Existing Observer a5 / Mesh a10 integration | Eight tests pass, no skips | [Baseline gate](mesh-baseline.json) |
| Existing Observer a5 / Mesh a11 compatibility | Eight tests pass after the labelled in-memory admission substitution, no skips | [Compatibility gate](mesh-admission-only.json) |
| Explicit profile injected into prepared fleet worker | Seven existing synthetic fleet cases pass with implicit reference profiles blocked, no skips | [Explicit gate](mesh-explicit-profile.json) |
| Explicit a11 reader with a10 remote bridge | Owned real tmux and loopback SSH case passes, including refresh, passivity, owner restart, empty state and cleanup | [Mixed native gate](mesh-mixed-native.json) |

The model in [profile_probe.py](profile_probe.py) uses only the supported pure
`tmux_observer.native` and `delivery` facades for native interpretation. It
implements the structural SDK interface without reference-codec inheritance.
The production core, collector, owner, desktop, action and Agent implementations
are forbidden imports during the pure/configured-IPC probe. Mesh independently
rejects proof digest forgery, expiry extension, receipt removal, duplicate
identities and foreign rows. Owner validation rejects native boolean counters.

[probe.py](probe.py) records the independent reference baseline and the explicit
model separately. Expected output is not derived by calling the tested model.
Its native state is copied to avoid aliasing in the experiment; those copying
choices are not accepted production performance decisions.

[run_mesh_gate.py](run_mesh_gate.py) runs the existing harness against installed
wheels. Observer a5's real version guard rejects a11; the report preserves that
negative. Compatibility experiments substitute the worker's admission string
with a10 in memory while installed Mesh remains a11. Explicit-profile cases
add reader/guard injection in memory and reject implicit `ReferenceProfile`
construction. The cached publisher remains the reviewed reference adapter.
These hooks demonstrate feasibility, not implementation of a new producer.

Native fixture servers use private owned `TMUX_TMPDIR` default-server namespaces,
private keys and a loopback-only SSH daemon. Cleanup terminates only those owned
processes and removes their fixture directories. Ordinary tmux sessions,
production sockets, services and managed controls are outside the experiments.

## Concurrent conformance work

During this research Mesh committed maintenance planning at `d2af3c2` and began
an uncommitted a12 `mesh_plus.testing` kit. A five-file private snapshot is bound
by [its manifest](draft-testing-snapshot.json). The snapshot ran on installed
a11 with this model: six fixed Tmux oracle cases pass; a deliberately empty
receipt callback produces three assertion failures and zero errors.
[The draft report](draft-conformance.json) retains both outcomes.

The draft kit and corpus are not an accepted or installed a12 artifact. Owner
tests can adopt its published interface after its separate wheel/portability
gates pass. Its independent expected states are useful supplementary validation;
a11 owner integration does not depend on completion of that Mesh work.

A subsequent [source/release follow-up](followup.json) records the committed
conformance kit at `64173d5` and diagnostics at `e91f828`. The reviewed SDK,
profile, reader and guard implementation files remain byte-identical to the
a11 handoff checkpoint; a11 is still the latest published release at that check.
This follow-up does not rerun the draft probe against the expanded kit or certify
the a12 candidate. The archived draft result keeps its original provenance.

## Reproduction

Use the named Observer harness and Mesh fixture checkpoints in the recorded
workspace paths. Copy the three archived Python probes to one private directory.
Create `a10` and `a11` virtual environments alongside those files, install the
exact hash-verified wheels above and pin jsonschema 4.26.0/Ruff 0.16.6. The mixed
native helper locates its a10 bridge interpreter relative to its own file.

Run the baseline and profile probes separately, then compare their `samples`:

```sh
rtk proxy /absolute/private/a10/bin/python /absolute/private/probe.py baseline --output /absolute/private/baseline.json
rtk proxy /absolute/private/a11/bin/python /absolute/private/probe.py profile --output /absolute/private/profile.json
rtk proxy /absolute/private/a10/bin/python /absolute/private/run_mesh_gate.py baseline --output /absolute/private/mesh-baseline.json
rtk proxy /absolute/private/a11/bin/python /absolute/private/run_mesh_gate.py admission-only --output /absolute/private/mesh-admission-only.json
rtk proxy /absolute/private/a11/bin/python /absolute/private/run_mesh_gate.py explicit-profile --output /absolute/private/mesh-explicit-profile.json
rtk proxy /absolute/private/a11/bin/python /absolute/private/run_mesh_gate.py mixed-native --output /absolute/private/mesh-mixed-native.json
```

The native modes additionally require tmux, OpenSSH client/key tools, sshd and
Linux BOOTTIME/IPC support. Missing dependencies are failures rather than silent
acceptance. Reproduction with different source, harness or package bytes needs
its own report; it does not update this checkpoint.

## Acceptance limits

The SDK/profile boundary is feasible. A proper Observer implementation still
needs normal source/import tests, a new frozen producer artifact, explicit-profile
native acceptance, performance/resource measurements and downstream artifact
selection. Cached publisher extraction still needs review of Mesh's fixed remote
CLI factory. Managed verification also needs an accepted headless path for Snap.

These experiments establish no live deployment, installed candidate resource
ceiling, production recovery/rollback, graphical behavior or physical suspend
acceptance. No artifact was published or selected by this research.
