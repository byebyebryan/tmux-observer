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

The related Mesh investigation found two failures in 400 installed Mesh-backed
grouped-refresh attempts. A detailed failed reply retained its request and
publisher binding while the coordinator scope was revoked. The reason for that
rare revocation remains unresolved; this fix does not claim to eliminate it.
Redacted traces and exact input/harness digests are in the sibling Mesh record:
`docs/evidence/2026-10-10-operational-hardening/`.

This source change requires a new artifact and exact downstream module pins
before deployment. Do not attribute existing a4 acceptance to the changed bytes.
