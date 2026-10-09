"""Explicit fresh fleet diagnosis, retaining the released inventory shape."""

from __future__ import annotations

import copy
import re
import shlex
import socket
import sys
import time
import unicodedata
import uuid
from concurrent.futures import ThreadPoolExecutor

from tmux_observer._clock import boottime_ms
from tmux_observer.native import decode_document, encode_document, validate_observation

from ._command import run_bounded
from ._errors import ContractError
from .mesh import HostMeshAdapter, MeshHost

REACHED = "\x1eTMUX_OBSERVER_REACHED_V1:"
REMOTE_EXEC = '"$HOME/.local/share/tmux-observer/bin/tmux-observer"'


def safe_alias(value):
    return (
        isinstance(value, str)
        and bool(value)
        and value.strip() == value
        and not value.startswith("-")
        and not any(char.isspace() or unicodedata.category(char).startswith("C") for char in value)
    )


def fallback_host(requested, deadline, runner):
    """Keep legacy local aliases; bound optional FQDN discovery off the UI path."""
    short = socket.gethostname().split(".", 1)[0] or "localhost"
    host_id = (
        short.casefold() if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", short) else "localhost"
    )
    aliases = [short] if safe_alias(short) else [host_id]
    if any(name.casefold() not in {alias.casefold() for alias in aliases} for name in requested):
        # getfqdn can consult DNS and block. Only non-short selection needs it;
        # an owned child enforces the direct operation's BOOTTIME deadline.
        remaining = deadline - boottime_ms()
        if remaining <= 0:
            raise ContractError("operation_failed", "local identity deadline exceeded")
        try:
            result = runner(
                [
                    sys.executable,
                    "-I",
                    "-c",
                    "import json,socket; print(json.dumps(socket.getfqdn()))",
                ],
                timeout=min(2, remaining / 1000),
                stdout_limit=32768,
                stderr_limit=4096,
            )
            if (
                result.returncode
                or result.timed_out
                or result.overflow_streams
                or boottime_ms() >= deadline
            ):
                raise ValueError("local identity lookup failed or exceeded its bound")
            full = decode_document(result.stdout_bytes, limit=32768)
            if not isinstance(full, str):
                raise TypeError("local identity lookup returned invalid text")
            aliases = [name for name in (full, short) if safe_alias(name)] or [host_id]
        except (OSError, ValueError, TypeError) as error:
            raise ContractError(
                "operation_failed", "bounded local identity lookup failed"
            ) from error
    display = (
        short
        if short.strip() == short
        and not any(unicodedata.category(char).startswith("C") for char in short)
        else host_id
    )
    return MeshHost(host_id, display[:255], True, tuple(aliases), ())


def ssh_argv(route, policy, program):
    return [
        policy.executable,
        "-T",
        "-o",
        "BatchMode=yes",
        "-o",
        "StrictHostKeyChecking=yes",
        "-o",
        f"ConnectTimeout={policy.connect_timeout_seconds}",
        "-o",
        f"ConnectionAttempts={policy.connection_attempts}",
        "-o",
        "ControlMaster=no",
        "-o",
        "ControlPath=none",
        "-o",
        "ControlPersist=no",
        "-o",
        "ClearAllForwardings=yes",
        "-o",
        "ForwardAgent=no",
        route,
        program,
    ]


def profile(panes, option_names):
    names = tuple(dict.fromkeys(option_names))
    if any(
        not isinstance(name, str)
        or len(name) > 16384
        or re.fullmatch(r"@[A-Za-z0-9_.-]+", name) is None
        for name in names
    ):
        raise ContractError("invalid_input", "invalid user option profile")
    return (["--panes"] if panes else []) + [item for name in names for item in ("--option", name)]


def observation_row(host, value, route=None):
    validate_observation(value)
    if value["source"]["hostId"] != host.host_id:
        raise ContractError("operation_failed", "owner observation has a foreign host scope")
    coverage = value["sample"]["coverage"]
    row = {
        "hostId": host.host_id,
        "display": host.display,
        "local": host.local,
        "status": "ok"
        if coverage == "complete"
        else "tmux_missing"
        if coverage == "unsupported"
        else "error",
        "observedAt": value["sample"]["observedAt"],
        "nativeHostname": value["source"]["nativeHostname"],
        "serverGeneration": value["serverGeneration"],
        "route": None if host.local else route,
        "sessions": copy.deepcopy(value["sessions"]),
    }
    if coverage != "complete":
        issue = value["sample"]["error"]
        row["error"] = {
            "code": "tmux_missing" if coverage == "unsupported" else "operation_failed",
            "message": issue["message"],
        }
    return row


def failed_row(host, code, message, route=None):
    row = {
        "hostId": host.host_id,
        "display": host.display,
        "local": host.local,
        "status": "unreachable" if code == "host_unreachable" else "error",
        "observedAt": time.time_ns() // 1000000,
        "nativeHostname": None,
        "serverGeneration": None,
        "route": None if host.local else route,
        "sessions": [],
        "error": {"code": code, "message": message},
    }
    return row


class DirectInventory:
    def __init__(
        self,
        *,
        mesh=None,
        local=None,
        runner=run_bounded,
        remote_exec=REMOTE_EXEC,
        identity_runner=run_bounded,
    ):
        self.mesh = mesh or HostMeshAdapter()
        self.local = local
        self.runner = runner
        self.remote_exec = remote_exec  # Private owned acceptance injection, not a CLI option.
        self.identity_runner = identity_runner

    def remote(self, host, policy, revision, *, deadline, panes, option_names):
        last = ("operation_failed", "SSH did not prove the selected owner was reached")
        for route in host.routes:
            remaining = deadline - boottime_ms()
            if remaining <= 0:
                return failed_row(host, "operation_failed", "fresh fleet deadline exceeded")
            nonce = uuid.uuid4().hex
            arguments = ["collect", "--host-id", host.host_id, *profile(panes, option_names)]
            program = "printf '\\036TMUX_OBSERVER_REACHED_V1:%s\\037\\n' " + shlex.quote(nonce)
            program += (
                " >&2; exec " + self.remote_exec + " " + " ".join(map(shlex.quote, arguments))
            )
            try:
                result = self.runner(
                    ssh_argv(route.destination, policy, program),
                    timeout=min(remaining / 1000, 8),
                    stdout_limit=1048576,
                    stderr_limit=65536,
                )
            except OSError:
                return failed_row(host, "operation_failed", "SSH executable is unavailable")
            reached = (
                not result.timed_out
                and "stderr" not in result.overflow_streams
                and result.stderr.count(REACHED + nonce + "\x1f\n") == 1
            )
            if reached:
                self.mesh.report_route(
                    host_id=host.host_id,
                    route=route.destination,
                    status="reachable",
                    mesh_revision=revision,
                    observed_at=time.time_ns() // 1000000,
                    timeout_seconds=max(0.001, (deadline - boottime_ms()) / 1000),
                )
                if result.overflow_streams or boottime_ms() >= deadline:
                    return failed_row(
                        host,
                        "operation_failed",
                        "fresh owner output exceeded its bound",
                        route.destination,
                    )
                try:
                    value = decode_document(result.stdout_bytes)
                    validate_observation(value)
                    if result.returncode != (0 if value["sample"]["coverage"] == "complete" else 1):
                        raise ValueError("invalid direct exit/coverage binding")
                    if value["capabilities"]["panes"] != panes or value["capabilities"][
                        "options"
                    ] != list(dict.fromkeys(option_names)):
                        raise ValueError("direct capability profile differs")
                    return observation_row(host, value, route.destination)
                except (ContractError, ValueError, TypeError):
                    return failed_row(
                        host,
                        "operation_failed",
                        "remote owner returned malformed or incompatible observation",
                        route.destination,
                    )
            # Authentication/host-key/publisher failures are not reachability negatives.
            diagnostic = result.stderr.casefold()
            unreachable = result.timed_out or any(
                text in diagnostic
                for text in (
                    "could not resolve hostname",
                    "connection refused",
                    "connection timed out",
                    "no route to host",
                    "network is unreachable",
                    "connection reset by peer",
                    "name or service not known",
                )
            )
            if unreachable:
                self.mesh.report_route(
                    host_id=host.host_id,
                    route=route.destination,
                    status="unreachable",
                    mesh_revision=revision,
                    observed_at=time.time_ns() // 1000000,
                    timeout_seconds=max(0.001, (deadline - boottime_ms()) / 1000),
                )
                last = ("host_unreachable", "configured SSH route is unreachable")
            else:
                last = ("operation_failed", "SSH did not prove the selected owner was reached")
        return failed_row(host, *last)

    def inventory(
        self,
        *,
        requested_hosts=(),
        mesh_revision=None,
        panes=False,
        option_names=(),
        with_viewers=False,
        desktop_config=None,
    ):
        profile(panes, option_names)
        deadline = boottime_ms() + 15000
        mesh = self.mesh.load(timeout_seconds=5)
        if mesh is None:
            if mesh_revision is not None:
                raise ContractError("stale_mesh", "local-only mesh has no route revision")
            hosts = (fallback_host(requested_hosts, deadline, self.identity_runner),)
            revision = None
        else:
            if mesh_revision is not None and mesh.revision != mesh_revision:
                raise ContractError("stale_mesh", "Host Mesh changed; refresh and try again")
            hosts = mesh.hosts
            revision = mesh.revision
        wanted = set()
        for name in requested_hosts:
            matches = [
                host.host_id
                for host in hosts
                if name.casefold()
                in {host.host_id.casefold(), *(alias.casefold() for alias in host.aliases)}
            ]
            if len(matches) != 1:
                raise ContractError("unknown_host", "unknown Host Mesh host", name)
            wanted.update(matches)
        selected = [host for host in hosts if not wanted or host.host_id in wanted]
        rows = {}
        local_profile = None
        with ThreadPoolExecutor(
            max_workers=4, thread_name_prefix="tmux-observer-direct"
        ) as executor:
            futures = {
                host.host_id: executor.submit(
                    self.remote,
                    host,
                    mesh.policy,
                    revision,
                    deadline=deadline,
                    panes=panes,
                    option_names=option_names,
                )
                for host in selected
                if not host.local
            }
            for host in selected:
                if host.local:
                    from tmux_observer.collector import Collector

                    native = self.local or Collector(host.host_id)
                    value = native.collect(
                        panes=panes,
                        option_names=option_names,
                        budget_ms=max(1, min(2000, deadline - boottime_ms())),
                    )
                    rows[host.host_id] = observation_row(host, value)
                    if with_viewers:
                        from tmux_observer.attachment_collector import AttachmentCollector

                        local_profile = AttachmentCollector(native).sample(value, deadline)
            for host in selected:
                if not host.local:
                    rows[host.host_id] = futures[host.host_id].result()
        if boottime_ms() >= deadline:
            raise ContractError("operation_failed", "fresh fleet deadline exceeded")
        response = {
            "schemaVersion": 1,
            "generatedAt": time.time_ns() // 1000000,
            "meshRevision": revision,
            "hosts": [rows[host.host_id] for host in selected],
        }
        if with_viewers:
            from ._fresh_desktop import enrich

            response = enrich(
                response,
                endpoint=mesh.local_host.host_id if mesh else hosts[0].host_id,
                executable=mesh.policy.executable if mesh else None,
                profile=local_profile,
                deadline=min(deadline, boottime_ms() + 2000),
                config=desktop_config,
            )
        # The frozen Tmux Session v1 text type is nonempty, including option
        # values. The released CLI rejects these at its output boundary too.
        # Keep core observation values intact; never collapse an empty option
        # into absence or emit a malformed legacy success document.
        if any(
            value == ""
            for row in response["hosts"]
            for session in row["sessions"]
            for value in session.get("options", {}).values()
        ):
            raise ContractError(
                "operation_failed",
                "requested option values cannot be represented by Tmux Session v1",
            )
        encode_document(response)  # Preserve the released whole-response byte bound.
        return response
