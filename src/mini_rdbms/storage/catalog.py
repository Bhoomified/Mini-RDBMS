"""In-memory catalog interface used by semantic analysis and execution."""

from __future__ import annotations

from mini_rdbms.common.types import IndexSchema, TableSchema


class Catalog:
    """Track table and index definitions for the current database."""

    def __init__(self) -> None:
        self._tables: dict[str, TableSchema] = {}
        self._indexes: dict[str, IndexSchema] = {}

    def get_table(self, name: str) -> TableSchema | None:
        return self._tables.get(name)

    def get_index(self, name: str) -> IndexSchema | None:
        return self._indexes.get(name)

    def list_tables(self) -> tuple[TableSchema, ...]:
        return tuple(self._tables.values())

    def list_indexes(self) -> tuple[IndexSchema, ...]:
        return tuple(self._indexes.values())

    def create_table(self, schema: TableSchema) -> None:
        if schema.name in self._tables:
            raise ValueError(f"table {schema.name!r} already exists")
        self._tables[schema.name] = schema

    def create_index(self, index: IndexSchema) -> None:
        if index.name in self._indexes:
            raise ValueError(f"index {index.name!r} already exists")
        self._indexes[index.name] = index

    def indexes(self) -> tuple[IndexSchema, ...]:
        return tuple(self._indexes.values())
