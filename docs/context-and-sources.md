# Context and sources

Date: 2026-10-07. Sources were inspected read-only during this design pass.
Runtime measurements below come from the earlier Tmux Plus review in the same
conversation; they were not rerun for this documentation checkpoint.

## Checked repository context

| Repository | Checked context | Meaning |
| --- | --- | --- |
| `~/code/rofi-tmux-plus` | Clean `main`, released 0.6.0, `407ae58ba422ba88fed7da2f9d845ff274830f0e` | Immutable extraction baseline; existing contracts remain owned there |
| `~/code/tmux-observer` | New repository, unborn `main`, origin `byebyebryan/tmux-observer` | This checkpoint creates only design/planning documents |
| `~/code/agent-observer` | Design read at `3c71f216a716a36f2403f7c71fa5935c41c9917f`; checkout advanced to `53a7332106193babbcbaccd749e40022dbc8ef32` during this pass, with unrelated working changes | Active development reference, not an extraction or deployed-runtime dependency |

No Agent Observer runtime/deployment was inspected here. Its checkout moved
concurrently; no source or working changes were modified by this task. The plan
pins the accepted Tmux Plus baseline and borrows principles rather than binding
to another project's unaccepted development state.

Inspected Tmux Plus sources include `rofi_tmux_plus/tmux.py`, `model.py`,
`tmux_wire.py`, `wire.py`, `bounded_process.py`, `lifecycle.py`,
`viewer_service.py`, `inventory_service.py`, `picker_model.py`, `rofi.py`,
`presentation_cache.py`, `view_preferences.py` and `config.py`.

The canonical contracts are
[Tmux Session v1](https://github.com/byebyebryan/rofi-tmux-plus/blob/407ae58ba422ba88fed7da2f9d845ff274830f0e/contracts/tmux-session-v1/contract.md)
and [Host Mesh v1](https://github.com/byebyebryan/rofi-tmux-plus/blob/407ae58ba422ba88fed7da2f9d845ff274830f0e/contracts/host-mesh-v1/contract.md).
They govern current identity, bounds, fresh inventory, viewer evidence, action
validation, mesh authority and route reporting. New contracts do not replace them.

Agent Observer reference documents were `docs/architecture.md`,
`docs/contract-and-clients-plan.md`, `docs/shared-observation-service-plan.md`,
`docs/service-protocol-v1.md` and the shared-service/client handoff documents.
Borrowed ideas: host-local passive core; explicit source receipts; independent
producer/client acceptance; private shared service; no hidden direct fallback;
separate networking and actions. Explicit refresh hints are a deliberate Tmux
Observer-specific addition, not a claim that Agent Observer's subscriber API
already exposes forced collection.

## Recorded refresh baseline

The bounded [evidence JSON](evidence/2026-10-07-tmux-plus-refresh-baseline.json)
retains collection times, artifact digest, sample counts/durations, phase summaries
and the earlier callback trace. Raw native inventory, session names, process
arguments, SSH stderr and temporary trace paths are excluded.

The measured installed bundle digest was
`sha256:cbec5a4623130bbc293ee7ccd9611002c1abe0a0426a567540d3a3033b3eb41f`.
Both host runs reported version 0.6.0 and a two-host catalog. Their CLI/frame
measurements do not measure time to an actual graphical window.

| Context | Warm prepared frame median / p95 (20 samples) | Owner refresh median (5 samples) | Remote host phase median | Mesh-list phase median |
| --- | --- | --- | --- | --- |
| Snap, headless environment | 104 / 109 ms | 663 ms | 452 ms (7 samples) | 98 ms (65 samples) |
| Snap, captured desktop environment | 104 / 117 ms | 969 ms | 761 ms (6 samples) | 100 ms (63 samples) |
| Starship, headless environment | 69 / 72 ms | 517 ms | 420 ms (6 samples) | 56 ms (63 samples) |

The desktop-context Snap run's combined owner/viewer refresh median was 1,179 ms.
Remote phases varied up to approximately 952 ms. These are small recorded samples,
not a universal under-one-second guarantee, and phase medians are not additive
estimates of a concurrent operation's duration.

The callback reproduction requested a forced refresh at 4.254 seconds. At 5.015
seconds both job markers were complete, but view-arrow callbacks continued to
render cached `running`/refreshing presentation through 7.309 seconds. The idle
callback at 8.567 seconds finally cleared the notice: 4.313 seconds after the
request. This establishes an adoption/message problem in that callback path;
it is not a native GUI timing acceptance result.

Recorded effective SSH settings reported `ControlMaster=false` and
`ControlPersist=no` on the observed routes. Persistent owner watches should avoid
per-refresh connection setup, but the speedup, byte count and idle cost require
new measurements. A prepared service also removes recurring Mesh-list work from
foreground reads. Neither change alone fixes the Rofi inactivity callback.

## Primary references

- [tmux Control Mode documentation](https://github.com/tmux/tmux/wiki/Control-Mode)
  describes control-client attachment and notifications. The need to prove
  attachment/count/lifetime neutrality is this design's inference; enabling
  no-output alone is insufficient proof.
- [OpenSSH `ssh_config` manual](https://man.openbsd.org/ssh_config) documents
  connection sharing, persistence, noninteractive behavior and liveness options.
  Task-owned sharing and selected-route isolation are this design's operational
  constraints, not a proposal to change global SSH preferences.
- [Linux `clock_gettime(2)`](https://man7.org/linux/man-pages/man2/clock_gettime.2.html)
  documents BOOTTIME's inclusion of suspend. The cross-host nonce/remaining-lease
  translation is a proposed conservative algorithm, not a claim from that manual;
  it requires independent transport/clock proof.
- [systemd service specification](https://github.com/systemd/systemd/blob/main/man/systemd.service.xml)
  and [process termination specification](https://github.com/systemd/systemd/blob/main/man/systemd.kill.xml)
  inform restart and owned process-group cleanup. Actual units, stop deadlines
  and native lifetime still need G2/G3 acceptance.
- [Rofi 2.0.0 manual](https://github.com/davatorium/rofi/blob/2.0.0/doc/rofi.1.markdown)
  describes timeout behavior after user inactivity and input-change support.
  Whether a callback can update this frontend during continuous interaction
  without disturbing input must be demonstrated against the installed version.

These sources support the design constraints; they do not accept proposed APIs,
resource settings, extracted code, native events or managed deployment.
