# Tmux Observer

Passive tmux observation with shared local/fleet views and independent guarded
actions. The host-local core reads session metadata; an explicit owner publishes
it, and prepared readers compose fleet state with this desktop's evidence.

[Project showcase](https://dev.byebyebryan.com/fleet-plus/projects/tmux-observer/) ·
[Get started](docs/getting-started.md) · [Documentation](docs/README.md)

## Inspect local tmux

Requires Linux, Python 3.11+, uv and tmux. From a checkout:

```sh
uv run tmux-observer collect --host-id workstation
```

Replace `workstation` with your configured logical host ID. This explicit direct
read observes the default tmux server. It starts no service, attaches no client
and creates no server/session. Output is metadata, never pane contents.

The [setup guide](docs/getting-started.md) covers the separate owner service,
cached reads and optional fleet reader. Installing a package starts no service.

## Interfaces

| Need | Reference |
| --- | --- |
| Collect or share local state | [Getting started](docs/getting-started.md) |
| Compose prepared desktop/fleet views | [Runtime architecture](docs/runtime-architecture.md) and [service contexts](docs/service-contexts.md) |
| Configure cached Mesh delivery | [Mesh integration](docs/mesh-integration.md) |
| Implement direct/prepared/action clients | [Wire v1](docs/wire-v1.md) and [boundary contracts](docs/boundary-wire-v1.md) |
| Verify or recover a managed installation | [Managed operations](docs/managed-operations.md) |

Observation, cached delivery, explicit passive refresh and actions have distinct
paths. Cached reads start no collection and supply no action authority. Missing,
warming, partial, stale and failed views remain explicit.

This is generic tmux tooling. Agent Plus independently opens native provider
managers and has no Tmux dependency. Native agent session control stays external.

## Develop

```sh
uv run --extra dev ./scripts/check
uv run --extra dev --extra mesh python scripts/check-mesh
```

See [development](docs/development.md) for repository layout and separate source,
package, native, graphical, recovery and physical acceptance gates.

## Releases and history

[0.6.0a9](https://github.com/byebyebryan/tmux-observer/releases/tag/v0.6.0a9)
is published alongside the Tmux Plus 0.12.0a8 bundle. Managed role selection is
recorded separately in [operations](docs/managed-operations.md). Ordinary full
views remain selected; experimental feed/delta adoption is independent.

The [history index](docs/history/README.md) preserves first-delivery plans,
extractions, performance work and dated acceptance. Shared presentation and
project relationships live at [Fleet Plus](https://dev.byebyebryan.com/fleet-plus/).
