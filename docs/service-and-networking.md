# Service and networking design

Date: 2026-10-07. Status: historical first-delivery Service 1 / Fleet 1 design.
The command table below retains original planning names; use the
[README](../README.md) and [wire v1](wire-v1.md) for implemented commands/contracts,
and [implementation status](implementation-status.md) for acceptance. The
[component boundaries](component-boundaries.md) refine the next networking,
composition and desktop separation. [Validation](validation-plan.md) owns proof gates.

## Access modes and proposed commands

The names below are the original implementation targets, not today's command recipe.

| Interface | Proposed command | Behavior |
| --- | --- | --- |
| Fresh local diagnosis | `tmux-observer snapshot --host-scope HOST --json` | One bounded direct owner collection; starts no service |
| Cached owner query | `tmux-observer service snapshot --host-scope HOST --json` | Reads the selected owner publisher; starts no collection |
| Owner subscription/bridge | `tmux-observer service watch --host-scope HOST --stdio` | Bridges Service 1 local read/probe/refresh messages to stdin/stdout |
| Owner publisher | `tmux-observer-service serve --config PATH` | Fixed owning-host source and local endpoint |
| Prepared fleet query | `tmux-observer-client snapshot --access cached --json` | Reads the fleet service; no direct fallback |
| Explicit fresh fleet diagnosis | `tmux-observer-client snapshot --access direct --json` | Bounded one-shot composition using explicit direct owner reads |
| Fleet subscription | `tmux-observer-client watch --json` | Reads replacement Fleet 1 views and health |
| User refresh | `tmux-observer-client refresh --sources owner,desktop --json` | Returns a bounded coalesced refresh ticket |
| Refresh outcome | `tmux-observer-client refresh-status --ticket ID --json` | Reads retained ticket state; schedules no work |
| Fleet service | `tmux-observer-client-service serve --config PATH` | Shared network subscriptions and desktop observations |

The default Rofi integration uses explicit cached service access. A missing,
incompatible or warming service is a visible state, never a reason to invoke
direct collection implicitly. Operators can choose the direct diagnostic CLI.
Legacy `rofi-tmux-plus inventory` retains its existing explicit fresh semantics.

## Endpoints and fixed scope

Owner endpoint: `$XDG_RUNTIME_DIR/tmux-observer/owner.sock`.
Fleet endpoint: a context-specific path under
`$XDG_RUNTIME_DIR/tmux-observer-client/`; one configured desktop context owns it.
The implementation derives a bounded safe context key instead of putting raw
display names or socket paths in filenames. The launcher chooses that context
explicitly; it does not use the first socket found for the user.

Use private owned parent directories (0700), sockets/locks (0600) and same-user
peer checks for local access. Refuse unsafe paths and duplicate publishers.
Never unlink a live publisher's socket simply because startup sees a pathname.
Only clean up an endpoint demonstrated to belong to the exiting incarnation.

Owner configuration fixes logical host, default server executable, cadence and
metadata profile at startup. The core imports no Host Mesh. Fleet configuration
uses Host Mesh and captures its desktop environment/context; it cannot relabel
remote publisher output. Restart explicitly when source configuration changes.
Subscribing clients cannot choose source paths, arbitrary argv or scan intervals.

## Shared collection and initial budgets

One owner job is in flight per publisher. One desktop job is in flight per fleet
context; input changes coalesce behind it. One remote recovery attempt is in
flight per host. Late completions carry their operation epochs and are rejected
after scope, route, context or incarnation replacement.

These starting settings are tuning candidates, not accepted performance claims:

| Item | Candidate setting / limit |
| --- | --- |
| Local owner sampling | Every 2 seconds, absolute collection deadline 2 seconds |
| Owner lease | 10 seconds from sample start; failure invalidates immediately |
| Desktop sampling | Every 3 seconds while sources exist; absolute 2-second scan budget; ten-second expiry |
| Changed owner inputs | Coalesced desktop renewal, minimum one-second start spacing |
| Mesh configuration recheck | Every 15 seconds and on typed stale-Mesh rejection |
| Watch heartbeat | Every 3 seconds; no source lease renewal |
| Remote freshness probe | Every 3 seconds and on a materially changed view |
| Connected probe deadline | Absolute 2 seconds from request send through full validation |
| Started frame deadline | Absolute 2 seconds from first byte through full validation |
| Watch transport silence | Ten seconds without a valid frame; separate from source expiry |
| SSH setup per host | Absolute 15-second cap, also bounded by selected SSH policy |
| Background remote setup concurrency | Four; established streams remain independently serviced |
| Cached foreground query | Absolute 250 ms deadline; target p95 50 ms including validation |
| Subscribers | 32 per service; bounded admission failure beyond capacity |
| Refresh request tickets | At most 64 retained, ten-minute retention, fixed scopes |
| Pending native jobs | One per configured source; refresh requests coalesce |
| Native collection minimum spacing | One second, including explicit refresh hints |
| Prepared-service host capacity | 16 catalog owners initially; excess is an explicit capacity state |
| Outgoing data per subscriber | At most one started frame plus one queued full replacement; 64 KiB control metadata |
| Outgoing application buffers per service | Hard 72 MiB total; refuse/disconnect slow readers before exceeding it |
| Inbound remote frame storage | Hard 16 MiB aggregate; reserve space before accepting a full record |
| Retained owner documents | Hard 16 MiB aggregate; bounded last-known storage, no history accumulation |

Schedule from actual elapsed BOOTTIME, skip missed cadence slots after suspend,
and never replay a burst of missed jobs. Lease length is distinct from refresh
cadence and transport deadlines. Slow collectors consume their source lease;
clients cannot convert a long-running job into current data. Increase cadence
only with source-lag and resource measurements, not to hide stale status.

Operation deadlines also use BOOTTIME. Adapt the existing runner's monotonic
timeouts rather than relying on them alone: after suspend, reject late work and
advance affected epochs before accepting a result. A platform without the
required clock domain fails explicitly; it cannot silently use a clock that
stops counting suspend.

These are new prepared-service capacities, not changes to the released direct
CLI or Host Mesh parser limits. A larger valid catalog or aggregate returns an
explicit capacity/no-current-view state; do not silently choose the first hosts.
Historical data can remain explicitly stale for diagnosis. Raising capacity is
a separately measured configuration/package change. Count owned SSH children
and frame buffers in capacity tests, not only the Python publisher's RSS.

## Service protocol

Use newline-framed strict JSON on a private Unix stream. Each initial request
declares Service 1, an operation, expected host/source scope and request ID.
Operations are cached `status`, cached `snapshot`, `watch`, `probe` on a watch,
cached `refresh_status`, and a separately explicit `refresh` hint. A one-shot
request receives a bounded terminal reply. A watch has bounded bidirectional
control messages and ordered
service frames; this is not the existing public Tmux Session JSON stream.

Every frame binds protocol, publisher UUID, boot/time namespace, source identity,
per-connection sequence and shared view revision. Frame kinds are initial status,
view, heartbeat, gap, resync, error and refresh result. A probe reply is a status
frame carrying the matching request nonce and current snapshot/receipts.
Initial watch setup carries a nonce and obtains a full scoped status/resync.

Per-connection sequence starts anew on reconnect; publisher view revision is
monotonic within its incarnation. Accepted sample counters are independent of
view revision. A pure heartbeat carries no new sample. Reconnect requires a new
reader guard and full scoped view before positive facts can be exposed.

Accepted samples publish a receipt-bearing status/view update even when owner
values and view revision are unchanged. Local subscribers can renew only from
that actual accepted-sample receipt. Do not disguise that update as a pure
heartbeat; remote renewal still needs matching proof.

If a reader falls behind, replace queued unsolicited views with one explicit gap
and the latest full resync. Bytes of an already started record cannot be replaced.
Count both that frame and the one queued full replacement, plus at most 64 KiB of
control metadata per subscriber, against the 72 MiB service-wide outgoing cap.
Prefer shared immutable payload buffers; accounting cannot depend on that
optimization. A required initial/probe response is protected from replacement;
discard/coalesce unsolicited updates behind it. Admit at most one outstanding
probe per connection and disconnect within the deadline if protected control
delivery cannot progress. Never silently discard a nonce reply or ticket result.

One blocked subscriber cannot stall collection or other readers. G0 freezes
frame/control priority and admission errors; G2 verifies the budgets at capacity.
Bound inbound remote-frame storage separately to 16 MiB, with reservations before
reading maximum-sized records. Overflow is a typed capacity error, not a truncated
snapshot. There is no durable replay or lossless native event promise.

A ready socket with no sample returns warming/null snapshot. A ready service
with failed sources remains operational but has unavailable data. Subscriber
admission and source/data health are separate. Protocol errors fail the specific
connection without changing native tmux or corrupting the shared view.

## Explicit refresh tickets

Refresh is passive collection control, not a native action. This is a deliberate
difference from Agent Observer's initial read-only subscriber protocol: Tmux
Plus already exposes Alt+R and needs an honest completion boundary.

The caller requests only fixed configured source types and an expected current
scope/revision. The service assigns a ticket bound to its incarnation and those
sources. Multiple requests can join one native collection job. Subscriber count
or repeated keypresses cannot bypass the minimum collection spacing.

A ticket progresses through accepted/coalesced, running and a terminal complete,
failed, stale-scope or deadline outcome. Its result becomes terminal only after
the requested owner reads have either published or failed and the requested
desktop join has been reconciled against their resulting accepted inputs, or
its deadline/scope ends. An obsolete scan does not finish a refresh whose owner
inputs changed beneath it. `complete` means every requested source succeeded;
mixed results use `failed` with per-source outcomes, retaining successful data.
A ticket never labels partial success as complete success.

A refresh asks for a sample started at or after ticket acceptance. It may join a
job only if that condition holds; an older in-flight job completes first and one
coalesced successor satisfies the request within the remaining deadline. Preserve
each ticket's requirement when joining jobs. For a remote owner, a newly validated
proof of that requested accepted sample is also required before fleet completion.
Ticket scopes can select only configured hosts/source types; collection and
desktop work remain bounded independently of how many hosts are requested.
For a remote source, create a child refresh request accepted by that owning
publisher and bind its sample/job result to the fleet ticket. Compare job-start
and acceptance clocks only there; the causally later remote request establishes
the fleet's post-request boundary without comparing host clocks.

Requests do not wait on the foreground query path. An explicit refresh deadline
is 15 seconds, with independent per-source deadlines inside it; rejected/rate-limited
requests are terminal responses, not spinner states. Service restart invalidates
old tickets. A completed lifecycle action can request affected-owner observation,
but its failure/result cannot authorize redispatch of the action.

Ticket lookup is a cached read and schedules nothing. Bind its ID to the selected
service incarnation; absent/expired/old-incarnation tickets have terminal typed
results. Each retained result is at most 16 KiB and the whole 64-ticket store is
at most 1 MiB. A snapshot may request one ticket's status within its envelope
budget; do not include the entire ticket history in every fleet view. Watches
notify relevant results, and a disconnected reader can look up the retained
result. This keeps callback feedback independent of a transient notification.

## SSH transport

The fleet reader resolves hosts/routes and the SSH executable through Host Mesh.
Preserve noninteractive authentication, strict host-key checking, selected route
ordering and bounded connection policy. Do not add a second host list. A missing
SSH Plus executable permits local-only composition; a present but invalid
provider is an explicit error, following the existing contract.

Each remote connection runs the proposed owner read bridge via SSH, without a
PTY. The bridge accesses that host's configured owner socket and forwards only
the bounded Service 1 messages. It does not auto-start a publisher, select a
tmux socket, accept a shell command from a subscriber or invoke fleet composition.
Use argv construction and tested POSIX quoting only at SSH's remote command
boundary; do not interpolate host labels, titles or metadata into shell commands.

```mermaid
sequenceDiagram
    participant C as Snap fleet reader
    participant S as Starship SSH bridge
    participant O as Starship owner publisher
    C->>S: SSH route; start bounded stdio bridge
    S->>O: Subscribe with expected scope and nonce
    O-->>S: Full view and remaining source lease
    S-->>C: Matching initial response on same SSH channel
    O-->>C: Subsequent views via bridge
    C->>O: Probe nonce via same channel
    O-->>C: Scoped full status and matching nonce
```

The reader initiates the connection; updates return through it. There is no
network listener beyond existing SSH and no reverse connection to the desktop.
Owner services themselves remain host-local. Local IPC access and remote SSH
authentication are different scopes; source self-reported hostname is not enough
to attest the selected host. Validate fixed logical scope, expected SSH binding,
publisher incarnation and complete references before fleet publication.

A persistent watch avoids repeated transport setup. For explicit direct reads,
measure opportunistic SSH connection sharing using a private task-owned control
path and bounded persistence. Do not change global SSH configuration or commandeer
another application's master. Cleanup closes only owned children/masters, not all
SSH processes or interactive user sessions. See the
[OpenSSH reference](context-and-sources.md#primary-references).

## Remote age proof

Remote BOOTTIME and wall clocks are not comparable to local clocks. A frame's
arrival cannot establish when it was encoded: it may have waited in a pipe or
network buffer. Therefore unsolicited stream frames alone cannot extend a
remote lease or establish fresh positive attachment/viewer facts.

For an initial request or subsequent probe:

1. Record local BOOTTIME `t0`, choose an unpredictable bounded nonce and send it.
2. The publisher encodes a new full reply with that nonce and a source lease's
   remaining validity `r` at reply construction. Bridges forward it unmodified.
3. Receive and validate the full reply at local BOOTTIME `t1` within the absolute
   deadline. Match nonce, connection, scope, incarnation and stream sequence.
4. Translate conservatively:

```text
remaining_local = max(0, r - (t1 - t0) - safety_margin)
local_expiry = t1 + remaining_local
```

Use a 100 ms starting safety margin and measure it; neither the margin nor RTT
can be negative. Require `0 <= r <=` the declared ten-second source lease and
check sample/attempt counters and health with the full response. A response
cannot advertise an arbitrary duration or revive a failed source. The full
elapsed round trip upper-bounds time spent after the
matching request, including source/bridge queueing. An expired result is useful
only as last-known data. A same-source duplicate/replayed response cannot match
a newly outstanding nonce and extend a lease.

Unsolicited materially changed views are held as candidates and trigger one
coalesced probe. Publish the matching probe's full confirmed snapshot, not a
candidate blended into it. Unchanged accepted-source receipt updates await the
scheduled probe to renew remote validity. Local owner delivery needs no network
probe when boot/time namespace matches. The extra proof round trip is a deliberate
cost for conservative freshness, not an inference from unsynchronized clocks.

A validated failure, expired receipt or gap may invalidate a previously positive
projection immediately without a new proof: restricting a claim does not renew
evidence. A later positive still requires matching proof and nonregressing source
counters. Ignore old-incarnation/route frames before either projection.

Separate transport-silence deadlines from source leases. Probe/heartbeat success
does not renew a failed native receipt. A watch sequence gap invalidates current
claims until full resync plus a matching freshness proof. After local suspend,
remote route replacement or publisher restart, discard translated leases and
re-establish scope/proof before exposing positives.

## Recovery, Host Mesh and resource ownership

One selected route per host is active. On transport failure, mark that host's
current facts uncertain, retain last-known descriptors and retry with bounded
exponential backoff/jitter. Starting proposal: 1, 2, 4, 8, 16 and at most 30
seconds between attempts. Service absence/incompatibility is a typed source
error; it does not create a direct-collection fallback loop.

Use existing reached-host evidence for route reporting. A missing owner socket
after successful SSH reachability is not an unreachable-host report. Coalesce
route-health reports on connection outcomes/health renewal, not per subscriber
or every sample; their public semantics remain unchanged. A typed stale-Mesh
result reloads authority and cancels obsolete source associations before retry.

The Mesh recheck bounds detection of removed/changed hosts to its configured
cadence; do not claim instantaneous configuration propagation. Revisions bind
publication epochs. New/removed routes, mismatched scopes and late completions
cannot merge into a newer revision. Healthy hosts continue publishing while a
different host is reconnecting or awaiting a report.

Host Mesh itself has explicit authority health. If a present provider's recheck
fails, retain its last catalog as historical, expose the error and suspend current
fleet route/desktop claims and new route attempts until a valid catalog returns.
Do not reinterpret that as the executable-absent local fallback. Existing streams
may remain connected within their ordinary budgets, but cannot publish current
fleet positives through failed catalog authority. The local owner publisher
remains independently queryable. Reaccepting a catalog requires fresh association
guards/proof; configuration failure cannot be hidden by healthy SSH.
Outstanding fleet refresh tickets end with a typed stale-scope/authority result;
they cannot report current success while catalog authority is unavailable.

Use restartable user services with owned worker/process groups and bounded stop
deadlines. Owner and fleet roles have separate endpoints, units and startup
configuration. Do not use socket activation initially: continuously prepared
views are the purpose, and implicit activation changes cold-start semantics.
Publisher shutdown stops only its observation children. Fleet shutdown closes
only its subscriptions/owned SSH children and leaves owner/native sessions alone.

Desktop environment is captured at fleet-service startup and rebound on explicit
context replacement. Detect missing/replaced compositor sockets; keep owner facts
healthy and desktop facts unknown until a valid context is established. Headless
publisher startup never attempts Niri/Kitty discovery.

Owner units can bind to the user's ordinary service lifetime; fleet units are
desktop-context instances with private captured configuration/environment, not
one global imported display environment for all same-user desktops. Use bounded
restart backoff and a five-second owned-child stop budget. Exact units and
environment handoff are G2/G3 deliverables.

Prepared remote reads require an already running owner publisher. Validate boot,
login/logout and headless user-manager lifetime explicitly on each deployed host.
If that requires lingering or another persistent user-service policy, include
that concrete operational change in rollout review; do not silently enable it or
assume an SSH login keeps the publisher running indefinitely.

Keep diagnostic logs bounded and content-free: counters, result codes, identity
incarnations, durations and resource statistics. Persist no pane output, raw SSH
stderr, process argv/environment or unfiltered wire payload. Optional disk
last-known caches are private, bounded and stale after restart.

## Frontend consequence

A prepared query removes collection from startup, but does not make Rofi a stream
subscriber automatically. Rofi's current timeout is based on inactivity. The
frontend must cheaply adopt current Fleet 1 data during existing callbacks and
independently test idle and input-change delivery. Pending action state stays
bound to its original complete reference and revalidates at execution.

The UI gate must prototype native input-change/custom-callback behavior, preserving
filter/caret/selection and avoiding recursive callbacks. Until accepted, continuous
typing has no asserted live-update bound. Observer/service delivery can ship
independently while that frontend proof remains pending. Background renewal is
quiet; a user-visible refresh refers to its own bounded ticket only.
