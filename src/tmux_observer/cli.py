"""Command entry point. Operations are added only with their accepted producer."""

import argparse
import signal
import sys
import uuid
from pathlib import Path

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
    owner = commands.add_parser("owner", help="run one shared passive local publisher")
    owner.add_argument("--host-id", required=True, help="fixed logical owner ID")
    owner.add_argument("--socket", type=Path, help="private IPC endpoint, not a native tmux socket")
    for operation in (
        "status",
        "snapshot",
        "probe",
        "watch",
        "bridge",
        "refresh",
        "refresh_status",
    ):
        command = commands.add_parser(
            operation,
            help="explicit prepared owner read"
            if operation != "bridge"
            else "owner-only SSH stdio watch/request bridge",
        )
        command.add_argument("--expected-host", required=True)
        command.add_argument(
            "--socket", type=Path, help="private publisher endpoint; never auto-started"
        )
        if operation in ("refresh", "refresh_status"):
            command.add_argument("--publisher-id", required=operation == "refresh_status")
        if operation == "refresh_status":
            command.add_argument("--ticket-id", required=True)
        if operation in ("watch", "bridge"):
            command.add_argument("--request-id", help="bounded initial watch nonce")
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    from .public import OBSERVATION_PROTOCOL, SERVICE_PROTOCOL, encode_document

    if args.command in ("watch", "bridge"):
        from ._stream import stream_owner

        return stream_owner(
            args.expected_host,
            path=args.socket,
            bridge=args.command == "bridge",
            request_id=args.request_id,
        )
    if args.command == "owner":
        from ._ipc import IPCError
        from .owner import OwnerPublisher

        try:
            publisher = OwnerPublisher(args.host_id, path=args.socket)
            for selected in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
                signal.signal(selected, lambda _signal, _frame: publisher.stop())
            publisher.run()
            return 0
        except (IPCError, OSError, ValueError, AttributeError) as error:
            print(
                "tmux-observer owner unavailable: "
                + (error.code if isinstance(error, IPCError) else "invalid_context"),
                file=sys.stderr,
            )
            return 1
    if args.command != "collect":
        from ._ipc import IPCError, exchange

        try:
            request = {
                "protocol": SERVICE_PROTOCOL,
                "schemaVersion": 1,
                "operation": args.command,
                "requestId": uuid.uuid4().hex,
                "expectedHost": args.expected_host,
            }
            if args.command == "refresh":
                request["sources"] = [{"hostId": args.expected_host, "source": "owner"}]
            if args.command in ("refresh", "refresh_status") and args.publisher_id:
                request["publisherId"] = args.publisher_id
            if args.command == "refresh_status":
                request["ticketId"] = args.ticket_id
            value = exchange(request, path=args.socket)
        except (IPCError, OSError, ValueError, AttributeError) as error:
            value = {
                "protocol": SERVICE_PROTOCOL,
                "schemaVersion": 1,
                "kind": "operation_error",
                "error": {
                    "code": error.code if isinstance(error, IPCError) else "invalid_context",
                    "message": "prepared owner read is unavailable",
                },
            }
        sys.stdout.buffer.write(encode_document(value, limit=1064960))
        return 1 if value.get("kind") == "operation_error" else 0
    from .collector import Collector

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
