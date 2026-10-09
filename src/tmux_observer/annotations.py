"""Explicit bounded compatibility annotation profile; never repairs registration.

The launch/action client owns the Plus annotation and its meaning. Observation 1
retains its boolean projection, independently of generic native session metadata.
"""

from ._process import ProcessError
from ._tmux_wire import TmuxWireError, parse_explicit_user_options

PENDING = "@rofi_tmux_plus_pending"


class PlusPendingProfile:
    name = "plus_pending_v1"

    @classmethod
    def sample_pending(cls, read, session_ids, deadline):
        """Coalesce minimal annotations, retaining explicit empty/absent meaning."""
        identifiers = list(session_ids)
        if len(identifiers) <= 1:
            return {sid: cls.sample(read, sid, (), deadline) for sid in identifiers}
        result = {}
        for start in range(0, len(identifiers), 32):
            selected = identifiers[start : start + 32]
            commands = []
            for sid in selected:
                if commands:
                    commands.append(";")
                commands.extend(("display-message", "-p", "-t", sid, "#{session_id}", ";"))
                commands.extend(("show-options", "-q", "-t", sid, PENDING))
            output = read(commands, deadline, absent=True)
            lines = output.splitlines()
            offset = 0
            for sid in selected:
                if offset >= len(lines) or lines[offset] != sid:
                    raise ProcessError("malformed_metadata", "native annotation scope changed")
                offset += 1
                value = ""
                if offset < len(lines) and lines[offset].startswith(PENDING + " "):
                    value = lines[offset]
                    offset += 1
                try:
                    pending, _values = parse_explicit_user_options(value, (), pending_name=PENDING)
                except TmuxWireError as problem:
                    raise ProcessError(
                        "malformed_metadata", "invalid native option metadata"
                    ) from problem
                result[sid] = pending, {}
            if offset != len(lines):
                raise ProcessError("malformed_metadata", "unexpected native annotation output")
        return result

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
