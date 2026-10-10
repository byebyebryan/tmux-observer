# Tmux Observer documentation

Start with the [project overview](../README.md) and [current runtime architecture](runtime-architecture.md).
The recorded current selection is Observer **0.6.0a2**, Tmux Plus **0.12.0a2**
and Mesh **0.1.0a7** on Snap and Starship, as of 2026-10-10.

## Current interfaces and operation

| Read | Purpose |
| --- | --- |
| [Runtime architecture](runtime-architecture.md) | Core, owner, Mesh, desktop, actions and UI responsibilities |
| [Wire v1](wire-v1.md) | Implemented Observation, Service and Fleet contracts |
| [Boundary wire v1](boundary-wire-v1.md) | Native attachments, desktop association, bindings and action contracts |
| [Service contexts](service-contexts.md) | Explicit startup, captured desktop environment and context teardown |
| [Mesh integration](mesh-integration.md) | Source configuration, state delivery, separate refresh control and rollout history |
| [Candidate artifacts](candidate-artifacts.md) | Frozen committed-source builds and package verification |
| [Managed operations](https://github.com/byebyebryan/dotfiles/blob/main/docs/tmux-observer-operations.md) | Exact installed tuple, managed controls and rollback |

## Selection and acceptance

[Current accepted catalog fix](evidence/2026-10-10-catalog-bound-fix/README.md)
is the front door for the selected artifact's native, headless, resource/capacity
and installed recovery/rollback evidence. [Implementation status](implementation-status.md)
keeps the original A–E checkpoint history. Acceptance belongs to the exact
artifact, endpoint and scope recorded by each report.

| Historical record | Scope |
| --- | --- |
| [Previous Mesh rollout](evidence/2026-10-10-mesh-rollout/README.md) | SDK a6 / Observer 0.6.0a1 / Plus 0.12.0a1 |
| [Original Mesh candidate](evidence/2026-10-09-mesh-integration/README.md) | Earlier candidate inputs, diagnostics and limitations |
| [CPU performance](cpu-performance-design.md) | Observer 0.5.0a1 delivery |
| [Fleet performance](fleet-performance-design.md) | Observer 0.4.0a1 delivery |
| [Local performance](tmux-observer-0.3.0a1.md) | Attachment-driven associations |
| [Boundary extraction](tmux-observer-0.2.0a1.md) / [implementation ledger](boundary-implementation.md) | Independent native, desktop, action and consumer gates |
| [Always-on acceptance](always-on-acceptance.md) | Awake-host acceptance and simulated recovery scope |

Native [direct](native-direct-acceptance.md), [fleet](native-fleet-acceptance.md),
[desktop](native-desktop-acceptance.md), [remote desktop](native-remote-desktop-acceptance.md),
[capacity](installed-capacity-acceptance.md) and [suspend](native-suspend-acceptance.md)
guides explain their separate proof boundaries. Preparation or a source test
does not establish installed, graphical or physical acceptance.

## Design and implementation history

The [original architecture](architecture.md), [observation semantics](observation-contract.md),
[service/networking design](service-and-networking.md), [implementation plan](implementation-plan.md),
[backlog](implementation-backlog.md), [design review](design-review.md) and
[validation plan](validation-plan.md) retain the first-delivery baseline.
Planning command names and future tense in these documents belong to that baseline.

The [component boundary design](component-boundaries.md) and
[source review](component-boundaries-review.md) record the subsequent extraction.
[Local performance implementation](local-performance-implementation.md) records
later association work. [Context and primary sources](context-and-sources.md)
preserve the checked design inputs.

Current behavior is summarized in runtime architecture and implemented wire guides.
Historical records retain their original failures, hashes and acceptance limits.
