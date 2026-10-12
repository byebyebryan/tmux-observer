"""Explicit optional Mesh cached-state adapter for the native owner contract.

Import this facade only when Mesh delivery is selected. The reviewed Mesh
reference codec retains its pure compatibility validation. Cached acquisition
uses the Observer-owned source and public generic Mesh publisher. The
Observer-owned SDK profile supplies pure native interpretation through
``native`` and ``delivery``. These interfaces start no collection.
"""

from mesh_plus.observer import ObserverCodec

from .mesh_profile import TmuxMeshProfile, TmuxMeshStateCodec
from .mesh_publisher import make_publisher


class TmuxMeshCodec(ObserverCodec):
    def __init__(self, host, source="tmux_default"):
        super().__init__("tmux", host, source)


class TmuxMeshAdapter:
    """Compatibility constructor over the independently imported owner factory."""

    def __init__(self, host, path, source="tmux_default"):
        self.publisher = make_publisher(host, source, path)

    def __getattr__(self, name):
        return getattr(self.publisher, name)


__all__ = ["TmuxMeshAdapter", "TmuxMeshCodec", "TmuxMeshProfile", "TmuxMeshStateCodec"]
