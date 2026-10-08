"""Owned live stdio relay tests; no ordinary SSH connection is created."""

import json
import sys
import tempfile
import time
import unittest
from pathlib import Path

from tmux_observer._clock import boottime_ms
from tmux_observer.public import SERVICE_PROTOCOL
from tmux_observer_client.mesh import MeshHost, MeshPolicy, MeshRoute
from tmux_observer_client.ssh import RemoteConnection

PROGRAM = """#!INTERPRETER
import copy,json,os,re,sys,time
frame=json.load(open(FIXTURE))
nonce=re.search(r"--request-id ([a-f0-9]{32})",sys.argv[-1])[1]
print("\\x1eTMUX_OBSERVER_REACHED_V1:"+nonce+"\\x1f",file=sys.stderr,flush=True)
frame.update(kind="resync",requestId=nonce,sequence=0)
raw=json.dumps(frame,separators=(",",":")).encode()+b"\\n"
MODE
os.write(1,raw[:17]); time.sleep(.03); os.write(1,raw[17:])
for line in sys.stdin.buffer:
    request=json.loads(line)
    REPLY
    frame.update(kind="status",requestId=request["requestId"],sequence=frame["sequence"]+1)
    print(json.dumps(frame,separators=(",",":")),flush=True)
"""


class SSHTests(unittest.TestCase):
    def connection(self, temporary, mode="", *, reply="", on_error=None):
        root = Path(__file__).resolve().parent.parent
        fixture = root / "contracts/service-v1/fixtures/ready.json"
        host_id = json.loads(fixture.read_text())["source"]["hostId"]
        executable = Path(temporary) / "owned-ssh"
        executable.write_text(
            PROGRAM.replace("INTERPRETER", sys.executable)
            .replace("FIXTURE", repr(str(fixture)))
            .replace("MODE", mode)
            .replace("REPLY", reply)
        )
        executable.chmod(0o700)
        host = MeshHost(host_id, host_id, False, (), ())
        route = MeshRoute("fixture-destination", 0, None, None)
        policy = MeshPolicy(str(executable), 2, 1, 300)
        connection = RemoteConnection(host, route, policy, boottime_ms(), on_error=on_error)
        self.addCleanup(connection.close)
        return connection

    def pump(self, connection, condition, budget=3):
        deadline = time.monotonic() + budget
        while time.monotonic() < deadline and not condition():
            connection.poll(boottime_ms())
            time.sleep(0.005)
        self.assertTrue(condition(), connection.state.error)

    def test_one_owned_connection_handshake_fragmentation_and_proof(self):
        with tempfile.TemporaryDirectory(prefix="tmux-observer-ssh-relay-") as temporary:
            connection = self.connection(temporary)
            pid = connection.process.pid
            self.pump(connection, lambda: connection.state.expiry > boottime_ms())
            self.assertTrue(connection.reached)
            self.assertEqual(connection.process.pid, pid)
            self.assertEqual(connection.state.sequence, 1)
            self.assertEqual(
                connection.state.confirmed["requestId"], connection.state.proof["requestId"]
            )
            self.assertIsNone(connection.state.pending)
            connection.close()
            self.assertIsNotNone(connection.process.returncode)
            self.assertFalse(connection.incoming)

    def test_known_control_error_preserves_proof_but_unknown_error_is_fatal(self):
        reply = """if request["operation"]=="refresh":
        print(json.dumps({"protocol":"tmux-observer.service.v1","schemaVersion":1,
            "kind":"operation_error","requestId":request["requestId"],
            "error":{"code":"capacity","message":"full"}}),flush=True)
        continue"""
        for handled in (True, False):
            with (
                self.subTest(handled=handled),
                tempfile.TemporaryDirectory(prefix="tmux-observer-ssh-control-") as temporary,
            ):
                errors = []

                def error(_connection, value, _now, errors=errors, handled=handled):
                    errors.append(value)
                    return handled and value.get("requestId") == "known-control"

                connection = self.connection(temporary, reply=reply, on_error=error)
                self.pump(
                    connection, lambda selected=connection: selected.state.expiry > boottime_ms()
                )
                expiry = connection.state.expiry
                connection.send(
                    {
                        "protocol": SERVICE_PROTOCOL,
                        "schemaVersion": 1,
                        "operation": "refresh",
                        "requestId": "known-control",
                        "expectedHost": connection.state.host_id,
                        "publisherId": connection.state.scope[0],
                        "sources": [{"hostId": connection.state.host_id, "source": "owner"}],
                    },
                    boottime_ms(),
                )
                self.pump(connection, lambda selected=errors: bool(selected))
                self.assertEqual(connection.closed, not handled)
                self.assertEqual(connection.state.expiry, expiry if handled else 0)

    def test_trickled_frame_and_clock_jump_cannot_establish_membership(self):
        with tempfile.TemporaryDirectory(prefix="tmux-observer-ssh-trickle-") as temporary:
            connection = self.connection(
                temporary, "os.write(1,raw[:1]); time.sleep(10); sys.exit(0)"
            )
            self.pump(connection, lambda: connection.first_byte is not None)
            connection.poll(connection.first_byte + 2000)
            self.assertTrue(connection.closed)
            self.assertEqual(connection.state.expiry, 0)
            self.assertEqual(connection.state.error["code"], "deadline")

    def test_oversized_and_foreign_frames_fail_with_owned_child_reaped(self):
        cases = (
            "os.write(1,b'x'*1064961); time.sleep(10); sys.exit(0)",
            "frame['source']['hostId']='foreign'; raw=json.dumps(frame).encode()+b'\\n'",
        )
        for mode in cases:
            with (
                self.subTest(mode=mode),
                tempfile.TemporaryDirectory(prefix="tmux-observer-ssh-invalid-") as temporary,
            ):
                connection = self.connection(temporary, mode)
                self.pump(connection, lambda selected=connection: selected.closed)
                self.assertEqual(connection.state.expiry, 0)
                self.assertIsNotNone(connection.process.returncode)

    def test_silent_setup_expires_without_reaping_unrelated_processes(self):
        with tempfile.TemporaryDirectory(prefix="tmux-observer-ssh-silence-") as temporary:
            connection = self.connection(temporary, "time.sleep(10); sys.exit(0)")
            connection.poll(connection.state.handshake[1])
            self.assertTrue(connection.closed)
            self.assertEqual(connection.state.transport, "failed")
            self.assertEqual(connection.state.expiry, 0)
