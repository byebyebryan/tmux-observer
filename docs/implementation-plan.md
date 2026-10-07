# Implementation and action plan

Date: 2026-10-07. This is the plan for future implementation. The present
checkpoint delivers documentation and design review only.

The [implementation backlog](implementation-backlog.md) turns these gates into
17 concrete tasks and five deliveries. Begin with Delivery A (T01–T05): contracts,
independent reader and accepted standalone local observation.

## Delivery boundaries

Build and accept the producer before migrating its consumers. Each gate ends
with a reviewable change, a versioned candidate and evidence for that gate;
passing a source check does not accept native behavior or deployment.

| Gate | Deliverable | Depends on | Exit evidence |
| --- | --- | --- | --- |
| G0 | Contract bundles, independent reader and pinned extraction manifest | Reviewed design | Raw-wire/semantic fixtures pass; interfaces and limits are explicit |
| G1 | Standalone passive local collector and direct CLI | G0 | Native identity, absence, race, bounds and passivity acceptance |
| G2 | Shared owner publisher, local read client and stdio bridge | G1 | Independent reader, native sharing, expiry, restart and resource proof |
| G3 | Fleet/read service, Host Mesh SSH transport and desktop adapter | G2 | Two-host recovery, conservative age proof, endpoint-local joins and sharing |
| G4 | Rofi read migration and completion feedback | G3 | Legacy compatibility plus native Rofi interaction/latency acceptance |
| G5 | Separate first-party lifecycle client; old CLI becomes a facade | G4 | Independent action/handle validation and old-contract parity |
| G6 | Published artifacts and scoped managed selection | Accepted G3/G4; G5 only if selected | Exact bytes, services, host acceptance and rollback |
| G7 | Optional native event source adapter | G2; separate experiment | No attachment/lifetime/geometry changes and measurable benefit |

G5 is a separate follow-up: G6 may deploy accepted prepared reads with the
existing lifecycle implementation. Do not make the startup improvement wait
for an unrelated action rewrite. G7 does not block polling-backed push delivery.

## Work ownership

This repository owns the pure contract, local observation, publisher, read
client, optional networking/desktop adapters and eventual write-client package.
The Rofi repository owns its released compatibility facade and UI migration.
Chezmoi owns managed artifact pins, entry points, configurations and units.
Agent Observer/Plus are references and consumers, not edit targets in this pass.

The primary owns boundary decisions and acceptance. Any later delegated task
must name owned paths, inputs, exclusions and its verification; no implicit
multi-repository work or overlapping ownership. Preserve other active checkouts.

## Extraction map

Source paths below are relative to the pinned `rofi-tmux-plus 0.6.0` checkout.
Package paths are proposed responsibilities, not whole-file copy instructions.

| Source | Destination/responsibility | Required separation |
| --- | --- | --- |
| `model.py` | `tmux_observer.public`: pure identity and owner metadata | No UI, terminal, network or action imports |
| `tmux_wire.py`, `wire.py` | Strict native/JSON parsing and public validation | Preserve bounds; separate native parsing from new envelope versions |
| `bounded_process.py` | Internal bounded collector process runner | Absolute budgets and owned-child cleanup; no arbitrary public execution API |
| Read methods in `tmux.py` | Local collector | Exclude create/rename/kill/attach; add generation bracketing and identity checks |
| Inventory in `lifecycle.py` | Direct observation adapter | Keep lifecycle and terminal launch outside passive imports |
| `observe_local_viewers` in `viewer_service.py` | Optional desktop adapter in fleet client | Exclude focus, close handles, close and action dispatch |
| Host Mesh and `RemoteInventory` logic | Optional `tmux_observer_client.network` | Reuse route/policy validation; add explicit subscription/proof, no recursive fleet export |
| Composition in `inventory_service.py` | Direct fleet reader and shared fleet service | Owner publisher remains host-only; preserve explicit fresh legacy inventory |
| Collection/cache portions of `picker_model.py` | Service schedulers, source receipts, fleet cache | Replace finite jobs with shared lifetime; keep UI intent and presentation private |
| `rofi.py`, `presentation_cache.py`, `view_preferences.py` | Remain Rofi-owned | Preserve exact selection, filter, bookmarks and pending targets |
| `config.py` | Split fixed owner, fleet/desktop and UI/write settings | Subscribers cannot set paths, cadence or executable options |

Do not copy the writable `TmuxClient`, `LocalLifecycle` or whole viewer module
into the passive core. Narrow read interfaces are the acceptance boundary.
Record source license, headers and extraction provenance before copying code;
choose the new repository license consistently with the inherited material.

## G0 — freeze executable boundaries and fixtures

1. Pin the Tmux Plus source commit and both canonical contract-bundle digests.
   Record the Agent Observer design reference separately; its moving development
   checkout is not an extraction dependency or accepted runtime baseline.
2. Create `contracts/observation-v1/`, `contracts/service-v1/` and
   `contracts/fleet-v1/`: strict schemas, API descriptors, semantics and fixtures.
   Freeze names/types, nullability, error/result codes, clock domains, extension
   policy, identity syntax, capabilities and frame/queue limits.
3. Define the direct API separately from service access. Optional legacy pane
   metadata/options remain explicit direct-read capabilities. Define fixed
   owner scope, desktop context, expected route association and nonce semantics.
4. Implement a pure public validator and an independent minimal read client.
   Test raw invalid UTF-8, duplicate keys, booleans as integers, depth/node limits,
   incompatible versions, stale receipts, scope conflicts and replayed proofs.
   Generate fixtures separately from production serializers where practical.
5. Add Python 3.11+ packaging, license/provenance and `scripts/check`. Pure imports
   require no native tmux, desktop, Rofi, SSH Plus or Agent Observer installation.

Exit: fixtures establish a coherent interface that a producer can implement and
a separate consumer can reject correctly. No service/native acceptance claim.

## G1 — standalone local producer

Implement explicit fresh collection and the diagnostic CLI with bounded process
execution. Preserve fast-path escaping, legacy fallback and metadata bounds.
The collector can receive a validated fixed scope; it cannot start a server or
receive arbitrary command/socket selection through its public interface.

Bracket the batch with generation checks. Guard per-session identity across
descriptor/option reads; validate the complete reference rather than an ID alone.
Treat interrupted or ambiguous coverage as failed/partial, retain no fabricated
complete roster, and allow at most one read retry within the original deadline.
The audit includes both fast and legacy paths, not only the optimized path.

Compare results with independently issued native tmux queries in disposable
scopes. Prove no-server behavior, server replacement, session reuse, rename,
pending registration, malformed metadata and no change to client counts/native
options/lifetime. Tests may inject an owned test-server runner; shipped source
configuration supports only the default server.

Exit: accepted direct producer, independently usable without any service or UI.

## G2 — shared host-local publisher

Add fixed-source configuration, private endpoint ownership, BOOTTIME scheduling,
attempt/accept receipts, stale historical storage and status/snapshot/watch/probe.
Implement bounded fan-out and explicit refresh tickets as specified in the
[network design](service-and-networking.md). Add the remote stdio bridge now,
but accept local behavior before testing it over SSH.

Use an independent reader to verify frame ordering, incarnation changes, queue
pressure and expiry. With 1, 8 and 32 readers, native collection rate remains
source-owned. Prove initial warming, collector failure, delayed readers, restart,
duplicate publisher rejection and bounded child cleanup. A service stop leaves
native tmux and unrelated processes alone.

Exit: accepted owner candidate and read-client candidate with native lifetime
and resource evidence. Remote networking and Rofi remain unaccepted.

## G3 — fleet, SSH and endpoint-local observation

1. Implement explicit direct fleet composition using accepted local producer
   reads and existing Host Mesh policy. Preserve the missing-executable-only
   local fallback and verified reached-host route reporting.
2. Implement the shared fleet service: one owner subscription per selected
   host, local owner IPC, independent source epochs, catalog order and bounded
   recovery. Mesh reload and route reporting run outside foreground reads.
   Failed catalog rechecks have explicit authority health; no silent fallback or
   current-route publication from a merely retained catalog.
3. Add strict non-PTY SSH stdio framing and matching-nonce remote age proof.
   Verify on Snap ↔ Starship with delay, buffered frames, disconnects, old scope,
   route removal, suspend and publisher restart. Measure persistent SSH versus
   one-shot calls before adding a task-owned connection-sharing optimization.
4. Extract display-only desktop observation. Preserve confirmed/matched rules,
   reason codes and independent expiry. No write handles enter the fleet view.
   Test local desktop versus headless contexts and changed owner/route inputs.
5. Exercise capacity separately from the normal two-host profile. Publish
   supported limits and fail explicitly when a valid fleet exceeds its aggregate
   bound; do not truncate it into an authoritative complete roster.

Exit: a CLI/independent subscriber can consume prepared fleet views while Rofi
is absent. Installed candidate services on both hosts must pass recovery and
native acceptance before the UI depends on them.

## G4 — Rofi becomes an observation client

Begin only with accepted producer/read artifacts. Replace picker collection
with an explicitly selected cached fleet reader. Keep presentation snapshots,
saved scope/reference, filter, ordering, confirmation and action authority in
the UI. Adopt new prepared data on callbacks without retargeting pending actions.

Use a supported in-process read/validation facade for Rofi callbacks where viable;
do not add a new Python/CLI launch for every prepared query without measuring
that cost. Public read imports exclude native collectors/network loops/actions,
and the consumer pins the accepted API/artifact rather than importing private
producer modules. The independent CLI remains an acceptance/diagnostic client.

Legacy `rofi-tmux-plus inventory` delegates to the explicit **direct** collector
and fresh fleet reader, preserving argv, JSON, bounds, host policy, exit codes
and `--with-viewers` semantics. Service envelopes never leak into Tmux Session
v1. Existing lifecycle behavior continues to revalidate native state directly.
Project direct errors using v1 semantics: non-`ok` host rows have no sessions.
Do not leak the prepared service's retained historical rows into fresh inventory.

Prototype native Rofi input-change/custom-callback delivery before promising
updates during continuous typing. Use the early T06 fixture-backed prototype to
expose interaction risks before the networking delivery; final migration still
depends on accepted producers. Verify initial selected-row preparation,
`keep-selection`/`keep-filter`, caret, view arrows and restore behavior against
the installed Rofi version. If it cannot meet the interaction gate, retain the
prepared-startup improvement, document the remaining live-update limitation and
keep that gate open; do not simulate an accepted stream frontend in tests.

Background renewal is quiet. Alt+R observes its own ticket, clears on a terminal
outcome and names failed/stale sources. Cached service absence/warming has a
bounded visible state and never silently invokes direct collection. Measure CLI
startup, parsing, model adoption, frame creation and actual graphical appearance
separately so a fast daemon query cannot hide frontend overhead.

Exit: compatibility fixtures/checks pass, Snap native GUI acceptance passes, and
Starship graphical acceptance is recorded separately. Source/callback tests alone
cannot close the graphical gate.

## G5 — independent lifecycle client

After read migration, separately move generic action implementation into a
first-party write client. Keep terminal choice, focus, confirmation and UI policy
at appropriate client boundaries. Expose no action RPC on observation services.

Preserve complete-reference revalidation, attachment metadata, verified close
handles, PID identity and session-survival checks. Never infer close authority
from Open/Attached or retry an ambiguous write. The old CLI remains the canonical
Tmux Session v1 facade until a separately reviewed contract migration.

Exit: independent native write-client acceptance and old-contract parity. Agent
Plus can continue using the old executable throughout this checkpoint.

## G6 — publish, manage and roll back

Prepare a reviewable rollout only after accepted candidates exist. Publish exact
versioned bundles first; pin revision and archive checksum together in chezmoi.
Render templates and inspect a scoped diff for owner/fleet units, host identity,
desktop environment and selected Rofi reader. Preserve unrelated managed drift.

Bring up owner publishers first, fleet readers second, then select the Rofi
candidate. Verify installed bytes/versions, service configuration and recovered
prepared data independently on Snap and Starship. Observe healthy, remote-down,
restart and desktop-context recovery before declaring either endpoint accepted.

Record a rollback selecting the previous Rofi artifact/configuration and stopping
only the new owned fleet/owner units if no other clients require them. Restore
only changed managed paths; preserve native sessions, bookmarks/preferences,
unrelated services and pre-existing SSH masters. Verify rollback explicitly.

Exit: exact published/managed/installed evidence plus each host's applicable
runtime and graphical acceptance. Commit, push and deployment follow the user’s
authorization for that implementation pass; this document pass performs none.

## G7 — optional native events

Run an isolated prototype after polling-backed service acceptance. Compare event
lag, command/byte counts and CPU with the sampled baseline. Control-mode clients,
hooks and tmux configuration writes are excluded from the accepted passive source
unless a separate review/native experiment proves the required invariants.

If the adapter changes attachments, last-attached behavior, session destruction
or geometry, reject it for passive observation. Polling remains a supported source;
native events are an optimization, not a reason to weaken truthfulness.
