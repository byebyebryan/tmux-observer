# Tmux complete-view feed pilot

The bounded opt-in [a24 integration](../../view-feed-pilot.md) passes its source,
installed-pair and disposable native checks. **Retain the legacy full-view
default**: the ordinary Reader workload shows no consistent overall benefit.
This is a private source candidate on `view-feed-pilot-20261020`, not a release
or managed rollout.

The baseline is Tmux Observer `7e14d799796a96b81f3a35947a7ed3c535701bf2`.
Mesh is the downloaded experimental a24 wheel, SHA256
`9bca5b554babfa59ba56b1a4ac5e8e5c66a85e63709731ee1fe7d4f0ed6a18a6`,
tag `bb0c45399e5b8264c9936ca48457cc9a442431df`.

Reviewed source/candidate commit:
`bb4b0438864e587f3d70cce2576d25c76aa8460a` (Observer **0.6.0a9**).
The exact 259,872-byte wheel has SHA256
`b117cc5d353f323ce25c6629dc3371d5d95aa349639cf09974fda3a62f8d7738`.
[candidate.json](candidate.json) binds all 87 installed runtime modules and the
frozen contract payloads. The original private wheel is under
`.cache/view-feed-pilot/observer-a9/` in the owning worktree. Documentation
closeout may advance the branch; candidate runtime bytes remain exact.

## Gates and coverage

| Gate | Result and actual boundary |
| --- | --- |
| Canonical source/contract/lint | `uv run --extra dev ./scripts/check`: 405 tests each on Python 3.11.17 and 3.14.8, no skips; contracts and Ruff pass |
| Exact installed Tmux pair | `scripts/check-mesh --installed --artifact .../candidate.json`: 47 tests each on both versions, no skips; 87 installed modules match the committed wheel |
| Exact installed Mesh bytes | All 107 runtime/schema files match the downloaded a24 wheel on both versions; no source-runtime import |
| Installed SDK feed lifecycle | All 40 a24 `test_view_feed_*.py` tests pass on both versions, including GC-disabled lifetime cases; tests are unchanged from the release tag |
| Actual native IPC/fixed SSH | Disposable default-server namespaces, private owner sockets and loopback sshd; both full-view and feed paths pass |
| Installed cost | Eight fresh-process Python 3.11 trials, two repetitions per mode/workload in reversed order; GC disabled, exact installed pair, one planned reconnect per trial |

The canonical command uses `UV_NO_SYNC=1` and an explicit isolated
`UV_PROJECT_ENVIRONMENT`, after installing the editable project and declared
development tools there. Initial bare synchronization failed before tests with
HTTP 401 from the existing lockfile's registry. Initial isolated probes also
required the editable package for their `python -I` children. Both environment
requirements were corrected; all checks ran. The lockfile's index and dependency
versions were preserved. Installed gates then replaced the editable package
with the committed wheel and excluded checkout runtime paths.

The native Fleet cases establish complete-empty versus unavailable, nonempty
views, exact native session order, insertion, rename, exact row restoration on
removal, unchanged-sample proof/expiry renewal, explicit refresh, owner
outage/restart, complete-empty after server removal and server-generation
rebirth. Attachment counts, native client list, session identities, hooks and
options are independently checked. A failed remote owner retains historical
rows without positives while the healthy local sibling remains current. The
remote command trace confirms `view-feed-bridge --source ... --stdio` only when
the selector is enabled; the legacy case uses `bridge`.

The pure Tmux-profile sequence uses public `CachedPublisher`, `FeedEncoder`
and `FeedReceiver` APIs to compare each reconstructed native target exactly,
including atomic receipt-only changes, order-only changes, partial failure,
expiry, warming and full identity rebirth. Ordinary Reader/ReadGuard/domain
projection remains the consuming path. Synthetic receipt cases are separate
from native unchanged-sample renewal through periodic full reads/proofs.

Three additional actual native IPC cases run with GC disabled: retained output
keeps credit after client close, held drain/close waits for unwind without early
refund, and failed write plus repeated cancel/close preserves a second client's
fresh full proof requests. No deadline is enlarged. SDK tests separately cover
zero-credit slow-peer gap/coalescing/exact replacement, reconnect, malformed
targets, retained errors, constructor refusal, budget pressure and real-pipe
stdio. Those SDK fault cases are protocol evidence, not a maximum native fleet
or managed SSH pressure qualification. No private Mesh helper is added to this
integration or its new tests, and no supported-SDK blocker required a workaround.

## Matched installed cost

[measurements.json](measurements.json) retains every raw trial, runtime file
hash, useful output, Reader operation count and accounting exclusion. Each trial
has two owners with 16 actual sessions, an initial baseline plus three actor
stages 2.5 seconds apart, and one planned reconnect. Mostly-static changes one
session per owner per stage; all-changing changes all 16. Both modes deliver
the same four useful 32-row outputs and 18 projected Reader frames, incur eight
full local cached snapshots and eight fresh full remote nonce proofs, and close
all connections. Feed adds four setup negotiations. Reads do not change native
collection cadence.

| Workload | Legacy total JSON bytes, two trials | Feed total JSON bytes, two trials | Median CPU: legacy / feed | Feed change: bytes / CPU |
| --- | --- | --- | --- | --- |
| Mostly-static | 543,211–543,212 | 526,168–526,169 | 4.582 s / 4.710 s | -3.14% / +2.79% |
| All-changing | 551,556 | 584,733 | 4.725 s / 4.961 s | +6.02% / +5.00% |

The memory samples show no consistent reduction: mostly-static summed RSS
peaks were 212.31–214.62 MiB legacy and 212.65–212.68 MiB feed; all-changing
peaks were 210.30–210.93 MiB legacy and 209.97–213.55 MiB feed. Two short trials
per cell establish a bounded comparison, not statistical confidence or a
normal-fleet performance estimate.

Totals count both directions once per completed owner-cache JSON edge and Mesh
JSON edge, including LF, full snapshots/proofs, setup, watch and reconnect. SSH
encryption/framing, failed partial writes and native tmux command stdout are
excluded. This is total completed application JSON at the declared boundaries,
not physical network bandwidth. Full Fleet service serialization, Rofi and
graphical consumer work are outside this measured Reader/domain-projection
workload; the separate native tests do exercise the actual Fleet service.

CPU includes coordinator, reaped descendants and sampled daemonized tmux server
work: owner collection/cache, bridge, SSH, validation, ordinary Reader copies,
Observer domain admission/projection, actor/oracle/instrumentation and cleanup.
Daemon sleep-shell CPU and processes not reaped through the owned tree are
excluded. Memory is 20 ms sampled simultaneous summed RSS for that tree plus
owned tmux daemons/descendants, including source input/cache, Reader copies,
profile and process runtime. Shared pages are counted repeatedly and short
peaks may be missed. Feed's 32 MiB encoded / 64 MiB heap reservation defaults
remain unchanged; these RSS samples do not establish an inclusive physical
capacity bound at those numbers.

## Reproduce and remaining gates

Verify retained hashes, unchanged source payload, gate counts and matched trials:

```sh
python docs/evidence/2026-10-20-view-feed-pilot/verify.py
python docs/evidence/2026-10-20-view-feed-pilot/verify.py \
  --artifacts .cache/view-feed-pilot
```

Installed integration uses each explicit interpreter without source runtime:

```sh
.cache/view-feed-pilot/py311/bin/python scripts/check-mesh --installed \
  --artifact .cache/view-feed-pilot/observer-a9/candidate.json
.cache/view-feed-pilot/py311/bin/python scripts/qualify-view-feed-pilot \
  --installed --mode feed --workload mostly-static --sessions 16 --stages 3 \
  --output /private/pilot.json
```

Repeat cost trials in fresh processes with identical arguments for legacy/feed
and reverse their order. The a24 SDK fault tests come from the exact tag's
`tests/test_view_feed_*.py` and run against the installed SDK, rather than that
checkout's `src`. [qualification.json](qualification.json) hashes retained
receipts and compressed original logs. [inputs.json](inputs.json) records native
tool hashes/versions (tmux 3.8 and OpenSSH 10.6p1) and preserved checkouts.

Maximum 256-session capacity, inclusive hard physical memory limits, populated
normal-host/fleet performance, actual two-host remote clocks, physical suspend,
graphical adoption, managed service/selection recovery, release publication and
rollout remain separate gates. Complete native schemas and systemd files are
unchanged from the starting commit. No normal service, live selection, sibling
source or released asset was changed by this pilot.

The primary owned decisions, native lifetime tests, comparison harness, overall
review, exact artifact checks and acceptance. Luna Max owned opt-in runtime/CLI
wiring, dependency/CI pins and Tmux correctness tests, then relinquished source
ownership for final review. No other model was delegated. Two local commits
separate the reviewed source candidate from qualification closeout; no push or
release is part of this result.
