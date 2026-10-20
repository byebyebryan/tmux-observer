# Tmux complete-view feed pilot

This is the owning source/private qualification record for the opt-in
[a24 integration](../../view-feed-pilot.md). Qualification is in progress in
the isolated `view-feed-pilot-20261020` branch; installed-candidate results and
the final measured decision will be recorded separately from managed rollout.

The baseline is Tmux Observer `7e14d799796a96b81f3a35947a7ed3c535701bf2`.
Mesh is the downloaded experimental a24 wheel, SHA256
`9bca5b554babfa59ba56b1a4ac5e8e5c66a85e63709731ee1fe7d4f0ed6a18a6`,
tag `bb0c45399e5b8264c9936ca48457cc9a442431df`.

The primary owns decisions, the comparison harness, overall review, exact
artifact checks and acceptance. Luna Max owns the opt-in runtime/CLI wiring,
dependency/CI pins and Tmux correctness tests. No other model was delegated.
No managed service, installed selection, producer sibling or released asset is
an edit target in this pilot.
