# Service contexts and desktop handoff

These implemented interfaces originated in the first-delivery candidate.
Current selection and installed evidence are recorded in
[implementation status](implementation-status.md) and
[managed operations](https://github.com/byebyebryan/dotfiles/blob/main/docs/tmux-observer-operations.md).
The generic fleet unit defaults to legacy transport; selected managed controls
explicitly pass Mesh transport and source `tmux_default`.

The owner publisher and fleet reader have separate lifetimes. The packaged
`tmux-observer-owner@.service` uses the configured logical host ID. The packaged
`tmux-observer-fleet@.service` uses a captured desktop context ID. Neither unit is
installed or enabled by installing the Python package.

After selecting the accepted bundle and installing the units, desktop startup
explicitly requests its fleet service:

```sh
tmux-observer-client start-context --host-id snap --json
tmux-observer-client snapshot --access cached --expected-host snap --json
```

Use the endpoint's configured Mesh local ID. `prepare-context --host-id snap
--json` captures the file without contacting the user manager. `context` prints
the current context ID without writing files. Cached snapshot/status/probe/watch
and ticket lookup do neither operation and have no direct-collection fallback.
The cached RPC facade has a 250 ms absolute foreground deadline; streaming and
owner probes retain their separate protocol budgets.

Capture writes only PATH, runtime-directory, desktop endpoints, SSH-agent socket,
native temporary-directory selection and the fixed owner ID. All variables have
explicit values, including empty desktop values for a headless context. It does
not import the caller's full environment into the user manager. The private
environment file overrides the unit's empty desktop defaults; systemd reads it
before executing the service. Its quoting follows the
[systemd.exec EnvironmentFile rules](https://raw.githubusercontent.com/systemd/systemd/main/man/systemd.exec.xml).
Dollar signs/backticks remain literal, not shell commands.

Files live at `$XDG_RUNTIME_DIR/tmux-observer-client/context-CONTEXT.env`, with a
0700 parent and 0600 files. Capture is complete before publication, bounded to
64 KiB per file and 16 contexts, and serialized by a private lease. Existing
different data is a conflict rather than an implicit rebind. The service verifies
that its instance ID matches the environment, UID, boot and time namespace.

`start-context` resets only its named unit's failed/start-limit state and requests
start. A `start_requested` response establishes manager acceptance, not a ready
sample; query readiness separately. Start does not enable the instance. Context
IDs include boot identity, so desktop startup must prepare/request the current
instance rather than persistently enable an old instance name.

Stop the specific context on desktop teardown or before replacing its captured
environment:

```sh
tmux-observer-client stop-context --context-id CONTEXT --json
```

Stop addresses only that fleet instance and removes its verified capture file
after the manager accepts the stop. A failed stop preserves the file. It does not
stop an owner publisher or native sessions. Socket parents are not managed by a
unit-wide RuntimeDirectory cleanup. The unit uses control-group cleanup, a
five-second stop budget, and bounded restart admission. Same-path compositor
replacement invalidates desktop epochs inside the running fleet; owner leases
remain independent. Other desktop contexts are separate instances.

Native environment parsing, installed unit bytes, two-host fleet acceptance and
managed startup/teardown have separate recorded gates. Owner availability across
SSH logout still requires endpoint-specific user-manager policy validation;
this helper does not enable lingering.
