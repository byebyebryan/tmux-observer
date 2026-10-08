# Candidate artifact preparation

The development builder produces one wheel from a committed Git snapshot with
an exact, hashed setuptools build constraint. It prepares a candidate for later
independent acceptance; it does not publish, select managed pins, start services
or establish runtime, GUI or deployment acceptance.

```sh
python3 scripts/candidate-artifact build --revision HEAD --output /tmp/to-candidate-new
python3 scripts/candidate-artifact verify /tmp/to-candidate-new/candidate.json
```

The output must be a new directory. Existing directories and symlinks are
refused. Extraction, build and validation occur in a temporary sibling before
the complete candidate directory is exposed. Working-tree modifications and
untracked files are excluded; the builder never resets the checkout. Source
archives containing links or special files are rejected.

`packaging/build-requirements.in` names the reviewed build dependency;
`packaging/build-constraints.txt` pins its version and distribution hashes.
The builder uses the constraint from the selected source commit, with build
isolation and required hashes. Regenerate the constraint deliberately with:

```sh
uv pip compile --generate-hashes --no-header --no-annotate \
  --output-file packaging/build-constraints.txt packaging/build-requirements.in
```

`SOURCE_DATE_EPOCH` is the source commit time. The descriptor records the commit,
tree, epoch, package version, Python/uv versions, backend generator, constraint
and executing builder checksums. Every runtime Python file, contract file,
service template and license must be present and byte-identical to the committed
source. Generated wheel metadata is covered by the member manifest. Repeated
builds can be compared by wheel SHA-256; evidence must state the actual tool
versions and scope tested rather than infer reproducibility on every platform.

`candidate.json` always has state `built_unaccepted`. Verification checks the
wheel checksum/size, safe member paths, package layout, exact member manifest,
source-member mapping and all three bundled contract manifest digests without
importing the candidate. The descriptor is local provenance, not a signature:
an independent acceptance record and later managed pin must name the reviewed
wheel checksum. A wheel plus a replaced descriptor is not an authenticated
source or an accepted release.

Each native/installed acceptance coordinator accepts `--artifact PATH/candidate.json`.
It copies and verifies the exact frozen wheel instead of running a build. For
example:

```sh
uv run --extra dev python scripts/accept-native-collector \
  --artifact /tmp/to-candidate-new/candidate.json --output /tmp/to-g1.json
uv run --extra dev python scripts/accept-native-owner \
  --artifact /tmp/to-candidate-new/candidate.json --output /tmp/to-g2.json
uv run --extra dev python scripts/accept-native-fleet \
  --artifact /tmp/to-candidate-new/candidate.json --output /tmp/to-g3-partial.json
```

The option is also available on context, direct, desktop, remote-desktop,
suspend and capacity coordinators. It is rejected in private worker modes;
installed workers receive only the already selected wheel. It changes no test
scope or physical-sleep authorization. Omitting the option preserves checkout
build mode.

Frozen-input records name the artifact's `sourceCommit` and checksum separately
from `harnessCommit`/`harnessTreeDirty`. All packaged runtime/data/license files
must match the harness checkout, including its complete tracked file set. This
prevents source-level native race cases from silently testing different code.
Untracked generated caches do not count as packaged source. Copied inputs are
verified again before installation, and existing destination files are preserved.

The next artifact acceptance uses the same frozen wheel across installed
producer, owner, fleet, direct-reader and frontend checks. Changing packaged
source requires a new artifact and review of affected evidence. Existing native
records remain valid within their named source/wheel scope; they cannot silently
be relabeled as acceptance of a newly built wheel. Physical sleep remains an
independent G3 case and is deferred by the user on both active hosts.

## Recorded preparation

Clean source `3437633` passed 164 source tests and two independent builds with
CPython 3.14.7, uv 0.8.22 and setuptools 84.0.0. Their 69-member wheel bytes were
identical. The [preparation record](evidence/2026-10-08-candidate-artifact-preparation.json)
names its SHA-256 and includes the exact isolated installation probe. The same
wheel installed on Snap and Starship: all 64 runtime/data/license members and
three contract checksum manifests matched; import origins and both entry-point
help commands passed. Temporary install roots were removed. No service or native
collection was requested, and this wheel remains unaccepted for those gates.

Clean harness `d107b04` exercised that same wheel independently: [G1](evidence/2026-10-08-frozen-g1.json)
passed 14 cases, [G2](evidence/2026-10-08-frozen-g2.json) 11,
[context](evidence/2026-10-08-frozen-context-t12.json) four,
[direct](evidence/2026-10-08-frozen-direct-t10.json) 24 and
[fleet](evidence/2026-10-08-frozen-fleet-g3-partial.json) 15. Those 68 passed
cases establish only their recorded scopes.

The same wheel's [ten-minute desktop profile](evidence/2026-10-08-frozen-normal-g3-failed-cpu.json)
passed functional, memory and foreground timing checks but failed Snap's unchanged
5% combined CPU target at 5.1046% (Starship: 2.0739%). Sampled fleet/associated
bridge peaks were 82.04/57.63 MiB against 96 MiB, with zero new observer SSH starts.
The [capacity run](evidence/2026-10-08-frozen-capacity-failed-query.json) stopped
after six passed cases when a validated near-cap healthy-reader reply exceeded
250 ms. Its original harness lost the numeric duration and RSS result on that
assertion; the failure reconstruction states those limits. Both temporary
capacity roots were verified absent afterward. Neither failure is superseded by
the earlier, separately scoped resource passes, and this candidate is not
accepted for G3 or promotion. Physical sleep remains separately deferred.
