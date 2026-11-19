"""Logical reverse-order undo log."""

from __future__ import annotations

from collections.abc import Callable


class UndoLog:
    """Store rollback callbacks in reverse execution order."""

    def __init__(self) -> None:
        self._entries: list[Callable[[], None]] = []

    def append(self, undo: Callable[[], None]) -> None:
        self._entries.append(undo)

    def rollback(self) -> None:
        for undo in reversed(self._entries):
            undo()
        self._entries.clear()

    def clear(self) -> None:
        self._entries.clear()
