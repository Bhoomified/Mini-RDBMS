"""Hash index for equality predicates."""

from __future__ import annotations

from collections import defaultdict
from typing import Hashable

from mini_rdbms.common.types import RecordId, Value


class HashIndex:
    """Map values to sets of logical record IDs."""

    def __init__(self) -> None:
        self._entries: dict[Hashable, set[RecordId]] = defaultdict(set)

    def insert(self, value: Value, record_id: RecordId) -> None:
        self._entries[value].add(record_id)

    def search(self, value: Value) -> set[RecordId]:
        return set(self._entries.get(value, set()))

    def remove(self, value: Value, record_id: RecordId) -> None:
        ids = self._entries.get(value)
        if ids is None:
            return
        ids.discard(record_id)
        if not ids:
            self._entries.pop(value, None)

    def update(self, old_value: Value, new_value: Value, record_id: RecordId) -> None:
        self.remove(old_value, record_id)
        self.insert(new_value, record_id)

    def rebuild(self, records: list[tuple[RecordId, Value]]) -> None:
        self._entries.clear()
        for record_id, value in records:
            self.insert(value, record_id)
