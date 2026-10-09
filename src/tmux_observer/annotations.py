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
    def pending_commands(selected):
        commands = []
        for sid in selected:
            if commands:
                commands.append(";")
            commands.extend(("display-message", "-p", "-t", sid, "#{session_id}", ";"))
            commands.extend(("show-options", "-q", "-t", sid, PENDING))
        return commands

    @staticmethod
    def pending_rows(output, selected):
        lines = output.splitlines()
        offset = 0
        result = {}
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
        return result, lines[offset:]

    @classmethod
    def sample_pending(cls, read, session_ids, deadline):
        """Coalesce minimal annotations, retaining explicit empty/absent meaning."""
        identifiers = list(session_ids)
        if len(identifiers) <= 1:
            return {sid: cls.sample(read, sid, (), deadline) for sid in identifiers}
        result = {}
        for start in range(0, len(identifiers), 32):
            selected = identifiers[start : start + 32]
            output = read(cls.pending_commands(selected), deadline, absent=True)
            values, remaining = cls.pending_rows(output, selected)
            result.update(values)
            if remaining:
                raise ProcessError("malformed_metadata", "unexpected native annotation output")
        return result

    @classmethod
    def sample_pending_and_closing(cls, read, session_ids, deadline, closing_command):
        """Keep explicit annotation scope and closing rows in one bounded chain."""
        identifiers = list(session_ids)
        if not identifiers:
            return {}, read(closing_command, deadline, absent=True, empty=True)
        result, closing = {}, ""
        # Two commands per annotation plus one final command stay below 64.
        for start in range(0, len(identifiers), 31):
            selected = identifiers[start : start + 31]
            last = start + len(selected) == len(identifiers)
            commands = cls.pending_commands(selected)
            if last:
                commands.extend((";", *closing_command))
            output = read(commands, deadline, absent=True, empty=True)
            values, remaining = cls.pending_rows(output, selected)
            result.update(values)
            if last:
                closing = "\n".join(remaining)
            elif remaining:
                raise ProcessError("malformed_metadata", "unexpected native annotation output")
        return result, closing

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
