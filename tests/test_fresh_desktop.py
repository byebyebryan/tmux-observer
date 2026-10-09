"""Fresh optional inputs keep scope/leases separate and sampling explicit."""

import copy
import unittest
from unittest.mock import Mock, patch

from tests.test_attachment_collector import AssociationFixture
from tmux_observer._clock import boottime_ms
from tmux_observer.attachment_collector import AttachmentCollector
from tmux_observer.collector import Collector
from tmux_observer_client._desktop_types import LocalViewerObservation, ViewerObservationBatch
from tmux_observer_client._errors import ContractError
from tmux_observer_client._fresh_desktop import FreshClients, enrich
from tmux_observer_client.direct import DirectInventory, observation_row
from tmux_observer_client.mesh import MeshHost, MeshPolicy, MeshSnapshot


class FreshDesktopTests(unittest.TestCase):
    def setUp(self):
        self.native = AssociationFixture()
        self.collector = Collector("fixture", runner=self.native)
        self.observation = self.collector.collect()
        self.profile = AttachmentCollector(
            self.collector, process_identity=lambda *_args: 500
        ).sample(self.observation, boottime_ms() + 2000)
        self.host = MeshHost("fixture", "Fixture", True, (), ())
        self.row = observation_row(self.host, self.observation)

    def test_complete_profile_scope_and_incarnation_are_consumed_without_collection(self):
        clients = FreshClients(self.row, self.profile, boottime_ms() + 2000)
        self.assertEqual(clients.client_pids_by_session(), {"$1": {123}})
        self.assertEqual(clients.client_incarnations[123], (self.profile["source"]["uid"], 500))
        calls = len(self.native.calls)
        clients.client_pids_by_session()
        self.assertEqual(len(self.native.calls), calls)

    def test_missing_expired_foreign_or_changed_profile_never_proves_local_join(self):
        for changed in ("missing", "uid", "clock", "namespace", "ref", "expiry"):
            profile = copy.deepcopy(self.profile)
            row = copy.deepcopy(self.row)
            now = boottime_ms()
            if changed == "missing":
                profile = None
            elif changed == "uid":
                profile["source"]["uid"] += 1
            elif changed == "clock":
                profile["clock"]["bootId"] = "00000000-0000-0000-0000-000000000000"
            elif changed == "namespace":
                profile["pidNamespace"] = "pid:42"
            elif changed == "ref":
                row["sessions"][0]["createdAt"] += 1
            elif changed == "expiry":
                now = profile["sample"]["startedAt"] + 10000
            with (
                self.subTest(changed=changed),
                patch("tmux_observer_client._fresh_desktop.boottime_ms", return_value=now),
                self.assertRaises((ContractError, ValueError)),
            ):
                FreshClients(row, profile, now + 2000).client_pids_by_session()

    def test_explicit_direct_job_samples_profile_once_and_adapter_receives_no_collector(self):
        mesh = Mock()
        mesh.load.return_value = MeshSnapshot(
            "sha256:" + "a" * 64, "fixture", MeshPolicy("ssh", 1, 1, 30), (self.host,)
        )
        with (
            patch.object(AttachmentCollector, "sample", return_value=self.profile) as sample,
            patch("tmux_observer_client._fresh_desktop.observe_local_viewers") as scan,
        ):

            def observe(targets, _config, *, local_tmux, deadline):
                self.assertIsInstance(local_tmux, FreshClients)
                self.assertEqual(local_tmux.client_pids_by_session(), {"$1": {123}})
                return ViewerObservationBatch(
                    boottime_ms(),
                    {
                        target.session.reference: LocalViewerObservation(
                            "open", "confirmed", "native_client"
                        )
                        for target in targets
                    },
                )

            scan.side_effect = observe
            result = DirectInventory(mesh=mesh, local=self.collector).inventory(with_viewers=True)
        self.assertEqual(sample.call_count, 1)
        self.assertEqual(mesh.load.call_count, 1)
        self.assertEqual(result["hosts"][0]["sessions"][0]["localViewer"]["state"], "open")

    def test_adapter_failure_is_display_uncertainty_without_poisoning_native_row(self):
        response = {"hosts": [copy.deepcopy(self.row)]}
        with patch("tmux_observer_client._desktop_scan._niri_windows", return_value=[]):
            result = enrich(
                response,
                endpoint="fixture",
                executable=None,
                profile=None,
                deadline=boottime_ms() + 2000,
            )
        row = result["hosts"][0]
        self.assertEqual(row["status"], "ok")
        self.assertEqual(row["sessions"][0]["localViewer"]["state"], "unknown")


if __name__ == "__main__":
    unittest.main()
