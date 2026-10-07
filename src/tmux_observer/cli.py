"""Command entry point. Operations are added only with their accepted producer."""

import argparse

from . import __version__


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tmux-observer")
    parser.add_argument("--version", action="version", version=__version__)
    parser.parse_args(argv)
    parser.print_help()
    return 0
