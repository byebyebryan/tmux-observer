"""UI-neutral, fixed-source terminal/action configuration."""

import unicodedata
from dataclasses import dataclass

from .errors import ContractError


def has_control(value):
    return any(unicodedata.category(char).startswith("C") for char in value)


def require_clean_text(value, field):
    if "\x00" in value or has_control(value):
        raise ContractError("invalid_input", f"{field} must not contain NUL or control characters")
    return value


@dataclass(frozen=True, slots=True)
class ActionConfig:
    terminal: tuple[str, ...] = ("ghostty",)
    attach_timeout_seconds: int = 60

    def __post_init__(self):
        if (
            not isinstance(self.terminal, tuple)
            or not self.terminal
            or any(
                not isinstance(item, str) or not item or has_control(item) for item in self.terminal
            )
            or type(self.attach_timeout_seconds) is not int
            or not 1 <= self.attach_timeout_seconds <= 3600
        ):
            raise ContractError(
                "invalid_input", "invalid terminal or attachment timeout configuration"
            )


Config = ActionConfig
