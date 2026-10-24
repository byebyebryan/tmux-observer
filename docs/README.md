# Tmux Observer documentation

Start with [local and cached reads](getting-started.md), or visit the
[Fleet Plus walkthrough](https://dev.byebyebryan.com/fleet-plus/projects/tmux-observer/).

## Use and operate

| Guide | Purpose |
| --- | --- |
| [Getting started](getting-started.md) | Explicit local collect, owner hosting, cached and fleet reads |
| [Runtime architecture](runtime-architecture.md) | Native, owner, Mesh, desktop, action and UI boundaries |
| [Service contexts](service-contexts.md) | Captured desktop environment and explicit start/teardown |
| [Mesh integration](mesh-integration.md) | Fixed source configuration and explicit transport selection |
| [Managed operations](managed-operations.md) | Artifact selections, readiness, recovery and rollback ownership |

## Develop a client

| Reference | Purpose |
| --- | --- |
| [Wire v1](wire-v1.md) | Observation, Service and Fleet contracts |
| [Boundary wire v1](boundary-wire-v1.md) | Native attachment, desktop association, bindings and action contracts |
| [Mesh preparation](mesh-preparation.md) | Optional prepared domain facade and independent qualification |
| [Development](development.md) | Source/integration checks, layout and documentation ownership |

Core observation is passive. Actions require separate explicit intent and fresh
validation. Cached delivery never changes into direct collection on failure.
Tmux retains generic workflows independently of native agent runtime control.

## History and evidence

The [history index](history/README.md) groups original implementation plans,
extractions, releases, performance studies and acceptance guides. Future-tense
steps there belong to their checkpoint, not a new backlog. Experimental feed
qualification is not managed transport selection.

[`evidence/`](evidence/) retains exact dated receipts and failures unchanged.
Source, installed, native, desktop, recovery and physical proofs keep their
original package and endpoint scope. Old forwarding paths preserve receipt and
consumer links; new guidance belongs in the maintained guides above.
