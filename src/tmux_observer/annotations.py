"""Explicit bounded compatibility annotation profile; never repairs registration.

The launch/action client owns the Plus annotation and its meaning. Observation 1
retains its boolean projection, independently of generic native session metadata.
"""

from ._process import ProcessError
from ._tmux_wire import TmuxWireError, parse_explicit_user_options

PENDING = "@rofi_tmux_plus_pending"


class PlusPendingProfile:
    name = "plus_pending_v1"

    @staticmethod
    def sample(read, session_id, names, deadline):
        values = {}
        for name in dict.fromkeys((PENDING, *names)):
            output = read(["show-options", "-q", "-t", session_id, name], deadline, absent=True)
            try:
                _pending, selected = parse_explicit_user_options(
                    output, [name], pending_name=PENDING
                )
            except TmuxWireError as problem:
                raise ProcessError(
                    "malformed_metadata", "invalid native option metadata"
                ) from problem
            values[name] = selected[name]
        return values[PENDING] is not None, {name: values[name] for name in names}
