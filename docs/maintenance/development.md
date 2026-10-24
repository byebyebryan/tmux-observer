# Development

Use Python 3.11+, uv and tmux on Linux. From maintained `main`:

```sh
uv run --extra dev ./scripts/check
uv run --extra dev --extra mesh python scripts/check-mesh
```

The first is the source, contract, lint and format gate. It uses the declared
dev dependencies. The second adds separately selected Mesh integration checks.
Neither command alone establishes installed native, graphical, managed recovery
or physical sleep/wake acceptance.

## Repository map

| Path | Contains |
| --- | --- |
| `src/tmux_observer/` | Passive native collection and owner service |
| `src/tmux_observer_client/` | Direct/prepared fleet and desktop composition |
| `src/tmux_observer_actions/` | Independent guarded lifecycle/window actions |
| `contracts/` | Canonical versioned wire bundles and fixtures |
| `systemd/` | Units, installed/started only by explicit deployment |
| `scripts/` / `tests/` / `tests_mesh/` | Source, integration and scoped acceptance tools |
| `docs/guides/` / `docs/reference/` | Current workflows and interface references |
| `tests/fixtures/` / `artifacts/` | Executable fixture inputs and artifact provenance |

The public native facade is `tmux_observer.native`; the compatibility facade
is `tmux_observer.public`. Prepared reads use `tmux_observer_client.public`;
actions use `tmux_observer_actions.public` independently.

## Independent acceptance

Use owned disposable sessions/endpoints for authorized native probes. Preserve
ordinary sessions, hooks, sockets, attachments and desktop services. Frozen
contract checks do not accept native passivity or a different consumer package.
See [managed operations](operations.md) for current selection and exact proof scopes.

## Documentation maintenance

Keep only `README.md` and `getting-started.md` at the docs root. Use lowercase
kebab-case filenames in one shallow topic folder: `guides/` for workflows,
`reference/` for current interfaces, and `maintenance/` for development/operations.
Media belongs in `assets/`. Mesh's hash-locked `contract-freeze.md` is the sole
root exception; its original bytes remain normative input.

Update or consolidate the existing guide instead of adding a dated plan,
handoff or status page. Delete superseded notes; Git retains earlier revisions.
Do not add forwarding pages or copy old reports into the current docs tree.
Keep executable test data beside tests, not under docs. Record necessary release
provenance with an immutable Git/release link in the operations guide.

Run `scripts/check-docs` and the canonical source gate before committing. The
docs check enforces this layout and checks local links/heading fragments.
Package, native, managed, consumer and physical acceptance remain separate.
