"""Checked private owner admission; no native, transport or public bypass API."""

import copy

from tmux_observer._delivery_validation import _checked_service_frame


class OwnerDocument:
    __slots__ = ("full_size", "header_size", "value")

    def __init__(self, value):
        self.value, self.full_size, self.header_size = _checked_service_frame(value)

    def header(self):
        return copy.deepcopy({**self.value, "snapshot": None})

    def retained(self):
        # The decoder/caller may still own its input; only owned copies survive.
        return copy.deepcopy(self.value)
