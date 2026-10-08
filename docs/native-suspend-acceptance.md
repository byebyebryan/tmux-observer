# Physical suspend acceptance preparation

G3 requires actual host sleep/wake in each direction. Source clock-jump tests,
SIGSTOP, transport delays and existing headless profiles do not establish this.
No whole-host suspend was executed by this preparation.

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
