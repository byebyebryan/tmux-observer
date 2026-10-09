"""Checked private owner admission; no native, transport or public bypass API."""

import copy

from tmux_observer._delivery_validation import (
    _checked_service_frame,
    _decode_service_frame,
    _decode_service_input,
)


class OwnerDocument:
    __slots__ = ("full_size", "header_size", "value")

    def __init__(self, value):
        self.value, self.full_size, self.header_size = _checked_service_frame(value)

    @classmethod
    def from_wire(cls, raw):
        return cls._from_checked(_decode_service_frame(raw))

    @classmethod
    def decode_input(cls, raw):
        checked = _decode_service_input(raw)
        value = checked[0]
        return value, None if value.get("kind") == "operation_error" else cls._from_checked(checked)

    @classmethod
    def _from_checked(cls, checked):
        result = cls.__new__(cls)
        result.value, result.full_size, result.header_size = checked
        return result

    def header(self):
        return copy.deepcopy({**self.value, "snapshot": None})

    def retained(self):
        # The decoder/caller may still own its input; only owned copies survive.
        return copy.deepcopy(self.value)
