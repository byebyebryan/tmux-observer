"""Bounds and escape cases at the optimized pre-parser boundary."""

import json
import unittest
from unittest.mock import patch

from tmux_observer import _wire as wire


class WirePreflightTests(unittest.TestCase):
    def test_repeated_strings_keep_occurrence_bounds_and_content_rejection(self):
        with patch.object(wire, "MAX_NODES", 4):
            wire.validate_tree(["same", "same", "same"])
            with self.assertRaises(wire.WireError):
                wire.validate_tree(["same"] * 4)
        for value in ("bad\n", "\ud800", "x" * (wire.STRING_LIMIT + 1)):
            with self.subTest(value=value[:10]), self.assertRaises(wire.WireError):
                wire.validate_tree(["same", "same", value, value])
        with patch.object(wire, "MAX_DEPTH", 2), self.assertRaises(wire.WireError):
            wire.validate_tree(["same", [[["same"]]]])

    def test_escaped_structural_characters_and_unicode_are_not_container_tokens(self):
        value = [r"\"{}[]", '"\\[]{}', "α界🐟", "\\" * 16000]
        self.assertEqual(wire.decode_document(wire.encode_document(value)), value)
        encoded = b'["\\u005b\\u007b", "\\ud83d\\udc1f"]\n'
        self.assertEqual(wire.decode_document(encoded), ["[{", "🐟"])

    def test_nesting_and_node_limits_precede_container_parser_construction(self):
        for raw, limits in (
            (b'[[["[]{}"]]]\n', {"MAX_DEPTH": 2}),
            (b'{"a":0,"b":1}\n', {"MAX_NODES": 4}),
            (b"[true,false,null,1.2,-3]\n", {"MAX_NODES": 5}),
        ):
            with (
                self.subTest(raw=raw),
                patch.multiple(wire, **limits),
                patch.object(
                    wire.json, "JSONDecoder", side_effect=AssertionError("parser must not run")
                ) as parser,
            ):
                with self.assertRaises(wire.WireError):
                    wire.decode_document(raw)
                parser.assert_not_called()
        raw = b"[" * wire.MAX_DEPTH + b'"[]{}"' + b"]" * wire.MAX_DEPTH + b"\n"
        self.assertIsInstance(wire.decode_document(raw), list)

    def test_malformed_escapes_duplicate_decoded_keys_and_wire_values_still_fail(self):
        for raw in (
            b'"unterminated\\"\n',
            b'"\\q"\n',
            b'{"x":1,"\\u0078":2}\n',
            b'"\\ud800"\n',
            b"[1e999]\n",
            b"[truefalse]\n",
            b"[0 1]\n",
            (json.dumps("a" * (wire.STRING_LIMIT + 1)) + "\n").encode(),
        ):
            with self.subTest(raw=raw[:60]), self.assertRaises(wire.WireError):
                wire.decode_document(raw)


if __name__ == "__main__":
    unittest.main()
