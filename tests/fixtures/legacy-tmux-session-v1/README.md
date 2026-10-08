# Pinned legacy inventory schemas

These three schema files are copied unchanged from Rofi Tmux Plus source
`407ae58ba422ba88fed7da2f9d845ff274830f0e`, under its MIT license. They are a
test dependency for the fresh direct facade, not an Observer contract bundle.

`SHA256SUMS` is the original complete legacy bundle manifest. Its SHA256 must
match `docs/extraction-manifest.json`, and every copied schema must match its
listed digest. This directory deliberately contains only the schemas needed for
inventory/error validation; it does not claim complete legacy bundle coverage.
Native acceptance separately verifies the complete bundle in the unchanged
consumer checkout before consuming the installed CLI's raw output.
