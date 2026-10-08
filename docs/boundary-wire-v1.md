# Executable component contracts, B0

Frozen for implementation: 2026-10-08. These schemas and pure validators accept
contract inputs; they do not accept a native source, action executor or deployment.
The [design](component-boundaries.md) and [review](component-boundaries-review.md)
remain the authority for scope. [Execution status](boundary-implementation.md)
records subsequent gates.

Existing Observation 1, Service 1, Fleet 1 and Tmux Session v1 files retain their
exact bytes and meanings. New native association, desktop and action contracts
have independent version identifiers. Extraction itself changes no old wire.

## Facades and dependency rules

| Contract | Supported pure facade | Implementations excluded |
| --- | --- | --- |
| C1 native observation | `tmux_observer.native` | Fleet, SSH, desktop, actions |
| C1 optional native associations | `tmux_observer.attachments` | Native execution, processes, IPC, desktop, actions |
| C2 owner delivery | `tmux_observer.delivery` | Fleet models, routing, desktop, actions |
| C3 desktop association | `tmux_observer_client.desktop_contract` | Native collection, compositor/process reads, networking, actions |
| C4 prepared Fleet | `tmux_observer_client.contract` | Collectors, transport loops, scanners, actions |
| C5 explicit action | `tmux_observer_actions.contract` | Executors, desktop actions, routing, Rofi |

Generic framing, scalar bounds, clocks and closed-object helpers sit below these
domains. The legacy `tmux_observer.public` resolves its old delivery/Fleet exports
only when requested. Existing names remain compatible; new consumers use narrow
facades. Generic IPC dispatch loads Fleet validation only for a Fleet request.
The owner imports successfully when client/action packages are unavailable.

The independent reader is `scripts/read-boundary-contract`; it uses schemas and
separate semantic checks, importing no producer package. `scripts/check` checks
new bundle digests, independent valid/invalid fixtures and runtime validators.
Contract updates use `scripts/update-boundary-contracts`, which never writes the
three accepted original bundles.

## Optional local native association profile

`tmux-observer.attachments.v1` contains fixed source, boot/time clock, PID namespace,
native sample, server generation, a complete full-reference session roster and
native client associations. Each client contains its full `sessionRef`, positive
`clientPid` and positive `processStartTicks`. PID scope is the source UID, kernel
boot and PID namespace, plus the sampled process incarnation. No numeric PID is
a cross-host or durable identity.

Limits are 256 sessions, 512 clients and 256 KiB. Duplicate PIDs/session IDs,
unbound references, boolean identities, incomplete authoritative rows and absent
servers with clients are rejected. Failed/partial/unsupported samples carry no
current generation or authoritative roster. A complete no-server sample is empty.
There is no silent truncation or partial-positive splice.

The native read adapter owns tmux reads and narrowly bounded local process
incarnation checks for this optional profile. At B1 it must bracket generation,
full references and client-to-session membership, check UID/start ticks before
and after the bounded read, and reject changed, unreadable or reused identities.
Desktop process evidence must match the accepted sampled UID/start ticks and
recheck process/window incarnation before accepting a join. Failure invalidates
the association source independently of the native session roster.

`tmux-observer.attachments-delivery.v1` wraps that profile with publisher, source,
clock/PID scope, encoding time, independent Service 1 receipt, retained snapshot,
request ID and diagnostic. A ready receipt binds its own sample start/finish,
acceptance and remaining lease. Failed/expired delivery may retain metadata but
cannot provide a current join. Encoding, desktop scans and owner-roster renewal
cannot renew the association receipt.

The selected B1 transport is a second private local endpoint,
`$XDG_RUNTIME_DIR/tmux-observer/attachments.sock`, served by the same owner process.
There is no additional daemon. It accepts only a closed cached `snapshot` request
with protocol/version, `requestId` and `expectedHost`. Requests are at most 16 KiB
and start no collection or service. Replies echo the request ID and must match
expected host, UID, boot/time/PID scope and publisher incarnation.
Admission, scope and absent-endpoint failures use the profile's closed
`operation_error` envelope (`error.schema.json`), with no retained positive data.

Fixed owner configuration enables the profile; readers cannot enable it or
change its source/cadence. Owner refresh hints reconcile configured profiles;
the attachment endpoint has no refresh or action verb. The prepared reader
periodically reads this prepared endpoint independently of UI subscribers.
This avoids putting a large PID roster inside Service 1's 16 KiB control envelope.
Default owner frames, remote stdio bridges and remote mesh subscriptions export
no detailed association profile. Headless owner configuration needs no profile.

Observation 1's `pending` field remains the compatibility projection of the
bounded Plus annotation `@rofi_tmux_plus_pending`. B1 makes the adapter's annotation
profile explicit. The launch/action client owns the annotation meaning and writes;
the read adapter only samples it. No generic native phase, provider status or
registration repair is inferred. This preserves the accepted v1 field while
keeping generic native reads separate from annotation policy.

B1 enables this fixed profile with `owner --local-attachments`; the
`local-attachments --expected-host HOST` command only reads its cached endpoint.
One native worker publishes the roster before sampling the optional profile.
Its accepted opening generation/full-reference bracket is shared, with two
client-membership reads, before/after process incarnation checks and a closing
generation/full-reference bracket. Both fit the original two-second budget.
Association failure or timeout invalidates its own receipt only. An existing
owner refresh ticket still certifies the roster attempt; clients must inspect
the association receipt separately. No subscriber changes collection cadence.

## Desktop association

`tmux-observer.desktop.v1` is a bounded association batch with clock/context/epoch,
encoding time, independent desktop receipt, owner dependencies and per-reference
rows. Dependencies include owner publisher/generation, translated owner expiry,
local-versus-remote scope and optional local association expiry. Rows include the
full reference, copied native attached count and a closed presence record.
There are at most 16 dependencies, 256 rows per owner and 1 MiB total.

Presence has `state`, nullable `confidence`, `evidence` and nullable `reason`:

| Evidence | Presence/confidence | Required claim |
| --- | --- | --- |
| `current_native_association` | `open` / `confirmed` | Current owner/desktop/local-association receipts and verified process incarnation |
| `qualified_title` | `open` / `matched` | Unique compatible live terminal/process plus positive native attachments |
| `launch_reference` | `open` / `matched` | Qualified launch evidence; no claim of current end-to-end binding |
| `absence` | `none` / null | Complete supported scan with current owner inputs |
| `unknown` | `unknown` / null | Explicit missing, expired, unsupported, ambiguous or failed evidence |

Every positive requires current desktop and owner receipts and positive native
attached count. Confirmation additionally requires a current local association
receipt; the contract does not support remote native-binding confirmation.
Failure of a required local association source yields unknown, never absence.
The matcher owns complete-scan coverage, process-race checks and ambiguity.
Validators enforce frame consistency; trusted collection and the coordinator
must additionally verify the supplied input hash, expected context/epoch and
accepted references. A well-shaped document does not attest its own source.

New desktop objects are closed and contain no action handles, window/PID roster,
raw process argv/environments, pane contents or credentials. Niri is an optional
backend; unsupported desktop results preserve useful owner inventory.

## Explicit actions

`tmux-observer.action.v1` has separate request and result schemas. It is an
in-process/explicit CLI client boundary, never an owner/Fleet daemon RPC.

Requests contain request ID, operation, explicit owning host, nullable Mesh
revision, exact reference where required, guards and operation-specific parameters.
Open selects `reuse_unique`, `verified` or explicit `new` viewer policy.
Create has no existing reference and carries name/cwd/options/command/deferred
attachment settings/Open intent. Rename/Kill require expected-name guards.
Viewer inspection/close retain independent verification and close-handle guards.
The caller cannot select a tmux executable, socket, route or collector cadence.
Configured action adapters own those choices.

Requests are closed, at most 16 KiB, with at most 64 option entries and 128 command
arguments. These new serialized API bounds do not rewrite the old facade's
argv bounds. The compatibility write client retains its existing method/validation
semantics; callers of the new API receive explicit validation failures.

Results separately record native effect (`none`/`confirmed`/`uncertain`), terminal
spawn, completed/unverified attachment, focus, viewer close and transport certainty.
Success requires exact target and effect certainty. A successful Create/Rename/Kill
requires confirmed native effect. Open/inspection/close are not native mutation
requests. Failed writes can retain confirmed native effect or explicit uncertainty,
including when a subsequent presentation step fails. Confirmed effects require a
full reference. `automaticRetry` is always false; request IDs supply no idempotency.

`legacyResult` contains the separately validated bounded Tmux Session v1 success
projection. It agrees with target, Mesh revision and spawn/focus/close outcomes;
failure has no compatibility success. Local spawn means `terminalLaunched`, never
proof of completed remote attachment. The v1 facade continues validating its
command-specific result schema and errors/exits independently.

## Compatibility decisions and acceptance corpus

| Interface | Frozen mapping |
| --- | --- |
| Observation/Service/Fleet 1 | Original bundle bytes and field semantics unchanged |
| Legacy remote launch `confirmed` | Preserved only by explicit legacy projection; new C3 reports `matched` |
| New prepared UI | B4 consumes C3 evidence when selected; no silent reinterpretation of Fleet 1 fields |
| Ordinary Open | B3/B4 deliberately rejects duplicate compatible focus candidates; no first-title focus or implicit new viewer after ambiguity |
| Explicit new viewer | Caller deliberately chooses `new`; ambiguity is not authorization |
| Verified Open/close | Existing exact-reference, process/window identity and session-survival guards retained |
| Fresh inventory | Explicit direct reads remain fresh; no cached fallback |
| Uncertain native/launch/close effect | Error/result records uncertainty; no automatic redispatch |

Extraction provenance is the reviewed frontend `41b6737` / runtime `388ee6e`.
Tmux Session v1 manifest digest is
`929aebc003e4af9d0ebe1e2f541c6e45bb03dd996019fbfba425fe5cb454f567`;
Host Mesh v1 manifest digest is
`258e8df0562aea18a20db5378b3335b03332e3df0c0709faf49ccfbffa5c3e10`.
B3/B4 must independently replay their command-specific corpus and document the
duplicate-focus delta before switching any facade. These pins identify the source
contract; they do not claim that an extracted executor already passes it.

The B0 corpus includes complete/absent/failed associations, wrong PID scope,
duplicate client, incomplete authority, local confirmed/remote launch-matched,
expired native joins, headless uncertainty, every action request, spawn without
completed attachment, uncertain Create and forbidden retry/native-effect claims.
Additional adversarial tests cover identity reuse, independent leases, shape and
import isolation. Native, GUI, installed, resource and rollback gates remain open.
