# Managed Mesh a24 full-view update

Accepted on Snap and Starship, 2026-10-20, after Bryan explicitly requested
upgrading the installed runtime while opting out of delta delivery.

| Component | Selected version |
| --- | --- |
| Tmux reader SDK and Tmux-only bridge | Mesh **0.1.0a24**, full-view route |
| Observer | **0.6.0a9**, qualified private wheel |
| Tmux Plus | **0.12.0a8**, qualified private bundle with the exact Observer a9 pin |
| Default shared/Agent routes | Their prior independent selections, unchanged |

[deployment.json](deployment.json) pins exact artifacts and the canonical
chezmoi selection commit. Both hosts passed Observer's managed operations
verification in **desktop** scope: installed bytes/modes, frontend exact module
guard/native artifact, two fresh owners, current desktop/local-binding evidence,
and preservation of pre-existing native references. Both hosts had active desktop
contexts; earlier Snap headless evidence was not reused as desktop acceptance.
Each prepared Fleet frame was 4,600 bytes at verification.

The live client and bridge bootstrap imports independently report Mesh a24 and
Observer a9. Managed launcher bytes match their rendered sources, the running
fleet has no `--view-feed` argument, and the Tmux-only bridge rejects feed/delta
commands. It accepts only `serve`/`bridge` for the fixed `tmux_default` source.
The shared dispatcher routes that source before importing an SDK. Agent's active,
working-set and default routes retain their prior SDKs; their owned control
hashes and service identities survived unchanged on both hosts.

The existing frontend's exact Observer a7 guard correctly rejected the first
a9 attempt. Starship was restored to the previous pair and independently
verified before continuing; Snap had not yet switched. The matching frontend
artifact updates the complete 87-module pin to the qualified a9 wheel, preserving
the version/coverage/hash guard. Its native manifest changes only source-commit
provenance; native binary and presentation/action code are identical to the
previous installed frontend. The full 293-test frontend source gate, constrained
wheel/bundle checks, isolated installed Observer/native checks, and full paired
chezmoi source gate passed. No check was weakened to permit the update.

Disposable full-view mixed-version preflights passed in both directions before
the rollout. Snap and Starship were then updated separately, stopping only their
Tmux desktop/owner services and starting the owner before the captured desktop
context. New publisher identities were required while native server generations
and complete session references remained intact. Final verification used both
updated hosts and fresh full nonce proof; no native tmux or Agent service was
stopped. The [pilot](../2026-10-20-view-feed-pilot/README.md) retains its separate
source/SDK/installed/native/cost scope and its no-benefit adoption decision.

The private Observer wheel and frontend bundle are content-addressed durable
inputs on both hosts under `~/.local/share/tmux-observer/artifacts/`, pinned by
`file://` URL and SHA256 in chezmoi. Mesh's exact a24 wheel is fetched from the
public release. Old SDK roots, paired payload/control captures and the previous
source selection remain available for recovery. No public release or GitHub push
was performed. Raw captures with private controls/native identities remain in
owned private cache directories; the public record retains verification hashes.

Twenty-second cgroup samples recorded fleet CPU of about 0.86% on Starship;
the exact samples for both hosts are in the JSON record. Memory is cgroup
`MemoryCurrent`, not RSS or a hard physical peak. These brief recovery samples
do not establish long-run resource/capacity, physical suspend or new graphical
interaction acceptance. Limits, native cadence, schemas, full reads/proofs and
independent action validation remain unchanged.
