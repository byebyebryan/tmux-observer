"""Explicit client operations; prepared access never falls back to collection."""

import argparse
import signal
import sys
from pathlib import Path

from tmux_observer._ipc import IPCError
from tmux_observer.native import FRAME_LIMIT, REQUEST_LIMIT, encode_document
from tmux_observer_client.contract import FLEET_PROTOCOL

from ._errors import ContractError


def prepared_arguments(parser):
    parser.add_argument(
        "--context-id", help="captured desktop context; defaults to this environment"
    )
    parser.add_argument("--expected-host", help="expected configured local owner ID")
    parser.add_argument("--publisher-id", help="expected fleet reader incarnation")
    parser.add_argument("--socket", type=Path, help="private fleet IPC endpoint")


def direct(args):
    from .direct import DirectInventory

    try:
        if any((args.context_id, args.expected_host, args.publisher_id, args.socket)):
            raise ContractError("invalid_input", "prepared scope flags require cached access")
        value = DirectInventory().inventory(
            requested_hosts=args.host,
            mesh_revision=args.mesh_revision,
            panes=args.panes,
            option_names=args.option,
        )
        sys.stdout.buffer.write(encode_document(value))
        return 0
    except (ContractError, OSError, ValueError) as error:
        # Direct diagnosis retains the released Tmux Session v1 failure envelope.
        value = (
            error.envelope()
            if isinstance(error, ContractError)
            else {
                "schemaVersion": 1,
                "ok": False,
                "error": {"code": "operation_failed", "message": "fresh fleet read failed"},
            }
        )
        sys.stdout.buffer.write(encode_document(value))
        return 1


def main(argv=None):
    parser = argparse.ArgumentParser(prog="tmux-observer-client")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("context", help="print the current captured desktop context ID")
    for operation in ("prepare-context", "start-context", "stop-context"):
        selected = commands.add_parser(operation, help="explicit per-desktop service " + operation)
        selected.add_argument("--json", action="store_true", required=True)
        if operation == "stop-context":
            selected.add_argument("--context-id")
        else:
            selected.add_argument("--host-id", required=True)
    fleet = commands.add_parser("fleet", help="explicitly run one prepared fleet publisher")
    fleet.add_argument("--host-id", required=True, help="fixed configured local owner ID")
    fleet.add_argument("--context-id")
    fleet.add_argument("--socket", type=Path)
    fleet.add_argument(
        "--transport",
        choices=("legacy", "mesh"),
        default="legacy",
        help="explicit cached-state backend; Mesh requires the mesh extra",
    )
    fleet.add_argument(
        "--mesh-source",
        default="tmux_default",
        help="fixed Mesh source selector configured on each owner host",
    )
    snapshot = commands.add_parser("snapshot")
    snapshot.add_argument("--access", choices=("direct", "cached"), required=True)
    snapshot.add_argument("--host", action="append", default=[])
    snapshot.add_argument("--mesh-revision")
    snapshot.add_argument("--panes", action="store_true")
    snapshot.add_argument("--option", action="append", default=[])
    snapshot.add_argument("--json", action="store_true", required=True)
    prepared_arguments(snapshot)
    for operation in ("status", "probe", "watch", "refresh", "refresh_status"):
        selected = commands.add_parser(operation, help="prepared fleet " + operation)
        prepared_arguments(selected)
        selected.add_argument("--json", action="store_true", required=True)
        if operation == "refresh":
            selected.add_argument(
                "--source", action="append", required=True, help="HOST:owner or LOCAL_HOST:desktop"
            )
        if operation == "refresh_status":
            selected.add_argument("--ticket-id", required=True)
    args = parser.parse_args(argv)
    if args.command == "snapshot" and args.access == "direct":
        return direct(args)
    try:
        from .public import desktop_context_id, read_cached

        if args.command == "context":
            print(desktop_context_id())
            return 0
        if args.command in ("prepare-context", "start-context", "stop-context"):
            from ._context import prepare_context, stop_context

            value = (
                stop_context(args.context_id or desktop_context_id())
                if args.command == "stop-context"
                else prepare_context(args.host_id, start=args.command == "start-context")
            )
            sys.stdout.buffer.write(encode_document(value, limit=REQUEST_LIMIT))
            return 0
        context = args.context_id or desktop_context_id()
        if args.command == "fleet":
            if args.transport == "mesh":
                try:
                    from .mesh_fleet import MeshFleetPublisher as FleetPublisher
                except ImportError as error:
                    raise ValueError(
                        "Mesh backend requires the optional mesh dependencies"
                    ) from error
                options = {"source": args.mesh_source}
            else:
                from .fleet import FleetPublisher

                options = {}

            publisher = FleetPublisher(
                args.host_id, context_id=context, path=args.socket, **options
            )

            def stop(_signum, _frame):
                publisher.stop()

            signal.signal(signal.SIGTERM, stop)
            signal.signal(signal.SIGINT, stop)
            publisher.run()
            return 0
        if args.command == "snapshot" and any(
            (args.host, args.mesh_revision, args.panes, args.option)
        ):
            raise IPCError(
                "invalid_request", "expanded/selected direct inventory requires direct access"
            )
        if args.command == "watch":
            from ._watch import stream_fleet

            return stream_fleet(
                context,
                path=args.socket,
                expected_host=args.expected_host,
                publisher_id=args.publisher_id,
            )
        sources = None
        if args.command == "refresh":
            sources = []
            for source in args.source:
                host, separator, kind = source.partition(":")
                if not separator or kind not in ("owner", "desktop"):
                    raise IPCError(
                        "invalid_request",
                        "refresh source requires HOST:owner or LOCAL_HOST:desktop",
                    )
                sources.append({"hostId": host, "source": kind})
        if args.command == "refresh_status" and args.publisher_id is None:
            raise IPCError(
                "invalid_request", "ticket lookup requires the originating fleet incarnation"
            )
        value = read_cached(
            context,
            expected_host=args.expected_host,
            operation=args.command,
            path=args.socket,
            publisher_id=args.publisher_id,
            sources=sources,
            ticket_id=getattr(args, "ticket_id", None),
        )
        sys.stdout.buffer.write(encode_document(value, limit=FRAME_LIMIT))
        return 0
    except (IPCError, ContractError, OSError, ValueError) as error:
        code = error.code if isinstance(error, (IPCError, ContractError)) else "invalid_request"
        sys.stdout.buffer.write(
            encode_document(
                {
                    "protocol": FLEET_PROTOCOL,
                    "schemaVersion": 1,
                    "kind": "operation_error",
                    "error": {"code": code, "message": "prepared fleet operation unavailable"},
                },
                limit=REQUEST_LIMIT,
            )
        )
        return 1
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
