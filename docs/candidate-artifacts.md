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

The next artifact acceptance uses the same frozen wheel across installed
producer, owner, fleet, direct-reader and frontend checks. Changing packaged
source requires a new artifact and review of affected evidence. Existing native
records remain valid within their named source/wheel scope; they cannot silently
be relabeled as acceptance of a newly built wheel. Physical sleep remains an
independent G3 case and is deferred by the user on both active hosts.
