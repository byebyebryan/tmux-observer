# Installed synthetic capacity profile

```sh
uv run --extra dev scripts/accept-installed-capacity --output /tmp/tmux-installed-capacity.json
```

This builds one wheel and installs it in a private environment. Sixteen installed
owner publishers accept explicitly synthetic facts. One installed fleet publisher
uses a synthetic catalog and production remote connection/proof logic. Its owned
transport execs fifteen plain installed stdio bridges locally with SSH-shaped
arguments. There is no SSH process, network, native collector, compositor action
or ordinary service configuration. Headless desktop observation stays unsupported.
The fleet worker includes fixture-tool imports; the bridges use the plain installed
CLI, without importing this tool. These process-layout limits remain explicit.

The independent reader validates complete snapshots. The tool exercises sixteen
current owner subscriptions, thirty-two nonreading watchers, explicit rejection
of reader thirty-three, logical queue/retention high-water marks, a near-cap
complete aggregate, a seventeenth catalog owner and scoped stop. It separately
exercises maximum readers and a near-cap frame; it does not establish their
simultaneous maximum load. Small-frame watcher observations across heartbeats
may fit kernel socket buffers and do not prove the stalled-writer cutoff.

RSS sampling every 100 ms includes the fleet process and its entire owned bridge
tree. Fixture owners/readers/coordinator stay outside that tree. Samples can miss
transient peaks; the short fixture does not replace a ten-minute background CPU
profile. The evidence records the selected target and reports it as failed when
the sampled tree exceeds it, even if every included functional case passes.
`--memory-target-mib 256` reproduces the initial ceiling; the default 768 MiB is
the subsequently selected candidate from the [resource review](resource-design-review.md#selected-direction).
Local bridges omit actual SSH process and encrypted network costs, so this cannot
accept the full native capacity/resource gate.

Shutdown verifies exact owned process incarnations, removes the private fleet
endpoint and preserves fixture owners. Cleanup stops every fixture owner and
owned bridge before the private backing directory is removed. Native two-host
transport, normal resource profiles, desktop truth and physical suspend/wake have
independent acceptance tools/evidence; none follows from this fixture profile.

Clean installed source `ef94ebe` passes all seven included functional cases in
the [recorded profile](evidence/2026-10-07-installed-capacity-t12-partial.json).
The result is `failed_resource_target`: the sampled fleet/bridge peak is
322,592,768 bytes (307.65 MiB), exceeding 256 MiB without actual SSH processes.
The peak contains the fleet and fifteen plain installed bridge processes.
The near-cap complete aggregate contains all sixteen owners in 918,291 bytes.
Recorded process incarnations were absent or exited after cleanup. These facts
motivate a resource/process-design review; they accept neither full capacity nor
revised budgets automatically.
