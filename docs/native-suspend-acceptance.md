# Physical suspend acceptance preparation

G3 requires actual host sleep/wake in each direction. Source clock-jump tests,
SIGSTOP, transport delays and existing headless profiles do not establish this.
No whole-host suspend was executed by this preparation.

The user explicitly deferred sleep on both Snap and Starship because both hosts
are actively working. Keep both power states and alarms untouched while that
deferral is in force. Continue independent awake-host acceptance and review;
the physical G3 cases remain open. This is a deferral, not physical acceptance
or removal of the producer/frontend/deployment gates. Do not repeat the timing
request during this pass.

Read-only preflight on 2026-10-07 found `freeze mem disk` on both hosts, Snap
using `[s2idle]` and Starship offering `s2idle [deep]`. Both expose an RTC0
wakealarm path. These observations establish advertised interfaces, not permission
to arm an alarm or successful hardware wake. Recheck them at execution time.

A later read-only preflight found no pending RTC0 alarm on either endpoint.
User-mode `CanSuspend` returned `yes` on Snap and `challenge` on Starship; both
had sleep-delay inhibitors but no sleep-block inhibitor. Privileged
`sudo -n rtcwake --dry-run --mode no --seconds 30` succeeded on both hosts.
The installed util-linux manual defines dry-run as not setting an alarm,
suspending or waiting. This verifies noninteractive access to the proposed RTC
interface, not actual wake or an agreed whole-host interruption. No alarm was
armed. Honour inhibitors explicitly in the eventual logind/systemctl operation;
root access alone must not bypass them.

## Concrete execution profile

`scripts/accept-native-suspend` now prepares the installed two-host fixture and
runs independent cached supervisors. Its default mode is preparation only:

```sh
uv run --extra dev python scripts/accept-native-suspend --output /tmp/suspend-preparation.json
```

Both private endpoints install the same wheel, capture native references,
attachment/window counts, hooks and pane geometry, and check logind permission,
inhibitors, enabled RTC wake capability and noninteractive access. Preparation
keeps both sources readable for six seconds and verifies empty alarms afterward.
Five safety regressions cover an existing alarm, blocking versus delay inhibitors,
a blocker appearing after arming, an asynchronous suspend enqueue without actual
sleep, and an unavailable first resumed read. These are safety/source checks,
not physical acceptance.

Clean source `4465887` passed four preparation cases on both endpoints with the
same installed wheel; see [captured preparation evidence](evidence/2026-10-07-native-suspend-preparation-g3.json).
Snap/Starship supervisors captured 30/31 validated prepared responses, with
observed maxima 11.27/3.77 ms. Native identities, attachment/window counts, hooks
and pane geometry matched before/after. Both clocks showed no physical suspend
delta, both alarms stayed empty, and all owned units/children/sockets/backing
directories were removed. Both RTC wake capabilities were enabled, read-only
privileged alarm access passed and no sleep-block inhibitor was present.
This accepts preparation only; actual hardware wake and resume fencing remain
unexecuted until the agreed whole-host interruption window.

On 2026-10-08 the final frozen wheel at source `3beab8a` also passed all four
[preparation-only cases](evidence/2026-10-08-final-candidate-suspend-preparation.json),
using clean harness `25befbc` and the coordinator's default mode without
`--sleep`. The exact wheel SHA256 matches the final candidate's other native
checks. Each endpoint supplied 31 validated cached samples; Snap/Starship maxima
were 9.72/3.68 ms and both recorded zero suspend delta. Alarms stayed untouched,
native baselines/passivity passed, and both endpoints' owned units, children,
sockets and private roots were removed. This exercises the frozen-artifact input
of the preparation harness, not physical resume or hardware wake. The user's
deferral and the G3/consumer/deployment dependencies remain in force.

Physical execution is an explicit `--sleep snap` or `--sleep starship` invocation
with a separate evidence output, after the agreed interruption window. Each
invocation sleeps one endpoint; the other supervises it. The helper sets a
relative `+30` alarm through the
[kernel RTC sysfs interface](https://github.com/torvalds/linux/blob/master/drivers/rtc/sysfs.c),
which checks for an already enabled alarm, reads back the deadline and rechecks
inhibitors. It invokes `systemctl --check-inhibitors=yes suspend`. The
[systemd command documentation](https://github.com/systemd/systemd/blob/main/man/systemctl.xml)
describes suspend as an asynchronous enqueue; a successful exit is insufficient.
The helper instead requires a physical BOOTTIME/MONOTONIC delta exceeding ten
seconds on the same boot and clock namespace. It clears only a matching owned
alarm; a changed alarm is preserved and recorded as failure.

The supervisor retains bounded metadata, first invalid/recovered full frames,
and the first response after its own resume, including typed unavailability.
Installed validation handles every read; the independent acceptance reader
checks captured complete frames. Failure and cleanup failures remain evidence.
An alarm-owning helper is allowed to finish its guarded cleanup; timeout does
not trigger a reboot or a process kill. Backing paths remain available when
cleanup cannot be verified.

Use one accepted wheel in the existing two-host disposable default-server/unit
fixture. Record independent native generation, full references, creation times,
client/window counts and hooks before sleeping. Keep ordinary sessions and user
configuration untouched. Use the awake endpoint as the supervisor; sleep only
one host at a time, with a proposed 30-second interval exceeding the owner lease.

Before any suspend, verify a permitted RTC wake mechanism and a recovery path.
Preserve an existing wakealarm rather than overwriting a pending user alarm.
Arm and read back the proposed wake deadline. Honour active suspend inhibitors;
do not bypass them. A native RTC path existing is insufficient for this gate.
The whole-host interruption needs an agreed test window after this fixture and
wake/recovery procedure are prepared; brief isolated GUI authorization alone
does not specify when ordinary desktop/network availability may be interrupted.

Collect paired BOOTTIME/MONOTONIC readings and clock-domain identity immediately
before sleep and on the first resumed sample. Record the positive difference
between their elapsed durations to corroborate actual suspend. Preserve bounded
kernel/logind suspend-entry/resume evidence when readable. An unchanged boot ID
distinguishes resume from reboot; a PID freeze advances both clocks and cannot
substitute for this measurement.

On the awake supervisor, continue independent cached reads during peer sleep.
The sleeping peer's current authority must expire or fail within its existing
lease/liveness bounds while the supervisor's other sources remain readable.
After local resume, old owner/desktop leases and pending remote proofs cannot
regain positives from buffered data. Require a new in-budget native sample and
matching conservative proof before current confirmation; a desktop positive
requires a scan joined to those newly accepted inputs. Keep transport recovery,
owner receipt and desktop receipt timestamps distinct.

Repeat with Snap sleeping and then Starship sleeping. Compare the owned native
facts afterward, including preserved generation/references and absence of added
clients, hooks or geometry changes. Stop only the fixture units/children, verify
their exit and remove their private IPC/backing paths. Record failure, timeout
or unsupported wake honestly; never reboot a host or kill ordinary sessions as
an automated fallback.

## Required evidence

Each direction records source/wheel identity, endpoint/clock scope, armed and
actual wake times, paired-clock deltas, last pre-sleep positive expiry, first
post-resume prepared response and the later sample/proof/desktop admission.
The independent reader verifies captured records; separate native reads verify
session survival. This is physical G3 evidence only, not Rofi notice latency,
managed logout/recovery or Starship graphical acceptance.
