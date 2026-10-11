# Owner profile and Mesh SDK adoption, 2026-10-11

The [adoption guide](../../mesh-sdk-adoption.md) separates the pure profile,
explicit reader integration, frozen package, consumer and managed gates.
Research and the first a11 measurements retain their own exact inputs.

## Final frozen producer input

[Observer 0.6.0a6](observer-a6-candidate.json) is built from
`cb45e40a7915f78fc13a65b955d2ce2d2bc7b4e9`. Its 255,727-byte wheel has SHA-256
`232e604ab64c99657852b884720afaefdbcd45be00a56a797793b402e36ff640`.
The descriptor remains `built_unaccepted`; dated reports establish their own
acceptance scopes. [Mesh a13 and its dependency inputs](mesh-a13-inputs.json)
name immutable reviewed wheels, rather than a sibling checkout HEAD.

The source gate passes 404 tests and the source Mesh gate passes 24 tests.
[Installed Mesh acceptance](installed-mesh-a13.json) verifies all 84 runtime
Python modules and runs the same 24 cases from the installed wheel.
[Mixed-version acceptance](mixed-mesh-a13.json) uses that reader against an
isolated installed a10/Observer-a5 SSH bridge. The
[portable conformance report](conformance-a13.json) separately records six
independent profile cases, ten IPC/remote-proof lifecycle cases, one actual
owned SSH case, and rejection of a profile dropping required receipts.

The [native owner gate](owner-a13.json) passes 11 cases; the
[native direct gate](direct-a13.json) passes 28 cases on two hosts. The
[recovery simulation](recovery-a13.json) passes four clock/callback/pipe cases
without changing host power. [Synthetic capacity](capacity-a13.json) and
[actual SSH capacity](ssh-capacity-a13.json) pass their eight and eleven cases.
The latter exercises sixteen logical owners, fifteen strict SSH links and
thirty-two readers on two physical hosts. Its near-cap replies meet the
unchanged 250 ms deadline and sampled combined memory remains below 768 MiB.
These counts do not imply sixteen physical hosts or a capacity CPU soak.

[The final 600-second resource gate](normal-a13-summary.json) passes on both
physical hosts. Snap uses 4.286% combined CPU, Starship 2.508%, against 5%.
Fleet plus associated bridge RSS is 83.004/82.430 MiB against 96 MiB; owner RSS
is 24.785/19.875 MiB against 64 MiB. Both hosts pass 100 warm queries within
their deadlines. Native identities, hooks and attachment counts survive owned
teardown. This accepts headless cached delivery only; sampled RSS can miss
transient peaks, and no graphical or physical-suspend acceptance is claimed.
The producer package is accepted within these recorded scopes. Consumer and
managed acceptance pass independently as recorded below.

## Consumer and managed completion

[Plus a6 acceptance](https://github.com/byebyebryan/rofi-tmux-plus/blob/main/docs/evidence/2026-10-11-mesh-sdk-adoption/README.md)
passes 293 source tests and installed wheel/bundle headless gates. The 100-frame
p95 values are 57.963/58.929 ms, below 150 ms. Observer a6 and Plus a6 releases
are published; downloaded wheel/bundle assets match the accepted hashes.

[Managed acceptance](managed-acceptance.json) binds configuration `e094b17` and
both hosts' installed checks, recovery, restored a5 paired baseline and a6
reselection. Snap uses owner scope; Starship uses desktop scope. Cached snapshot
and watch deliver all fourteen native rows through each endpoint's explicit a13
profile with owned connection retirement. The
[retained a10 CLI/new a6 facade matrix](retained-bridge-a13.json) passes all 24
installed cases. Kernel peers, interpreter and source clocks match each owner.
Agent's a17 reader/a16 bridge remains independently accepted; its packages and
service incarnations are unchanged. Native generations/references/hooks/client
counts, static controls, preferences and Starship's two source edits survive.

Snap's first apply failed on a missing versioned SDK parent and restored the
captured pair/controls before retry. Parent preparation precedes the successful
apply. The archived [adoption helper](adopt-cohort.py),
[cached probe](cached-probe.py), [native preservation](native.py),
[kernel identity](identity.py) and [protection snapshot](preserve.py) bind their
executed hashes; they are dated harnesses, not general deployment entry points.
Private logs, ordinary native identities and rollback control bodies stay local.
Starship's route-health aggregate changes under existing reporting policy. Its
recent-history file's last write precedes the baseline; the per-file baseline
digest was not captured, so the report states that timestamp evidence limit.

Source CI passed Observer `cea86a9` and Plus `215c705`. The final documentation
commits advance these heads without changing the frozen runtime artifacts.
Graphical input and physical suspend remain optional and unrun. Native publisher
extraction retains its independent fixed-CLI factory/endpoint review.

Only `tmux_observer/__init__.py`, the optional compatibility `mesh.py` module and
the Mesh worker differ from the selected a5 runtime; `mesh_profile.py` is new.
Native/core, refresh/action, desktop matching and UI contracts retain their
prior bytes. The current cached publisher reference adapter remains supported;
its extraction needs the separate fixed-CLI factory review in the plan.

## Historical a11 input

[The a11 input tuple](mesh-inputs.json) and
[ten-minute resource summary](normal-a11-summary.json) bind the preceding
frozen a6/a11 candidate. Snap's combined CPU is 4.05%, Starship's 2.60%; memory
and query deadlines pass. Those measurements accept their own bytes, with
headless cached delivery and owned cleanup only. They are not relabeled as
a13 acceptance. Private full resource reports, ordinary references and rollback
control bodies stay outside the repository; summaries bind their report digests.
