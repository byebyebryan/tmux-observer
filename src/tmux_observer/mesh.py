"""Explicit optional Mesh cached-state adapter for the native owner contract.

Import this facade only when Mesh delivery is selected. The reviewed Mesh
reference codec and cached adapter retain their compatibility behavior. The
Observer-owned SDK profile supplies pure native interpretation through
``native`` and ``delivery``. These interfaces start no collection.
"""

from mesh_plus.observer import ObserverAdapter, ObserverCodec

from .mesh_profile import TmuxMeshProfile, TmuxMeshStateCodec


class TmuxMeshCodec(ObserverCodec):
    def __init__(self, host, source="tmux_default"):
        super().__init__("tmux", host, source)


class TmuxMeshAdapter(ObserverAdapter):
    def __init__(self, host, path, source="tmux_default"):
        super().__init__("tmux", host, source, path)


__all__ = ["TmuxMeshAdapter", "TmuxMeshCodec", "TmuxMeshProfile", "TmuxMeshStateCodec"]
