# Validation and acceptance plan

Date: 2026-10-07. Planned evidence; no new native/GUI/service acceptance occurred
in this documentation pass. Earlier Tmux Plus measurements are retained as a
[baseline](context-and-sources.md#recorded-refresh-baseline), not Observer results.

## Evidence levels

| Evidence | Establishes | Does not establish |
| --- | --- | --- |
| Document/link/example checks | Reviewable design and internal consistency | Implemented semantics |
| Pure fixtures and source checks | Framing, parser, model and simulated transition behavior | Native tmux passivity or SSH recovery |
| Independent native collector comparison | Identity/metadata and absence behavior on tested native versions | Shared-service or graphical behavior |
| Independent native service reader | Shared samples, leases, ordering and lifetime on tested hosts | Fleet joins or frontend latency |
| Two-host installed transport exercise | SSH proof/recovery and endpoint behavior for exact artifacts | Untested routes or graphical interaction |
| Native Rofi interaction | Actual filter/selection, notice and visible update behavior | Another endpoint's GUI |
| Scoped managed rollout and byte comparison | Selected artifact/configuration and installed bytes | Runtime acceptance without exercising it |

Keep candidate, source commit, dependency/native versions, host/context, clocks,
duration, operations and result codes with each evidence bundle. Persist bounded
metadata/counters, never pane output, raw argv/environment or session content.

## Contract and direct-producer cases — G0/G1

- Independent public validator imports no native collector, service or action
  implementation. Test supported versions and declared extension policy.
- Reject raw-invalid UTF-8, duplicate keys, extra records, missing LF, oversized
  frames/strings, booleans as numbers, nonfinite/overflow values and excessive
  nesting/nodes before semantic projection. Bound partial/trickled records by
  an absolute deadline, not a timeout reset for each byte.
- Validate all four identity fields. Exercise rename, session ID reuse within
  one server, server replacement, scope mismatch and conflicting descriptors.
- Compare one accepted sample against independently issued native reads bracketed
  with incarnation checks. Never use the producer's own JSON as its oracle.
- Distinguish native no-server, complete-empty, missing binary, partial parsing,
  disappearing descriptor, pending marker and command failure. Failed batches
  cannot erase a prior roster or invent zero attached clients.
- Verify fast/legacy native parsing with escaped separators, newlines and bounded
  metadata. Optional legacy options/panes stay explicit and bounded.
- Audit the read command allowlist and process cleanup. Start with no tmux server
  and prove collection creates none. Compare client counts, last-attached clocks,
  native options, session lifetime and geometry before/during/after observation.

Native probes use an owned disposable server via test-only runner injection or
an isolated user environment. Shipped default-server configuration must also be
exercised. Preserve ordinary sessions, hooks/options and user configurations;
restore temporary preferences/services and remove only owned resources.

## Owner service — G2

| Scenario | Required result |
| --- | --- |
| Ready socket before first read | Warming with null snapshot, never complete-empty |
| Unchanged successful sample | Accepted receipt renews; no invented activity/change |
| Collector failure after healthy sample | Current confirmation invalidated; historical descriptors remain |
| Subscriber reads/heartbeats | No collection-rate or native-lease renewal |
| Publisher restart with disk cache | New incarnation; historical cache stale until fresh read |
| 1, 8 and 32 subscribers | One source-owned schedule; bounded fan-out and healthy-reader progress |
| Slow subscriber / maximum-size frame | Declared queue budget, gap/resync or bounded disconnect |
| Saturated refresh hints | One job per source, minimum spacing, bounded ticket store |
| Refresh while owner/desktop inputs change | Correct epoch/job association; obsolete work cannot finish a new ticket |
| Duplicate service / unsafe socket path | Explicit refusal; no unlink of another live endpoint |
| Shutdown / failed child / deadline | Owned children reaped; no kill of native tmux or unrelated services |
| Boot / logout / headless user manager | Actual publisher availability matches the explicit managed lifetime policy |

Use an independent reader for sequence/incarnation/receipt assertions. Compare
native command counters across subscriber populations, not just service logs.
The stdout bridge validates both directions, partial input and broken pipes.

## SSH/fleet and clocks — G3

Run Snap reading Starship and Starship reading Snap. Use task-owned delay/fault
relays and disposable service contexts; do not disturb ordinary SSH or tmux.

| Scenario | Required result |
| --- | --- |
| Differing wall clocks / remote BOOTTIME | No cross-host subtraction or timestamp-order inference |
| Buffered old view or delayed/trickled probe | No receipt extension from arrival; absolute deadline enforced |
| Wrong/reused nonce, scope or incarnation | Proof rejected; no positive publication |
| Lease expired at publisher or consumed by RTT | Historical only; translated remaining validity is zero |
| Unsolicited changed view | One coalesced proof; publish the confirmed full response |
| Owner failure on a live SSH stream | Transport stays distinct from failed native evidence |
| Lost sequence / EOF / service restart | Invalidate old lease; guarded full resync before positives |
| Simulated service pause / elapsed-clock gap | First prepared read rejects expired leases and viewer membership; late work/proofs cannot renew them |
| Optional physical sleep/wake | Host-specific BOOTTIME and transport recovery check; outside required always-on acceptance |
| One remote hangs or reconnects | Other hosts and cached queries continue independently |
| Mesh host removed / route replaced | Reject late epochs; update catalog within declared recheck bound |
| Mesh executable absent versus present/broken | Only absent provider permits local-only fallback |
| Valid Mesh becomes invalid/unavailable at recheck | Retained catalog is historical; fleet authority recovers only after revalidation |
| SSH reached host, owner socket absent | Typed service error; never report host unreachable |
| Multiple read clients | At most one selected owner watch per configured host/context |
| Host/fleet bound exceeded | Explicit capacity failure, never truncated complete JSON |
| Fleet service stop | Close only owned bridge/SSH children and private masters |

For the age algorithm, generate publisher receipts independently, including
maximum advertised remaining lease and queue delay at each hop. Check the local
expiry never exceeds the conservative bound. Native delayed SSH tests must
corroborate the simulated clock cases; successful loopback fixtures are insufficient.

Desktop evidence is tested separately: confirmed metadata, qualified manual SSH
match, multiple conflicting matches, missing compositor, unsupported terminal,
headless context, changed owner name/reference/count/route, owner expiry and
desktop socket replacement. A fresh scan never refreshes owner attachments.
Compare Open here on each endpoint with direct native desktop inspection;
globally attached is not an expected local-window count. No handles/actions are
available through these observations.

## Performance and resource measurements

Measure prepared queries and source lag separately. A warm query reads prepared
state; it does not guarantee a native change less than one second old. The initial
two-second owner cadence plus collection, proof and desktop join can take several
seconds. Explicit refresh has its own bounded ticket and source-level outcomes.

| Metric | Initial acceptance target/profile |
| --- | --- |
| Warm local cached RPC, including validation | p95 ≤50 ms; absolute client deadline 250 ms |
| Warm prepared Rofi frame, including client/process startup | p95 ≤150 ms; no native/SSH collection on that path |
| Graphical keypress/open to useful first view | Target p95 ≤500 ms, measured independently from frame creation |
| Native complete read to fleet-confirmed replacement | Record owner publication, proof RTT and fleet adoption separately |
| Ticket terminal result to visible notice removal | Target ≤one accepted callback interval; test active input and idle separately |
| Normal two-host idle CPU | Combined owner + fleet + owned children mean ≤5% of one core |
| Normal two-host memory | Target each service plus owned children ≤64 MiB RSS |
| Maximum subscriber/declared-capacity profile | Hard logical queue caps; target each service plus owned children ≤256 MiB RSS |
| Stop/reap | All owned children gone within five seconds; native sessions preserved |

Targets are design candidates, not existing results. G0 fixes the measurement
profile; G2/G3 establish viable tuning with evidence before these are supported
claims. If the normal profile fails, review cadence/bounds/process choices rather
than weakening freshness or hiding work outside the measurement.

The table preserves the initial targets and failed evidence. The subsequent
[resource review](resource-design-review.md#selected-direction) records the user's
selected candidates for further fleet verification: normal fleet plus all owned
children ≤96 MiB, declared-capacity fleet plus all owned children ≤768 MiB. Owner
ceilings and CPU/foreground/logical limits retain their initial values. Selecting
these candidates is not native profile or G3 acceptance.

Use at least 100 warm foreground samples per endpoint for a reported p95, retain
duration arrays and state conditions, and report cold/service-absent separately.
Collect at least ten minutes of idle/background counters asynchronously, including
SSH bytes/connections, Mesh calls, native commands, RSS/CPU and queue high-water
marks. Test capacity separately; do not present the normal two-host result as
128-host acceptance. Avoid blocking user communication during long collection.

## Rofi and compatibility — G4/G5

Graphical acceptance on Snap uses isolated preferences/cache and disposable
sessions; the earlier endpoint preference was Snap. Record Starship graphical
acceptance separately if/when tested. Headless commands do not satisfy that gate.

- Open with prepared healthy, warming, stale and unavailable service data.
  A missing service must terminate the foreground query within its deadline.
- Restore scope and exact remembered row; filtering starts with the intended
  clean state. Renamed/replaced/missing remembered references fall back safely.
- Hold typing/navigation while a requested refresh completes. Separately measure
  worker finish, service/ticket adoption and actual notice disappearance.
  Exercise caret/filter preservation and avoid input-change callback loops.
- Switch All/Local/Open/Attached while remote owner and desktop receipts renew
  independently. Unknown membership stays visible instead of a false empty view.
- Open destructive confirmation, publish a changed roster and execute/cancel.
  The target remains exact and is revalidated; no newly selected row is acted on.
- Validate the existing Tmux Session v1 CLI with an independent strict consumer:
  flags, JSON/exit behavior, direct freshness, bounds, Host Mesh fallback,
  `--with-viewers`, optional metadata and lifecycle result/handle semantics.
- For G5, verify native focus/attach/close/create/rename/kill independently of the
  observation service, including stale references, PID reuse, session survival,
  unsupported close and ambiguous remote write. Never retry an ambiguous action.

## Managed rollout — G6

Match published archive digest/revision, rendered managed configuration and
installed bundle bytes on each host. Verify explicit unit ownership/environment,
source scope, private sockets, versions and restart behavior. Accept publisher,
fleet, legacy CLI and GUI independently. Run the recorded scoped rollback and
verify previous behavior plus preserved sessions and unrelated managed drift.

The first runtime evidence record lists exact artifact IDs, which gates passed,
which endpoint has GUI proof and all remaining limitations. A design review or
successful deployment command is never substituted for those results.
