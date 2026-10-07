"""Command entry point. Operations are added only with their accepted producer."""

import argparse
import sys

from . import __version__


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tmux-observer")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command")
    collect = commands.add_parser("collect", help="fresh passive local default-server read")
    collect.add_argument("--host-id", required=True, help="fixed logical owner ID")
    collect.add_argument("--panes", action="store_true")
    collect.add_argument(
        "--option", action="append", default=[], help="explicit session user option"
    )
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    from .collector import Collector
    from .public import OBSERVATION_PROTOCOL, encode_document

    try:
        value = Collector(args.host_id).collect(panes=args.panes, option_names=args.option)
    except (ValueError, OSError, AttributeError):
        value = {
            "protocol": OBSERVATION_PROTOCOL,
            "schemaVersion": 1,
            "kind": "operation_error",
            "error": {
                "code": "invalid_context",
                "message": "invalid or unsupported local collection context",
            },
        }
    sys.stdout.buffer.write(encode_document(value))
    return 0 if value.get("sample", {}).get("coverage") == "complete" else 1
