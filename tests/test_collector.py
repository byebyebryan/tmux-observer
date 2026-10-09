"""Native-boundary simulations. Real tmux acceptance is a separate script."""

import unittest
from unittest.mock import patch

from tmux_observer._process import Completed, ProcessError, ReadRunner, allowed_read
from tmux_observer.collector import FIELDS, GENERATION, PANES, PENDING, Collector, format_fields


class NativeFixture:
    def __init__(self):
        self.calls = []
        self.generation = "/tmp/fixture/default\t100\t200\n"
        self.row = "$1\t101\tfixture\t102\t\t0\t1\t/tmp\tfixture\t/tmp\n"
        self.final = "$1\t101\n"
        self.before = None
        self.fast = True

    def __call__(self, args, deadline):
        self.calls.append((args, deadline))
        if ";" in args:
            output, start = "", 0
            for end in [i for i, value in enumerate(args) if value == ";"] + [len(args)]:
                value = self(args[start:end], deadline)
                if value.returncode:
                    return value
                output += value.stdout
                start = end + 1
            return Completed(0, output, "")
        if self.before is not None:
            special = self.before(args)
            if special is not None:
                return special
        if args == ["display-message", "-p", format_fields(GENERATION)]:
            return Completed(0, self.generation if self.fast else "\t\t\n", "")
        if args == ["list-sessions", "-F", format_fields(FIELDS)]:
            return Completed(0, self.row, "")
        if args == ["list-sessions", "-F", format_fields((*FIELDS[:2], *GENERATION))]:
            return Completed(
                0, "".join(row + "\t" + self.generation for row in self.final.splitlines()), ""
            )
        if args[0] == "show-options":
            return Completed(0, "@empty ''\n" if args[-1] == "@empty" else "", "")
        if args == ["list-panes", "-a", "-F", format_fields(PANES)]:
            return Completed(0, "$1\t%1\t202\t/tmp\tsleep\n", "")
        if args == ["list-sessions", "-F", "#{session_id}"]:
            return Completed(0, "$1\n", "")
        if args[0] == "display-message":
            name = args[-1][2:-1]
            rows = self.row.splitlines()
            row = next(
                (row for row in rows if len(args) == 5 and row.split("\t")[0] == args[3]), rows[0]
            )
            values = dict(zip(FIELDS, row.split("\t"), strict=True))
            values.update(socket_path="/tmp/fixture/default", start_time="100", pid="200")
            return Completed(0, values[name] + "\n", "")
        raise AssertionError(args)


class CollectorTests(unittest.TestCase):
    def test_minimal_read_profile_and_single_deadline(self):
        native = NativeFixture()
        value = Collector("fixture", runner=native).collect()
        self.assertEqual(value["sample"]["coverage"], "complete")
        self.assertEqual(value["sessions"][0]["sessionId"], "$1")
        self.assertEqual(len({deadline for _, deadline in native.calls}), 1)
        self.assertEqual(
            [args[-1] for args, _ in native.calls if args[0] == "show-options"], [PENDING]
        )
        self.assertTrue(all(allowed_read(args) for args, _ in native.calls))

    def test_explicit_options_and_panes(self):
        native = NativeFixture()
        value = Collector("fixture", runner=native).collect(
            panes=True, option_names=["@empty", "@absent", "@empty"]
        )
        self.assertEqual(value["sessions"][0]["options"], {"@empty": "", "@absent": None})
        self.assertEqual(value["sessions"][0]["panes"][0]["paneId"], "%1")

    def test_generation_race_retries_once(self):
        native = NativeFixture()
        count = 0

        def change(args):
            nonlocal count
            if args == ["list-sessions", "-F", format_fields((*FIELDS[:2], *GENERATION))]:
                count += 1
                if count == 1:
                    native.generation = "/tmp/fixture/default\t103\t204\n"

        native.before = change
        value = Collector("fixture", runner=native).collect()
        self.assertEqual(value["sample"]["coverage"], "complete")
        self.assertEqual(count, 2)
        self.assertEqual(value["serverGeneration"], "tmux-v1:103:204:/tmp/fixture/default")
        self.assertEqual(len({deadline for _, deadline in native.calls}), 1)

    def test_nonempty_fast_final_bracket_checks_generation_with_one_native_read(self):
        native = NativeFixture()
        value = Collector("fixture", runner=native).collect()
        self.assertEqual(value["sample"]["coverage"], "complete")
        self.assertEqual(sum(args[0] == "display-message" for args, _ in native.calls), 1)
        self.assertEqual(sum(args[0] == "list-sessions" for args, _ in native.calls), 2)

    def test_live_empty_fast_final_bracket_still_probes_native_generation(self):
        native = NativeFixture()
        native.row = native.final = ""
        value = Collector("fixture", runner=native).collect()
        self.assertEqual(value["sample"]["coverage"], "complete")
        self.assertIsNotNone(value["serverGeneration"])
        self.assertEqual(value["sessions"], [])
        self.assertEqual(sum(args[0] == "display-message" for args, _ in native.calls), 2)

    def test_mixed_final_generations_cannot_publish_partial_native_rows(self):
        native = NativeFixture()
        native.row += native.row.replace("$1\t", "$2\t", 1)
        native.before = lambda args: (
            Completed(
                0,
                "$1\t101\t/tmp/fixture/default\t100\t200\n$2\t101\t/tmp/fixture/default\t100\t201\n",
                "",
            )
            if args == ["list-sessions", "-F", format_fields((*FIELDS[:2], *GENERATION))]
            else None
        )
        value = Collector("fixture", runner=native).collect()
        self.assertEqual(value["sample"]["error"]["code"], "unstable_source")
        self.assertEqual(value["sessions"], [])

    def test_persistent_reference_conflict_is_failed_not_partial_rows(self):
        for final in ("$1\t999\n", "$2\t101\n", ""):
            native = NativeFixture()
            native.final = final
            value = Collector("fixture", runner=native).collect()
            self.assertEqual(value["sample"]["error"]["code"], "unstable_source")
            self.assertEqual(value["sessions"], [])
            self.assertIsNone(value["serverGeneration"])

    def test_no_server_classes_do_not_include_permission_failures(self):
        for message, expected in (
            ("no server running on /tmp/fixture/default", "complete"),
            ("error connecting to /tmp/fixture/default (No such file or directory)", "complete"),
            ("error connecting to /tmp/fixture/default (Connection refused)", "complete"),
            ("error connecting to /tmp/fixture/default (Permission denied)", "failed"),
            ("failed to connect to server", "failed"),
        ):
            native = lambda _args, _deadline, diagnostic=message: Completed(
                1, "", diagnostic + "\n"
            )
            value = Collector("fixture", runner=native).collect()
            self.assertEqual(value["sample"]["coverage"], expected, message)
            self.assertEqual(value["sessions"], [])

    def test_disappearance_mid_batch_is_retryable(self):
        native = NativeFixture()

        def vanish(args):
            if args[0] == "show-options":
                return Completed(1, "", "no server running on /tmp/fixture/default\n")
            return None

        native.before = vanish
        value = Collector("fixture", runner=native).collect()
        self.assertEqual(value["sample"]["error"]["code"], "unstable_source")
        self.assertEqual(sum(args[0] == "show-options" for args, _ in native.calls), 2)

    def test_legacy_collection_is_bracketed(self):
        native = NativeFixture()
        native.fast = False
        value = Collector("fixture", runner=native).collect()
        self.assertEqual(value["sample"]["coverage"], "complete")
        self.assertEqual(value["sessions"][0]["name"], "fixture")
        self.assertEqual(sum(args[-1] == "#{socket_path}" for args, _ in native.calls), 2)
        self.assertEqual(sum(args[-1] == "#{session_created}" for args, _ in native.calls), 2)

    def test_malformed_numeric_metadata_does_not_become_unknown(self):
        native = NativeFixture()
        native.row = native.row.replace("\t0\t", "\tnot-a-count\t")
        value = Collector("fixture", runner=native).collect()
        self.assertEqual(value["sample"]["coverage"], "failed")
        self.assertEqual(value["sample"]["error"]["code"], "malformed_metadata")

    def test_expired_budget_and_missing_cli(self):
        native = NativeFixture()
        with patch("tmux_observer.collector.boottime_ms", side_effect=[100, 2100, 2100]):
            value = Collector("fixture", runner=native).collect()
        self.assertEqual(value["sample"]["error"]["code"], "deadline")

        def missing(_args, _deadline):
            raise ProcessError("tmux_missing", "tmux unavailable")

        value = Collector("fixture", runner=missing).collect()
        self.assertEqual(value["sample"]["coverage"], "unsupported")

    def test_default_environment_is_frozen_and_ambient_socket_ignored(self):
        with patch.dict(
            "os.environ", {"TMUX": "/tmp/other,1,0", "TMUX_PANE": "%1", "TMUX_TMPDIR": "/tmp/owned"}
        ):
            runner = ReadRunner()
        self.assertEqual(runner.prefix, ("tmux", "-u", "-L", "default"))
        self.assertNotIn("TMUX", runner.env)
        self.assertNotIn("TMUX_PANE", runner.env)
        self.assertEqual(runner.env["TMUX_TMPDIR"], "/tmp/owned")

    def test_command_allowlist_rejects_writes_and_format_jobs(self):
        for args in (
            ["new-session"],
            ["display-message", "-p", "#(touch /tmp/forbidden)"],
            ["show-options", "-g"],
            ["list-sessions", "-F", "#{session_id}", ";", "kill-server"],
            ["display-message", "-p", "-t", "session-name", "#{session_id}"],
        ):
            self.assertFalse(allowed_read(args))
            with self.assertRaises(ValueError):
                ReadRunner()(args, 2**62)
