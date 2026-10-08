"""Explicit client operations; prepared access never falls back to collection."""

import argparse
import sys

from tmux_observer.public import encode_document


def main(argv=None):
    parser = argparse.ArgumentParser(prog="tmux-observer-client")
    subparsers = parser.add_subparsers(dest="command", required=True)
    snapshot = subparsers.add_parser("snapshot")
    snapshot.add_argument("--access", choices=("direct",), required=True)
    snapshot.add_argument("--host", action="append", default=[])
    snapshot.add_argument("--mesh-revision")
    snapshot.add_argument("--panes", action="store_true")
    snapshot.add_argument("--option", action="append", default=[])
    snapshot.add_argument("--json", action="store_true", required=True)
    args = parser.parse_args(argv)
    from ._errors import ContractError
    from .direct import DirectInventory

    try:
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


if __name__ == "__main__":
    raise SystemExit(main())
