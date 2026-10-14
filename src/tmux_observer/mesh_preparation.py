"""Explicit optional static rules for Mesh-owned prepared watch generations.

Importing this module requires no Mesh installation or native activity. Only
the factory opts into preparation interface 1, independently of publisher setup.
"""


class _Preparation:
    __slots__ = ("descriptor",)

    def __init__(self, descriptor):
        self.descriptor = descriptor

    def prepare_rules(self, state):
        from mesh_plus.api import PreparedRule

        # This is the same generation-static receipt/eligibility policy as the
        # supported TmuxMeshProfile. Mesh alone applies projected expiry, clock,
        # stream, scope and delivery checks on every current query.
        required = (
            frozenset(
                (receipt["sourceId"], receipt["component"])
                for receipt in state.receipts
                if receipt["sourceId"] == "default" and receipt["health"] in {"current", "partial"}
            )
            or None
        )
        return tuple(
            PreparedRule(
                tuple(row[key] for key in ("hostId", "serverGeneration", "sessionId", "createdAt")),
                required,
                True,
            )
            for row in state.records
        )


def make_preparation():
    """Promise static, pure, lossless Tmux Service 1 rules for one generation.

    No clock, environment, I/O, collection or mutable callback state contributes
    to rules. Semantic/package changes require guard retirement and re-admission.
    The implementation label identifies owner semantics; Mesh does not attest it.
    """
    from mesh_plus.api import PREPARATION_INTERFACE_VERSION, PreparationDescriptor

    from . import __version__
    from .mesh_profile import TmuxMeshProfile
    from .native import ValidationError

    if PREPARATION_INTERFACE_VERSION != 1:
        raise ValidationError("unsupported Mesh preparation interface")
    return _Preparation(
        PreparationDescriptor(
            1, TmuxMeshProfile().descriptor, f"tmux-observer-{__version__}:preparation-v1"
        )
    )


__all__ = ["make_preparation"]
