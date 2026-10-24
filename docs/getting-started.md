# Local and cached tmux reads

Use Python 3.11+, uv and tmux on Linux. Run the examples from a maintained
checkout. Installing the package does not install/enable units or start native
sessions. The examples below use a configured host named `snap`; substitute
your logical local identity and runtime path.

## Use the read interfaces

Examples use `snap` as a configured logical host ID. Substitute your endpoint's
Mesh local ID. Python 3.11+ is required; native/service support targets Linux.
From this checkout, run an explicit fresh local read:

```sh
uv run tmux-observer collect --host-id snap
uv run tmux-observer collect --host-id snap --panes --option @example
```

`collect` reads the configured default tmux server. It starts no service,
attaches no client and creates no server or session. It emits metadata only.

The owner publisher is an explicit, long-running operation. Run it separately
before querying its prepared state:

```sh
uv run tmux-observer owner --host-id snap --local-attachments
```

In another terminal, these operations read the running owner:

```sh
uv run tmux-observer status --expected-host snap
uv run tmux-observer snapshot --expected-host snap
uv run tmux-observer watch --expected-host snap
```

A fleet reader needs the configured Mesh authority, a `tmux_default` source
on each participating host and already running owners. The selected backend
is explicit:

```sh
uv run --extra mesh tmux-observer-client fleet --host-id snap --transport mesh
```

In another terminal with the same desktop environment:

```sh
uv run tmux-observer-client context
uv run tmux-observer-client snapshot --access cached --expected-host snap --json
uv run tmux-observer-client watch --expected-host snap --json
```

Cached reads and subscriptions start neither services nor native collection.
Missing, warming, failed and incompatible services return explicit states;
they never fall back to a fresh read. The generic fleet CLI defaults to
`legacy`; managed selection passes `--transport mesh` explicitly.

Fresh fleet diagnosis remains a separate operation, returning Tmux Session v1:

```sh
uv run tmux-observer-client snapshot --access direct --json
```

Explicit passive refresh returns a scoped ticket. Use the reply's fleet
publisher and ticket IDs for lookup:

```sh
uv run tmux-observer-client refresh --source snap:owner --source snap:desktop --json
uv run tmux-observer-client refresh_status --publisher-id UUID --ticket-id UUID --json
```

Package installation does not install or enable user units. Deployment captures
desktop context and starts services explicitly; see [service contexts](guides/service-contexts.md)
and [current Mesh source configuration](guides/mesh-integration.md#current-configuration).

For current transport/source setup use [Mesh integration](guides/mesh-integration.md).
For development use [the source guide](maintenance/development.md); the
[documentation index](README.md) separates contracts from dated records.
