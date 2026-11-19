"""Transaction state and ownership metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from threading import get_ident


class TransactionState(str, Enum):
    ACTIVE = "ACTIVE"
    COMMITTED = "COMMITTED"
    ABORTED = "ABORTED"


@dataclass
class Transaction:
    """Track one session's transaction lifecycle."""

    transaction_id: int
    owner_thread: int = field(default_factory=get_ident)
    state: TransactionState = TransactionState.ACTIVE
    locks: set[tuple[str, str]] = field(default_factory=set)
    write_set: dict[str, set[int]] = field(default_factory=dict)
    modified_pages: dict[str, set[int]] = field(default_factory=dict)

    def record_write(self, table: str, record_id: int, page_id: int | None = None) -> None:
        """Track logical rows and, when available, modified page IDs."""
        self.write_set.setdefault(table, set()).add(record_id)
        if page_id is not None:
            self.modified_pages.setdefault(table, set()).add(page_id)

    def commit(self) -> None:
        self.state = TransactionState.COMMITTED

    def abort(self) -> None:
        self.state = TransactionState.ABORTED
