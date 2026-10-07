# Tmux Observer development instructions

## Scope and starting point

- The current user request sets authorized scope. The implementation goal covers
  Deliveries A–E in `docs/implementation-backlog.md`, with reviewed commits as
  work progresses. Runtime/deployment acceptance must pass its evidence gates.
- Read `README.md`, `docs/architecture.md`, `docs/observation-contract.md`,
  `docs/service-and-networking.md`, `docs/implementation-plan.md` and
  `docs/design-review.md` before implementation.
- Follow the applicable workspace instructions. On this workstation shell
  commands use the RTK wrapper described in `/home/bryan/.codex/RTK.md`.
- Keep work primary-led. Do not start sub-agents unless the user or applicable
  instructions explicitly request delegation.
- Preserve unrelated changes in this repository and all producer, consumer and
  chezmoi checkouts. Agent Observer is a design reference, not an edit target.

## Observation invariants

- Core is host-local and passive. It imports no Rofi, SSH routing, terminal
  launcher or lifecycle client. Explicit direct reads do not start a service.
- Observe only the configured default tmux server in the first delivery.
  Do not auto-create a server/session, attach a control client, install hooks,
  repair configuration or change native options to improve observation.
- Preserve complete identities: host scope, server generation, session ID and
  creation time. Names, titles, paths and PIDs are not replacement identities.
- Keep owner facts, endpoint-local viewer observations, health, activity and
  transport liveness distinct. Cached delivery and heartbeats renew no facts.
- Keep unknown, stale, failed, warming and complete-empty cases explicit.
  Partial collection cannot prove that an omitted session was removed.
- Observation publishes metadata, not prompts, terminal contents, pane output,
  raw process environments, credentials or action handles.
- Reads and subscriptions do not schedule collection. The separate explicit
  refresh operation only hints bounded passive collection for fixed sources.
- Core/service lifetime must not hold a session alive or change attachment
  counts. Native control-mode experiments have an independent later gate.

## Compatibility and execution

- Preserve the existing `rofi-tmux-plus` Tmux Session v1 facade, response
  semantics and lifecycle validation during migration. Cached reads are explicit.
- Accept each producer checkpoint independently before downstream migration.
  A consumer finding reopens the producer checkpoint that owns the defect.
- Direct reads, owner service, fleet service, lifecycle client, frontend and
  deployment have separate acceptance. One does not establish another.
- Source tests and synthetic fixtures do not establish native passivity,
  graphical behavior, sleep/wake, installed bytes or managed service recovery.
- Native probes use owned disposable sessions, isolated preferences/cache and
  services; preserve ordinary sessions, sockets, hooks and other services.
- The implementation plan specifies the future `scripts/check` gate. Until
  that exists, document-only verification checks links, examples, whitespace,
  decision consistency and source attribution; do not claim runtime tests here.
- Do not publish or promote an artifact merely because a design gate passes.
  User authorization and the concrete task determine when to commit/deploy.
