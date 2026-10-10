"""Owned default-server namespaces and real localhost SSH; ordinary state is untouched.

SSH isolation follows Mesh Plus tests/ssh_fixture.py (MIT, Copyright Bryan 2026).
"""

import json
import os
import pwd
import shlex
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from tmux_observer._ipc import IPCError, exchange
from tmux_observer.delivery import SERVICE_PROTOCOL


class NativeFixture:
    def __init__(self):
        self.temporary = tempfile.TemporaryDirectory(prefix=".tmux-mesh-", dir=Path.home())
        self.root = Path(self.temporary.name)
        self.processes = []
        self.local = self.root / "local"
        self.remote = self.root / "remote"
        self.bin = self.root / "bin"
        for path in (self.local, self.remote, self.bin):
            path.mkdir(mode=0o700)

    def env(self, role):
        environment = {**os.environ, "TMUX_TMPDIR": str(getattr(self, role))}
        environment.pop("TMUX", None)
        environment.pop("TMUX_PANE", None)
        return environment

    def native(self, role, *arguments, ok=True):
        result = subprocess.run(
            ["tmux", "-f", "/dev/null", "-L", "default", *arguments],
            env=self.env(role),
            capture_output=True,
            timeout=3,
            check=False,
        )
        if ok and result.returncode != 0:
            raise RuntimeError("owned native command failed: " + result.stderr.decode()[:512])
        return result.stdout

    def start_owner(self, role):
        path = getattr(self, role) / "owner.sock"
        host = "fixture-" + role
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "tmux_observer",
                "owner",
                "--host-id",
                host,
                "--socket",
                str(path),
            ],
            env=self.env(role),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        self.processes.append(process)
        end = time.monotonic() + 3
        while time.monotonic() < end:
            if process.poll() is not None:
                raise RuntimeError("owned Observer startup failed")
            try:
                frame = exchange(
                    {
                        "protocol": SERVICE_PROTOCOL,
                        "schemaVersion": 1,
                        "requestId": "native-fixture",
                        "operation": "snapshot",
                        "expectedHost": host,
                    },
                    path=path,
                )
                if frame["receipt"]["state"] == "ready":
                    return process, frame
            except IPCError:
                pass
            time.sleep(0.025)
        raise RuntimeError("owned Observer did not become ready")

    def write(self, path, content, *, executable=False):
        path.write_text(content)
        path.chmod(0o700 if executable else 0o600)

    def start_ssh(self):
        for name in ("host-key", "client-key"):
            subprocess.run(
                ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(self.root / name)],
                check=True,
                capture_output=True,
                timeout=5,
            )
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        user = pwd.getpwuid(os.getuid()).pw_name
        config = self.root / "sources.toml"
        self.write(
            config,
            'version = 1\nhost = "fixture-remote"\n[sources.tmux_default]\n'
            'domain = "tmux"\nsocket = ' + json.dumps(str(self.remote / "owner.sock")) + "\n",
        )
        self.write(
            self.bin / "mesh-plus",
            "#!/bin/sh\nexec "
            + shlex.join([sys.executable, "-m", "mesh_plus.cli"])
            + ' "$@" --config '
            + shlex.quote(str(config))
            + " 2>"
            + shlex.quote(str(self.root / "mesh.log"))
            + "\n",
            executable=True,
        )
        self.write(
            self.bin / "tmux-observer",
            "#!/bin/sh\nexec "
            + shlex.join([sys.executable, "-m", "tmux_observer"])
            + ' "$@" --socket '
            + shlex.quote(str(self.remote / "owner.sock"))
            + "\n",
            executable=True,
        )
        # The disposable key can only reach this loopback server. Its command
        # uses the same POSIX shell semantics as the production SSH transport.
        forced = self.root / "forced.py"
        self.write(
            forced,
            "import os\n"
            + "os.environ['PATH'] = "
            + repr(str(self.bin) + ":" + os.environ["PATH"])
            + "\n"
            + "os.environ['PYTHONPATH'] = "
            + repr(os.environ.get("PYTHONPATH", ""))
            + "\n"
            + "os.execv('/bin/sh', ['sh', '-c', os.environ['SSH_ORIGINAL_COMMAND']])\n",
        )
        authorized = self.root / "authorized_keys"
        self.write(
            authorized,
            "restrict,command="
            + json.dumps(shlex.join([sys.executable, str(forced)]))
            + " "
            + (self.root / "client-key.pub").read_text(),
        )
        daemon_config = self.root / "sshd.conf"
        self.write(
            daemon_config,
            f"Port {port}\nListenAddress 127.0.0.1\nHostKey {self.root / 'host-key'}\n"
            f"PidFile {self.root / 'sshd.pid'}\nAuthorizedKeysFile {authorized}\nAllowUsers {user}\n"
            "UsePAM no\nPasswordAuthentication no\nKbdInteractiveAuthentication no\nPubkeyAuthentication yes\n"
            "StrictModes yes\nPermitRootLogin no\nAllowTcpForwarding no\nAllowAgentForwarding no\n"
            "X11Forwarding no\nPermitTTY no\nLogLevel ERROR\n",
        )
        key = (self.root / "host-key.pub").read_text().split()
        self.write(self.root / "known_hosts", f"[127.0.0.1]:{port} {key[0]} {key[1]}\n")
        client_config = self.root / "ssh.conf"
        self.write(
            client_config,
            f"Host fixture-remote\n HostName 127.0.0.1\n Port {port}\n User {user}\n"
            f" IdentityFile {self.root / 'client-key'}\n UserKnownHostsFile {self.root / 'known_hosts'}\n"
            " GlobalKnownHostsFile /dev/null\n IdentitiesOnly yes\n IdentityAgent none\n",
        )
        self.write(
            self.bin / "ssh",
            "#!/bin/sh\nexec "
            + shlex.join([shutil.which("ssh"), "-F", str(client_config)])
            + ' "$@"\n',
            executable=True,
        )
        daemon = subprocess.Popen(
            [
                shutil.which("sshd"),
                "-D",
                "-f",
                str(daemon_config),
                "-E",
                str(self.root / "sshd.log"),
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.processes.append(daemon)
        end = time.monotonic() + 3
        while time.monotonic() < end:
            if daemon.poll() is not None:
                raise RuntimeError("owned localhost sshd startup failed")
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.1):
                    return
            except OSError:
                time.sleep(0.025)
        raise RuntimeError("owned localhost sshd did not become ready")

    def close(self):
        for process in reversed(self.processes):
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(3)
            if process.stderr is not None:
                process.stderr.close()
        for role in ("local", "remote"):
            self.native(role, "kill-server", ok=False)
        self.temporary.cleanup()
