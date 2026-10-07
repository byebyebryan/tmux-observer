# Observation contract design

Date: 2026-10-07. Status: semantic specification for G0 schemas and independent
reader fixtures. These are proposed contracts, separate from released Tmux
Session v1. No field or command here is implemented or accepted.

## Contract layers

| Layer | Proposed version | Content |
| --- | --- | --- |
| Owner observation | Observation 1 | One configured host/user/default-server source and its bounded native facts |
| Service envelope | Service 1 | Publisher identity, source receipts, stream ordering and delivery state |
| Fleet view | Fleet 1 | Authoritative host catalog, owner projections, desktop observations and transport health |
| Compatibility facade | Existing Tmux Session v1 | Unchanged public inventory/lifecycle envelopes and semantics |

Version these layers independently. Publish strict schemas, API descriptors,
semantic validators and raw-invalid fixtures before implementing native sources.
Consumers validate framing, schema and semantics; schema shape alone cannot
establish freshness, provenance, identity or complete coverage.

## Identity and scope

Keep the existing session reference:

```json
{
  "hostId": "starship",
  "serverGeneration": "tmux-v1:1722741000:1234:/run/user/1000/tmux-1000/default",
  "sessionId": "$6",
  "createdAt": 1722741001
}
```

This is an illustrative reference, not a live target. The four fields form one
identity. Session IDs are not globally unique; creation time guards reuse within
a server, and server generation guards replacement. Rename retains identity.
Names, titles, cwd, current window and native PID are descriptive evidence only.
Treat generation as an opaque bounded token; do not strip its spaces or parse
its socket path to select a different native server.

The owning source also fixes logical host, local UID and default-server scope at
startup. Native hostname is diagnostic metadata, not logical host attestation.
Host Mesh supplies the consumer's expected host/route association. A subscriber
cannot assign a different host label to the source. Remote UIDs need not equal
the reader's local UID; their meaning is source-scoped.

A publisher incarnation is a fresh UUID per service start, separate from tmux
server generation. Also identify kernel boot and time namespace for local clock
comparison. Reusing a native server after a publisher restart does not preserve
the publisher's leases, transport sequence or refresh tickets.

## Owner facts

Default service observation retains bounded session metadata already needed by
Tmux Plus: full reference, name, activity and last-attached clocks, attached-client
count, pending-registration flag, window count, session/current path and current
window. Preserve nullable unavailable native values rather than inventing zero.

Plain service snapshots collect no pane contents, prompts, environment, raw
process argv or arbitrary user-option values. The existing pending marker is
read as a boolean. Optional pane metadata and explicit requested options needed
by the legacy direct API remain separately bounded direct-read capabilities;
they do not expand the publisher's configured feed or persistent cache.

Native activity, creation, last-attached, sample-start, accepted-read, attempted-read
and publication times have different meanings. Wall-clock native timestamps
remain Unix seconds; diagnostic collection/publication wall times are Unix
milliseconds. Both use nonnegative signed-64-bit bounds. Local lease arithmetic
uses BOOTTIME milliseconds and never orders unrelated hosts by their wall clocks.

## Coverage and health

| Situation | Observation meaning | Retained display |
| --- | --- | --- |
| No sample accepted yet | Warming; no authoritative snapshot | Null snapshot, not an empty roster |
| Complete accepted roster | Known membership over the bounded sampling interval | Current facts within their receipt |
| No default server, independently established | Complete empty owner source, null server generation | No sessions; old references are absent |
| Binary unavailable | Unsupported/unavailable observation, not complete emptiness | Last-known metadata, if any, marked uncertain |
| Partial parsing or interrupted inventory | Incomplete coverage; omission proves no removal | Last-known metadata with uncertain facts |
| Source read failed | New current claims invalidated immediately | Original last-known values and ages |
| Receipt expired | Facts no longer confirmed current | Names/paths can remain historical; attachments are unknown |
| Owner publisher unreachable | Transport/source unavailable | Per-host retained data; healthy peers remain usable |

First delivery treats a failed/partial default-server batch as a failed current
owner receipt; it does not splice apparently healthy new rows into a complete
roster. This is simpler than per-session partial leases and prevents false
negative membership. The contract still distinguishes partial from failed for
diagnostics and future capability extension.

An accepted empty roster requires a bounded native absence result or complete
successful list, not a timeout, missing CLI, disconnected stream or missing
cache. A changed server generation invalidates every old reference, even when
a new server reuses session IDs and names.

Collection is not an atomic transaction across all tmux commands. Bracket native
reads with server-incarnation checks and check full per-session identity across
required descriptor/option reads. Changed incarnation, identity reuse or a row
disappearing during those reads invalidates the batch; retry a read at
most once within its original deadline. Do not start tmux to stabilize a read.
The supported default-server implementation must prove these cases in G1.

## Source receipts and freshness

Each source receipt records:

- Source identity and monotonically increasing attempted/accepted sample counters.
- Sample-start, acceptance and expiry BOOTTIME values in the publisher's clock domain.
- Last attempt result, current coverage/health and whether collection is in flight.
- Sample age and remaining validity recomputed when an envelope is encoded.
- Original native observation/metadata clocks and source incarnation.

A lease begins at sample start, not acceptance or delivery. Collection duration
consumes validity. A new successful native read can renew the receipt even if
the values are unchanged. Cached delivery, subscription creation, heartbeat,
route health, desktop scan or successful UI render cannot renew an owner receipt.

On source failure, invalidate its current confirmation immediately rather than
waiting for its old lease to expire. Preserve historical descriptors separately
from current attachment facts. Core and clients project this distinction using
explicit health/coverage, not a fabricated `attachedClients: 0`.

Local expiry uses BOOTTIME so suspend consumes validity. Compare BOOTTIME values
only when publisher and reader boot/time namespace match. Persisted descriptors
start stale after a publisher restart. A service returning a cache is not evidence
that collection or native tmux is healthy.

Remote clocks cannot be compared directly. The fleet reader conservatively
translates a remaining source lease into its own clock domain using a matching
bounded request/probe round trip; the algorithm and unverified-stream handling
are specified in [service and networking](service-and-networking.md#remote-age-proof).

## Endpoint-local viewer observations

Desktop observations are optional Fleet 1 extensions. The owner source has no
desktop dependency and never claims where another host's terminal is visible.
The fleet reader's desktop adapter returns the existing display-only states:

| State | Required meaning |
| --- | --- |
| `open`, `confirmed` | Existing exact-reference/attachment metadata or current local client association plus live desktop evidence |
| `open`, `matched` | Existing unique qualified legacy title/owner match with live process/attachment evidence |
| `none` | A complete supported scan found no qualifying local viewer for the current reference |
| `unknown` | Missing, expired, unsupported, incomplete, ambiguous or conflicting evidence |

Retain current reason codes and bounds during extraction. No observation contains
a verified close handle or grants focus/close authority. That remains the write
client's independent inspection. In particular, global attached counts and a
matching title alone cannot prove an endpoint-local viewer.

Desktop context binds UID, captured compositor environment/socket identity and
observer context incarnation. Same-user desktops do not share a positive viewer
lease. Missing compositor/terminal support affects desktop facts only; owner
inventory remains available.

An observation also binds the relevant owner input signature: full reference,
name, attachment count, pending flag, chosen route, native hostname and owner
health. Changed inputs invalidate the affected join and schedule one coalesced
desktop scan. An unchanged owner sample receipt alone need not rescan the desktop.

The initial desktop freshness ceiling remains ten seconds. A positive viewer
requires both a current desktop receipt and current matching owner facts. A fresh
desktop scan cannot renew remote attachments. Owner expiry, source failure,
server replacement, route change and context replacement invalidate positive
joins immediately when observed by the reader.

## Fleet view and presentation projection

Fleet 1 includes the current Mesh revision/catalog, reader incarnation/context,
per-owner provenance and translated receipt expiry, transport states, independent
desktop receipt, an optional requested ticket result and projected session rows. Host
catalog order follows Host Mesh declaration order; failure does not reorder it.

Complete owner inventories replace their own source rows. Failed/incomplete
sources preserve last-known rows with uncertainty; they do not erase healthy
peers. Removed hosts are removed from the current catalog and cannot be targets.
Late source results from an old route, Mesh revision, connection or publisher
incarnation cannot enter a new fleet view.

A failed present Host Mesh provider makes catalog authority unavailable. Its
last-known catalog/rows can remain historical, but cannot establish current fleet
route or desktop claims until revalidated. This is separate from a single owner
failure and never selects the executable-absent local-only fallback. Fixed local
owner facts remain available through the independent owner interface.

The UI derives Open/Attached membership from explicit current facts:

- Open: fresh confirmed or qualified viewer evidence for this desktop and owner.
- Attached: fresh positive owner attached-client count, regardless of desktop.
- All/host scopes: retain useful historical rows with their uncertainty visible.

Unknown membership is not a confirmed empty view. Rofi may display the existing
bounded uncertainty notice and direct inspection toward All/Local. Ordering,
attention styling, bookmarks and provider classifications are not owner facts.

## Validation profile

Carry forward existing native/session bounds: 256 sessions per owner, optional
512 panes per owner, clean bounded strings and stable reference syntax. The new
owner document cap is 1 MiB; its service envelope adds at most 16 KiB. Fleet
documents have an aggregate 1 MiB cap plus 16 KiB envelope allowance, so valid
individual owners do not guarantee that a whole fleet fits. Overflow is explicit;
no partial JSON or silently truncated authoritative roster is published.

The first prepared service supports at most 16 catalog owners, independently of
the existing Host Mesh/direct CLI limits. Excess is explicit capacity/no-current
view, not a silently selected subset. The networking design bounds document and
frame storage in addition to subscriber count. Increasing capacities needs its
own native resource acceptance.

Requests are at most 16 KiB. Strict UTF-8, one LF per JSON record, duplicate-key
rejection, finite numbers, bounded depth/nodes and absolute read deadlines apply.
Unsigned-looking booleans are not accepted as integer timestamps/counts. Unknown
fields follow the G0 declared extension policy; unsupported major versions fail
explicitly. Content-free diagnostic codes are bounded, and never carry raw input.

These limits become supported only with G0 machine schemas, semantic fixtures
and independent validators. New contracts do not rewrite the released bundles.
