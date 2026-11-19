"""Registry for table indexes."""

from __future__ import annotations

from .bplus_tree import BPlusTree
from .hash_index import HashIndex


class IndexManager:
    """Create and retrieve named hash or ordered indexes."""

    def __init__(self) -> None:
        self._indexes: dict[str, HashIndex | BPlusTree] = {}
        self._metadata: dict[str, tuple[str, str]] = {}

    def create(self, name: str, index_type: str, table: str = "", column: str = "") -> HashIndex | BPlusTree:
        if name in self._indexes:
            raise ValueError(f"index {name!r} already exists")
        if index_type == "HASH":
            index = HashIndex()
        elif index_type == "BTREE":
            index = BPlusTree()
        else:
            raise ValueError(f"unsupported index type {index_type!r}")
        self._indexes[name] = index
        self._metadata[name] = (table, column)
        return index

    def get(self, name: str) -> HashIndex | BPlusTree | None:
        return self._indexes.get(name)

    def column(self, name: str | None) -> str | None:
        return self._metadata.get(name, ("", ""))[1] if name else None

    def insert(self, name: str, value, record_id: int) -> None:
        self._indexes[name].insert(value, record_id)

    def update_row(self, table: str, record_id: int, old_row: dict, new_row: dict) -> None:
        for name, (index_table, column) in self._metadata.items():
            if index_table == table and old_row.get(column) != new_row.get(column):
                self._indexes[name].update(old_row.get(column), new_row.get(column), record_id)

    def delete_row(self, table: str, record_id: int, row: dict) -> None:
        for name, (index_table, column) in self._metadata.items():
            if index_table == table:
                self._indexes[name].delete(row.get(column), record_id)

    def rebuild_all(self, storage) -> None:
        """Rebuild every registered index from authoritative heap rows."""
        for name, (table, column) in self._metadata.items():
            index = self._indexes[name]
            index.rebuild(
                [
                    (row[column], record_id)
                    for record_id, row in storage.scan(table)
                ]
                if hasattr(index, "rebuild") and index.__class__.__name__ == "BPlusTree"
                else [
                    (record_id, row[column])
                    for record_id, row in storage.scan(table)
                ]
            )
