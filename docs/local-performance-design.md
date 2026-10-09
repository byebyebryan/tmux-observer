# Local performance: attachment-driven Kitty associations

Status: next-pass design, agreed scope on 2026-10-08. This is not implemented
or deployed by this note. The released B0–B5 behavior and its measured acceptance
remain recorded in [component boundaries](component-boundaries.md) and the
[resource review](resource-design-review.md).
The authorized follow-up has a separate [implementation ledger](local-performance-implementation.md).

## Supported baseline

Start with local tmux clients in ordinary Kitty OS windows. Opening a window
and attaching a client introduces a native client association; closing the
window normally ends that client and removes the association. The session can
remain alive, detached, or attached through other clients.

Use those changes to trigger desktop discovery. Do not continually repeat full
process/window matching to cover uncommon terminal rearrangements. Networking,
remote-window matching and additional terminal/compositor support are separate
work; this local pass establishes neither their behavior nor their savings.

## Collection and matching

Retain periodic passive session and client reads. `list-sessions` supplies
session metadata and attachment counts; `list-clients` supplies individual
client-to-session associations. Compare the actual client mapping rather than
only an aggregate attachment count: a replacement client or session switch can
leave that count unchanged.

Separate two retained mappings:

- A client process incarnation to its discovered local desktop window.
- That client to the complete current tmux session reference.

Bindings remain scoped to the owning host/user, server generation, local boot
and PID namespace, process birth identity and captured desktop context. Numeric
PIDs, titles and session names alone are not binding identities. A client that
switches sessions can reuse its terminal/window binding while the second mapping
changes.

| Native/context change | Adapter work |
| --- | --- |
| First sample or service restart with existing clients | Discover the currently attached clients once |
| New client incarnation | Perform bounded process/window discovery for that client |
| Same clients, same mappings, renewed native receipt | Reuse bindings; no full desktop discovery |
| Existing client switches sessions | Update the session association using the retained window binding |
| Client absent from a complete successful sample | Remove its binding; retain any other client bindings |
| Failed, partial or expired client sample | Make dependent associations unavailable; do not claim complete absence |
| Server generation, boot, PID namespace or desktop context replaced | Invalidate affected bindings and rediscover when valid inputs return |

A newly attached client may appear before its desktop window is ready. Allow
bounded settling retries for unresolved new clients, coalescing related work.
Exhausted or ambiguous discovery remains unknown. Retrying one unresolved client
must not become repeated full discovery for every stable client. An explicit
desktop refresh can request bounded rediscovery through the existing refresh
operation; ordinary snapshot/watch reads still schedule no collection.

The baseline has no periodic full reconciliation scan or new desktop event
subscription. No tmux hooks, attached control client or Kitty configuration
changes are implied. Cheap native polling remains the source of attachment
changes.

## Known limitations

Kitty can [move an existing tab or internal window to another OS
window](https://sw.kovidgoyal.net/kitty/actions/). The same tmux
client can survive that move. Its retained desktop association can therefore
refer to the previous OS window until explicit rediscovery or invalidation.
This is an accepted limitation of the initial local baseline, rather than a
reason to scan every stable binding continuously.

Complex multi-tab/split arrangements or shared terminal processes may not give
the adapter a unique client-to-window match. Publish uncertainty when the
available evidence cannot resolve them. Independent desktop changes that leave
the native client unchanged are not automatically detected by attachment
polling. The supported common case is ordinary Kitty window open/close.

## Evidence and actions

Fresh native attachment evidence proves that the client is still attached. It
does not prove that a previously discovered desktop window is still the current
focus target. Preserve the discovery timestamp and evidence basis of retained
bindings; native lease renewal must not silently renew a desktop observation.

Before implementation, refine C3/C4 to distinguish an attachment-backed retained
association from freshly captured desktop presence. Define its display meaning,
expiry behavior and compatibility projection explicitly. The current `Open`
projection requires fresh owner and desktop evidence, so simply extending its
desktop lease would violate the existing contract. The intended new statement
is “last resolved local window association for a currently attached client,”
with the relocation limitation above. Exact wire encoding and how Tmux Plus
qualifies that state belong to the contract review for this pass.

This distinction changes observation/display semantics, not action authority.
The action client continues to resolve and revalidate current focus/close
targets independently. Cached bindings do not become action handles. Native
`Attached` remains a separate fact and needs no desktop matching.

## Implementation order and acceptance

1. Measure local session/client collection, owner processing and desktop adapter
   work separately. Whole-service CPU is the acceptance result; a cheap
   `list-sessions` microbenchmark alone cannot establish it.
2. Specify the retained-association contract and consumer display projection,
   keeping independent evidence clocks and complete/partial coverage explicit.
3. Add incarnation-scoped bindings and compare client mappings. Remove periodic
   full matching for stable local bindings; bound new-client settling retries.
4. Verify bootstrap, ordinary open/close, multiple clients on one session,
   session switching, PID reuse, server/context replacement, ambiguous matching
   and failed/partial samples. Confirm that unchanged inputs cause no repeated
   full discovery and reads cause no native jobs.
5. Measure idle and changing-window local workloads at the existing native
   polling cadence. Report command starts, matching jobs, CPU, memory and update
   latency, then review the result before considering remote optimization.

No new CPU target is claimed by this note. Passing the existing release ceiling
does not establish that background cost is sufficiently low. Runtime tests and
foreground acceptance remain separate from this documentation change.
