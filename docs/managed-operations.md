# Managed Tmux Observer operations

The configuration repository owns the selected pair and host controls in
[deployments/tmux-observer.json](https://github.com/byebyebryan/dotfiles/blob/main/deployments/tmux-observer.json).
This repository owns installed verification, readiness, reader recovery and
paired rollback. Tmux Plus owns frontend/native verification through its public
`scripts/check-installed-artifact` command. Use reviewed tooling checkouts of
both repositories on the deployment host and record their exact commits. No
Snap-only checkout or private sibling import is required.

The accepted 2026-10-12 cohort is Observer a7 / Plus a7, with versioned reader
SDK/shared CLI a15 and the static owned Tmux publisher factory. Exact hashes, per-host scopes,
recovery, paired rollback and reselection are in the
[publisher acceptance record](evidence/2026-10-12-publisher-integration/README.md).
When staging a new external SDK archive through a scoped apply, prepare its
versioned parent directory before applying the `python` archive target. Review
the exact directory, URL/checksum, diff and dry run first. Keep old SDK roots for
paired rollback, and load the owner before recreating any desktop context.

```sh
./scripts/tmux-observer-operations verify --host snap --scope owner --source /absolute/chezmoi --selection /absolute/chezmoi/deployments/tmux-observer.json --frontend-verifier /absolute/rofi-tmux-plus/scripts/check-installed-artifact --output /absolute/private/verify.json
./scripts/tmux-observer-operations verify --host starship --scope desktop --source /absolute/chezmoi --selection /absolute/chezmoi/deployments/tmux-observer.json --frontend-verifier /absolute/rofi-tmux-plus/scripts/check-installed-artifact --output /absolute/private/verify.json
```

The operation is explicit: there is no default apply or recovery. Verification
checks Core/frontend member bytes and executable modes, release manifest,
managed controls, enablement, supported facade/native identity, current local
and remote owner leases, endpoint desktop evidence and fresh CLI state. When
`requirements.localAttachments` is selected, the independent attachment receipt,
source/clock/publisher/generation and complete references must also be current.
Presentation membership grants no operation authority. JSON outputs can contain
private controls and inventories; keep capture files in an owned private tree.

The default `--scope desktop` requires an active desktop service and exactly
one captured fleet context. Explicit `--scope owner` accepts the headless
topology only when the desktop is inactive and no captured fleet is active.
It verifies the same installed pair, controls and owner enablement, current
owner facts and required local attachment evidence, plus direct native generation
and complete references before/after the operation. Fresh CLI inventory remains
an independent check. Desktop bindings, prepared picker frames and viewer
positives are excluded from this scope; they are not normalized to healthy.
Snap's recorded headless baseline uses owner scope; Starship's captured desktop
uses desktop scope. Selecting a scope starts no missing service.

`capture` saves exact controls, separate paired payload archives and ordinary
native reference IDs. Capture alone is not rollback. `recover` restarts only the
selected owner and captured desktop/fleet reader: owner recovery tears down the
old desktop context, so explicitly recreate desktop context, discover its new
fleet and require new incarnations and current leases. No tmux session, provider,
desktop shell or ordinary SSH master is stopped.
Owner-scope recovery restarts only the owner, requires a new publisher and
current attachment evidence, and preserves native generation and complete
references. Capture records its scope; rollback rejects a baseline from another
scope before stopping services. Owner-scope paired rollback stops only the owner
and retains the same staged pair/control recovery guarantees.

`rollback --before /absolute/private/before.json` requires Rofi closed and
verifies the current selection before staging archives. Digests, complete member
coverage, safe paths, size bounds and regular-file modes reject corrupt payloads
before any service stop. The matching Core/frontend pair and only unchanged
captured controls are restored together. Second-tree rename, finalization or
partial-control failure restores the selected pair; retain backups if filesystem
recovery itself fails. Frontend finalization uses the explicit same-user public
verifier. Services remain stopped until explicit reselection/startup. Old
frontend-only captures cannot authorize a paired restore.

Rollback restores installed state while canonical selection remains unchanged.
Review its exact drift, apply only the package roots, public launchers,
versioned unit links/drop-ins, desktop controls and shared Mesh controls, then
start the owner before desktop/fleet context. Create a new versioned SDK parent
before a first scoped install. Use `--force` only after checking restored controls
against the private capture and only on that exact target list. Preserve Agent
bridge/collector/writer selections and unrelated target drift. Shared Mesh CLI
and source controls require both domains' verification after changes.

The owned fixture suite (`tests/test_managed_operations.py`) covers archive
rejection before stop, modes, generated-cache exclusion, paired restore,
replacement/finalization failure, partial control recovery and independent
readiness failures. Source tests, installed/native references, resource ceilings,
graphical input and physical suspend are separate evidence. Pure source cleanup
requires no live lifecycle or recovery operation.
