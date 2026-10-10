"""Explicit optional Mesh cached-state adapter for the native owner contract.

Import this facade only when Mesh delivery is selected. The reviewed Mesh
reference codec supplies delivery wrapping; native semantics remain validated
by ``native`` and ``delivery``. Neither adapter starts or imports collection.
"""

from mesh_plus.observer import ObserverAdapter, ObserverCodec


class TmuxMeshCodec(ObserverCodec):
    def __init__(self, host, source="tmux_default"):
        super().__init__("tmux", host, source)


class TmuxMeshAdapter(ObserverAdapter):
    def __init__(self, host, path, source="tmux_default"):
        super().__init__("tmux", host, source, path)


__all__ = ["TmuxMeshAdapter", "TmuxMeshCodec"]
