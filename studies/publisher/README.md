# Isolated cached publisher study

This directory implements the design candidate in
[the publisher plan](../../docs/publisher-extraction-plan.md), outside `src`,
normal entry points and package discovery. It is research code, not SDK adoption.

`generic_publisher.py` represents proposed Mesh-owned generic envelope/proof
construction. Its a13 internal imports are intentional study dependencies;
Observer production must use a separately accepted public Mesh helper.
`native_source.py` represents Observer-owned Service v1 cached IPC policy.
`cli_entry.py` copies the installed a13 CLI and adds only the trusted Python
factory injection seam. Neither an installed file nor Mesh source is modified.

Use a private Python 3.14 environment with the exact reviewed Observer a6, Mesh
a13 and dependency wheels. Run the study with `-I -B`; its runner explicitly
adds this directory and the existing owned native fixture directory. It must
record package/code origins, wheel digests and copied CLI source digests.

The native fixture follows `tests_mesh/native_fixture.py` (MIT, Bryan 2026).
It owns private default-server namespaces, owner processes, a localhost SSH
daemon and keys. The fixed production SSH command runs through the fixture's
private `mesh-plus` executable, with the same source descriptor and strict host
key/UID/clock binding. Trace files contain fixture events only.

Feasibility does not accept a new SDK, certify performance ceilings or alter
managed services, package selection, preferences, Agent, WSS or ordinary sessions.

The [accepted evidence](../../docs/evidence/2026-10-11-publisher-feasibility/README.md)
records 17 study checks and six independent profile cases. The
[review and backlog](../../docs/publisher-extraction-review.md) define the next
producer-first pass.

To replay, install the exact Observer a6 and dependency wheels into two private
Python 3.14 environments: one with Mesh a13, one with Mesh a10. Use only the
hash-reviewed wheels listed in the evidence; do not substitute a source checkout
or editable installation. Linux tmux, OpenSSH client/sshd and ssh-keygen must be
available. The runner creates and removes only its own native/SSH fixtures.
From the repository root, pass absolute environment and wheel paths:

```sh
rtk proxy /absolute/study-env/bin/python -I -B studies/publisher/run_study.py \
  --observer-wheel /absolute/wheels/tmux_observer-0.6.0a6-py3-none-any.whl \
  --mesh-wheel /absolute/wheels/mesh_plus-0.1.0a13-py3-none-any.whl \
  --baseline-wheel /absolute/wheels/mesh_plus-0.1.0a10-py3-none-any.whl \
  --baseline-python /absolute/baseline-env/bin/python \
  --output /absolute/private-output/feasibility.json
rtk proxy uv run --extra dev ruff check studies/publisher
rtk proxy uv run --extra dev ruff format --check studies/publisher
```

The ordinary source check does not discover the study. A successful replay must
have `ok: true`, explicit passing case IDs, no skips, successful independent
profile conformance and matching ordinary-server before/after hashes. The runner
checks final cleanup of its owned native fixture. Dynamic UUIDs, timing and
ordinary-server hashes can differ across runs; immutable input/code digests must
match the checked revision.
