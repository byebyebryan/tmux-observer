# Control reply binding review

Source-only compatible fix after the coordinated Mesh a9 rollout. The installed
Observer a4 / Plus a4 tuple and ordinary owner/fleet services are unchanged.

An OwnerControl captures epoch, native scope and selected route at creation.
Its admission requires a matching native publisher, but the previous poll path
checked only the returned frame against the *current* scope. After an epoch or
route change it could forward an old control result; after scope revocation it
misclassified a matching reply as `invalid_refresh`.

Poll now verifies the captured delivery binding before forwarding a reply and
reports the existing `stale_scope` code when that association has changed.
Native frame validation and the original admission deadline remain enforced.
No current facts, expiry, refresh scheduling or action authority are renewed.
The frozen service/Fleet wire and schemas are unchanged.

Three deterministic cases cover changed epoch, revoked scope and changed route.
All fail against installed a4 and pass against the source fix. The existing late
reply regression still reports `deadline`. The standard source gate passes 383
tests; the optional Mesh gate runs separately against installed Mesh a9.

The compatible Mesh a10 candidate is also admitted explicitly by the source
worker, including the library authority path. Its isolated wheel passes the
owned Mesh integration tests against this source. The optional dependency
and deployed tuple continue to select a9; admitting a candidate does not update
the released a4 wheel or downstream pins.

The related Mesh investigation found two failures in 400 installed Mesh-backed
grouped-refresh attempts. A detailed failed reply retained its request and
publisher binding while the coordinator scope was revoked. The reason for that
rare revocation remains unresolved; this fix does not claim to eliminate it.
Redacted traces and exact input/harness digests are in the sibling Mesh record:
`docs/evidence/2026-10-10-operational-hardening/`.

This source change requires a new artifact and exact downstream module pins
before deployment. Do not attribute existing a4 acceptance to the changed bytes.

## Private bridge retirement overlap

Client socket closure can precede publisher-handler retirement. The owned
local bridge admitted only one client, so proactive rotation could reconnect
while that slot was still retiring and incur an unnecessary failed setup.
It now admits at most two handlers: one active Reader and one retiring handler.
The general IPC server limit is unchanged; no publisher or fleet pool is added.

A real-IPC regression delays owned Bridge cleanup by 100 ms and forces three
rotations with a four-handle fixture threshold. It fails on the one-slot source
with three failed setups and passes with the bounded extra slot. Reader metrics
are sampled on their owning event-loop thread. This does not promise admission
under an arbitrarily stalled publisher, and the ordinary production handle
budget remains 4,080. The optional Mesh gate now has seven tests; an additional
two-host production-budget soak records its own exact harness and cleanup proof
in the Mesh operational-hardening evidence.
