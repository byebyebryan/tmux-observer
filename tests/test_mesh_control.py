"""Control acknowledgements cannot adopt facts or complete after their deadline."""

import json
import os
import unittest
from concurrent.futures import Future
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from tmux_observer._clock import boottime_ms
from tmux_observer._tickets import TicketStore
from tmux_observer.delivery import SERVICE_PROTOCOL
from tmux_observer_client._mesh_control import OwnerControl


class MeshControlTests(unittest.TestCase):
    def test_delayed_ack_after_queued_execution_is_rejected_without_owner_mutation(self):
        frame = json.loads(
            (
                Path(__file__).resolve().parent.parent / "contracts/service-v1/fixtures/ready.json"
            ).read_text()
        )
        host = frame["source"]["hostId"]
        frame["source"]["uid"] = os.getuid()
        frame["snapshot"]["source"]["uid"] = os.getuid()
        frame["kind"] = "refresh_result"
        frame["requestId"] = "controlled-refresh"
        frame["ticket"] = TicketStore(frame["publisherId"]).admit(
            [{"hostId": host, "source": "owner"}],
            100,
            minimum={(host, "owner"): 2},
        )
        state = SimpleNamespace(
            host_id=host,
            local_clock=frame["clock"],
            epoch=1,
            selected_route=None,
            expiry=10100,
            scope=(
                frame["publisherId"],
                os.getuid(),
                "default",
                frame["clock"]["bootId"],
                frame["clock"]["timeNamespace"],
            ),
        )
        future = Future()
        future.set_result(frame)
        executor = Mock()
        executor.submit.return_value = future
        accepted, failed = Mock(), Mock()
        control = OwnerControl(state, executor, on_frame=accepted, on_error=failed)
        control.send(
            {
                "protocol": SERVICE_PROTOCOL,
                "schemaVersion": 1,
                "operation": "refresh",
                "expectedHost": host,
                "publisherId": frame["publisherId"],
                "requestId": frame["requestId"],
                "sources": [{"hostId": host, "source": "owner"}],
            },
            boottime_ms() - 3000,
        )
        control.poll(boottime_ms())
        accepted.assert_not_called()
        self.assertEqual(failed.call_args.args[1]["error"]["code"], "deadline")
        self.assertEqual(state.expiry, 10100)
