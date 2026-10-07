# observation-v1

Version 1 schema/fixture boundary. Runtime acceptance is separate.

Use structural validation and the semantic rules in `docs/wire-v1.md`
together. Unknown fields are bounded extensions, never source/action authority.
Bundle SHA256SUMS covers every file except itself; dependency digests bind the
other canonical bundles. All fixture hosts and paths are synthetic.
