"""Released portable SDK checks supplement Observer's native acceptance."""

import unittest

from mesh_plus.testing import network_suite, profile_suite, run_suite
from mesh_plus.testing.ssh import ssh_suite

from tmux_observer.mesh_profile import TmuxMeshProfile, TmuxMeshStateCodec


def make_profile(domain):
    if domain != "tmux":
        raise ValueError("unsupported domain")
    return TmuxMeshProfile()


class PortableConformanceTests(unittest.TestCase):
    def assert_suite(self, suite, expected):
        report = run_suite(suite, domain="tmux")
        self.assertTrue(report["ok"], report)
        self.assertEqual(report["testsRun"], expected)
        self.assertTrue(all(case["status"] == "passed" for case in report["cases"]))

    def test_independent_profile_oracle(self):
        self.assert_suite(profile_suite(make_profile, domain="tmux"), 6)

    def test_owned_ipc_and_remote_proof_transitions(self):
        self.assert_suite(network_suite(make_profile, domain="tmux"), 10)

    def test_owned_ssh_carriage(self):
        self.assert_suite(ssh_suite(make_profile, domain="tmux"), 1)

    def test_independent_oracle_rejects_dropped_receipts(self):
        class BrokenCodec(TmuxMeshStateCodec):
            def record_receipts(self, record, state):
                return ()

        class BrokenProfile(TmuxMeshProfile):
            def bind(self, host, source):
                return BrokenCodec(host, source)

        report = run_suite(
            profile_suite(lambda _domain: BrokenProfile(), domain="tmux"), domain="tmux"
        )
        self.assertFalse(report["ok"], report)
        self.assertGreater(report["failures"] + report["errors"], 0)
