"""Read-chain safety and annotation scope failures; installed proof is separate."""

import unittest

from tmux_observer._process import READ_COMMAND_LIMIT, ProcessError, allowed_read
from tmux_observer.annotations import PENDING, PlusPendingProfile


class CoalescedReadTests(unittest.TestCase):
    def test_every_chained_command_must_be_a_bounded_read(self):
        read = ["list-clients", "-F", "#{client_pid}"]
        self.assertTrue(allowed_read([*read, ";", *read]))
        for other in (
            ["kill-server"],
            ["run-shell", "true"],
            ["display-message", "-p", "#{pane_current_command}; kill-server"],
            ["show-options", "-q", "-t", "$1", "@x;kill-server"],
            [],
        ):
            self.assertFalse(allowed_read([*read, ";", *other]))
            self.assertFalse(allowed_read([*other, ";", *read]))
        batch = [part for _ in range(READ_COMMAND_LIMIT) for part in [*read, ";"]][:-1]
        self.assertTrue(allowed_read(batch))
        self.assertFalse(allowed_read([*batch, ";", *read]))

    def test_annotations_preserve_present_empty_absent_and_quoted_values(self):
        captured = []

        def read(args, deadline, **_kwargs):
            self.assertTrue(allowed_read(args))
            captured.append((args, deadline))
            return "$1\n" + PENDING + " ''\n$2\n$3\n" + PENDING + " 'pending value'"

        result = PlusPendingProfile.sample_pending(read, ["$1", "$2", "$3"], 999)
        self.assertEqual(result, {"$1": (True, {}), "$2": (False, {}), "$3": (True, {})})
        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0][1], 999)

    def test_missing_duplicate_foreign_or_malformed_annotation_scope_fails(self):
        for output in (
            "$1\n",
            "$1\n$1\n",
            "$9\n$2\n",
            "$1\n" + PENDING + " 'unterminated\n$2\n",
            "$1\n$2\nextra",
        ):
            with self.subTest(output=output), self.assertRaises(ProcessError):
                PlusPendingProfile.sample_pending(
                    lambda *_args, selected=output, **_kwargs: selected, ["$1", "$2"], 999
                )

    def test_large_rosters_keep_the_chain_limit_and_same_deadline(self):
        captured = []

        def read(args, deadline, **_kwargs):
            self.assertTrue(allowed_read(args))
            captured.append((args, deadline))
            return "\n".join(
                args[i + 3] for i, value in enumerate(args) if value == "display-message"
            )

        identifiers = ["$" + str(i) for i in range(65)]
        result = PlusPendingProfile.sample_pending(read, identifiers, 999)
        self.assertEqual(set(result), set(identifiers))
        self.assertEqual(len(captured), 3)
        self.assertTrue(all(deadline == 999 for _args, deadline in captured))


if __name__ == "__main__":
    unittest.main()
