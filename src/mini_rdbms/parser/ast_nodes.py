"""AST nodes produced by the recursive-descent SQL parser."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Union

from mini_rdbms.common.types import DataType, Value


@dataclass(frozen=True)
class Condition:
    """One comparison in a WHERE clause."""

    column: str
    operator: str
    value: Value


@dataclass(frozen=True)
class ColumnDefinition:
    """A column declaration in CREATE TABLE."""

    name: str
    data_type: DataType
    nullable: bool = True
    primary_key: bool = False


@dataclass(frozen=True)
class CreateTableStatement:
    """CREATE TABLE statement."""

    table: str
    columns: tuple[ColumnDefinition, ...]


@dataclass(frozen=True)
class CreateIndexStatement:
    """CREATE INDEX statement."""

    name: str
    table: str
    column: str
    index_type: str = "HASH"


@dataclass(frozen=True)
class InsertStatement:
    """INSERT INTO statement with one or more value tuples."""

    table: str
    columns: tuple[str, ...] | None
    values: tuple[tuple[Value, ...], ...]


@dataclass(frozen=True)
class SelectStatement:
    """SELECT statement."""

    table: str
    columns: tuple[str, ...]
    conditions: tuple[Condition, ...] = ()


@dataclass(frozen=True)
class UpdateStatement:
    """UPDATE statement."""

    table: str
    assignments: tuple[tuple[str, Value], ...]
    conditions: tuple[Condition, ...] = ()


@dataclass(frozen=True)
class DeleteStatement:
    """DELETE FROM statement."""

    table: str
    conditions: tuple[Condition, ...] = ()


@dataclass(frozen=True)
class TransactionStatement:
    """BEGIN, COMMIT, or ROLLBACK statement."""

    action: str


Statement = Union[
    CreateTableStatement,
    CreateIndexStatement,
    InsertStatement,
    SelectStatement,
    UpdateStatement,
    DeleteStatement,
    TransactionStatement,
]


@dataclass(frozen=True)
class ExplainStatement:
    """EXPLAIN wrapper around a supported statement."""

    statement: Statement
