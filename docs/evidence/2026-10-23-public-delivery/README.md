# Tmux Observer 0.6.0a9 public supply preparation

Prepared 2026-10-23 from the qualified, content-addressed wheel selected by
the 2026-10-20 full-view cohort. At preparation time the public `v0.6.0a9` tag
and GitHub prerelease were absent. This record prepares exact release inputs;
it does not claim a push, tag or publication.

## Release assets

| Asset | Bytes | SHA-256 | Prepared source |
| --- | ---: | --- | --- |
| `candidate.json` | 55,770 | `10bab8158d8f7ee108b74ae6c4f07cf00de7624d56ff333d55a79a480886803a` | `docs/evidence/2026-10-20-view-feed-pilot/candidate.json` |
| `tmux_observer-0.6.0a9-py3-none-any.whl` | 259,872 | `b117cc5d353f323ce25c6629dc3371d5d95aa349639cf09974fda3a62f8d7738` | `/home/bryan/.local/share/tmux-observer/artifacts/b117cc5d353f323ce25c6629dc3371d5d95aa349639cf09974fda3a62f8d7738/` |

The descriptor verifies the frozen wheel, its 182-member inventory and its
source mapping. Its `built_unaccepted` state is builder provenance; acceptance
belongs to the separate records below.

## Provenance and qualification

- Runtime wheel source: `bb4b0438864e587f3d70cce2576d25c76aa8460a`.
- Selected artifact review source: `7b2d6917a48c858f9ec18140cb0c59a3166f2899`.
- Managed full-view qualification record: `a71a4d55bb6f428fc142caf6422f60424425173b`.
- The release source tip may be later than the wheel source. The exact tag
  target is the prepared source branch tip reported with the local handoff; do
  not relabel the wheel's `sourceCommit` as that tag target.
- The selected Tmux Mesh a24 route remains full-view. `view-feed` and semantic
  delta remain disabled.

The [candidate qualification](../2026-10-20-view-feed-pilot/README.md) and
[managed full-view acceptance](../2026-10-20-mesh-a24-full-view/README.md)
retain their original scopes. Neither the public source tag nor the wheel build
source changes those scopes.
