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
| `docs/history/` | Completed designs and original acceptance workflows |
| `docs/evidence/` / `artifacts/` | Dated exact-input evidence and artifact provenance |

The public native facade is `tmux_observer.native`; the compatibility facade
is `tmux_observer.public`. Prepared reads use `tmux_observer_client.public`;
actions use `tmux_observer_actions.public` independently.

## Independent acceptance

Use owned disposable sessions/endpoints for authorized native probes. Preserve
ordinary sessions, hooks, sockets, attachments and desktop services. Frozen
contract checks do not accept native passivity or a different consumer package.
See [managed operations](managed-operations.md) and the
[historical acceptance guides](history/README.md#delivery) for exact proof scopes.

## Documentation maintenance

Keep setup/current semantics in [the index](README.md)'s maintained guides.
Move completed plans and dated studies into history. Preserve evidence and
frozen contracts byte-for-byte; use forwarding pages when their old links need
to survive. Do not copy rollout ledgers into the README or runtime architecture.
