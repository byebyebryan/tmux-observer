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

After the selected-budget review, clean source `15d3203` reran the same seven
functional cases with the 768 MiB candidate named in its output. The
[reviewed-target fixture evidence](evidence/2026-10-07-installed-capacity-reviewed-t12-partial.json)
records a 307.01 MiB sampled peak and `passed_partial`. This establishes only
the included local-bridge fixture below that candidate ceiling; actual SSH costs
and simultaneous maximum reader/frame load remain unaccepted. The earlier
256 MiB failure is retained unchanged.

## Actual SSH and simultaneous near-cap readers

```sh
uv run --extra dev scripts/accept-installed-capacity --ssh-host starship --output /tmp/tmux-installed-ssh-capacity.json
```

This additional candidate profile places fifteen synthetic owner scopes in a
private installed environment on Starship and the local owner/fleet on Snap.
The production transport opens fifteen actual strict non-PTY SSH links, each
running the plain installed bridge for one distinct scope. Both endpoints use
the same wheel digest. Synthetic facts/catalog remain explicit: this is sixteen
logical scopes on two physical hosts, not sixteen native tmux/Host Mesh sources.
Actual remote clock domains, process layout and transport costs are exercised.

After the existing small-frame checks, thirty-two readers simultaneously receive
complete near-cap frames. Thirty-one then stop reading while the remaining
subscriber issues nonce-bound prepared snapshot requests with a 250 ms deadline,
including the installed decoder and semantic validation. Independent schema
verification runs separately, so it cannot stall that designated healthy reader.
The test requires actual stalled-reader retirement and
checks unchanged queue/retention caps, rather than inferring retirement from
fully buffered small frames. A seventeenth source still fails catalog authority.

Separate 100 ms samplers retain the local fleet/SSH process peak and the remote
associated bridge peak. Their conservative sum counts every attributed bridge;
the remote synthetic owners and fixture supervisors are accounted separately from
the fleet. The selected 768 MiB ceiling is assessed explicitly. Sampling can miss
transient peaks, and this short stress profile is independent of normal ten-minute
CPU acceptance. SSH process costs are included; encrypted wire-byte accounting,
native collection/desktop facts, physical suspend and managed rollout remain
separate evidence.

Shutdown must reap the fleet's owned SSH children, verify attributed remote
bridges have exited, and preserve all synthetic owners until fixture cleanup.
Only root-qualified recorded bridge incarnations and explicitly owned publisher
processes may be signalled. Both private directories are removed after cleanup.

Clean source `ab69e9d` passed all ten included cases in the
[captured SSH profile](evidence/2026-10-07-installed-ssh-capacity-t12-partial.json).
The conservative sum of local fleet/SSH and associated remote bridge sampled
maxima was 501.24 MiB, below the selected 768 MiB ceiling. All thirty-two readers
received complete near-cap frames; the healthy subscriber's ten round trips took
78–186 ms including installed validation, while the other thirty-one were retired.
Reader thirty-three and catalog owner seventeen failed explicitly. The stop case
preserved all synthetic owners and reaped the owned SSH/bridge tree; both private
directories were removed. These results establish the declared logical capacity
and included real transport/process costs, with the synthetic/source and sampling
limits above. They do not establish native facts on sixteen physical hosts.
