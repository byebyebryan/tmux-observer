"""Explicit optional cached publisher factory, independent of reference adapters."""


def make_publisher(host, source, socket):
    """Construct a fixed cached publisher; construction performs no native I/O."""
    from mesh_plus.api import CachedPublisher

    from ._mesh_source import TmuxCachedSource
    from .mesh_profile import TmuxMeshProfile

    return CachedPublisher(
        "tmux", host, source, TmuxCachedSource(host, socket), profile=TmuxMeshProfile()
    )


__all__ = ["make_publisher"]
