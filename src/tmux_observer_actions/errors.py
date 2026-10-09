"""Shared structured failures with native action distinctions."""

from tmux_observer_client._errors import ContractError, clean_message

__all__ = ["ContractError", "NoServer", "TmuxMissing", "clean_message"]


class TmuxMissing(ContractError):
    def __init__(self, message: str = "tmux is not available") -> None:
        super().__init__("tmux_missing", message)


class NoServer(ContractError):
    def __init__(self) -> None:
        super().__init__("session_not_found", "no default tmux server is running")
