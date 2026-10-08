"""Linux suspend-aware clocks; never compare these values across hosts."""

import os
import re
import time
from pathlib import Path


def boottime_ms() -> int:
    return time.clock_gettime_ns(time.CLOCK_BOOTTIME) // 1_000_000


def domain() -> dict[str, str]:
    match = re.fullmatch(r"time:\[([0-9]+)\]", os.readlink("/proc/self/ns/time"))
    if match is None:
        raise OSError("unsupported time namespace identity")
    return {
        "bootId": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
        "timeNamespace": "time:" + match[1],
    }


def pid_namespace() -> str:
    match = re.fullmatch(r"pid:\[([0-9]+)\]", os.readlink("/proc/self/ns/pid"))
    if match is None:
        raise OSError("unsupported local PID namespace")
    return "pid:" + match[1]
