"""Catalog-based semantic validation for parsed SQL statements."""

from __future__ import annotations

from collections.abc import Iterable

from mini_rdbms.common.errors import SemanticError
from mini_rdbms.common.result import Result
from mini_rdbms.common.types import Catalog, ColumnSchema, DataType, TableSchema, Value

from .ast_nodes import (
    ColumnDefinition,
    Condition,
    CreateIndexStatement,
    CreateTableStatement,
    DeleteStatement,
    ExplainStatement,
    InsertStatement,
    SelectStatement,
    Statement,
    TransactionStatement,
    UpdateStatement,
)


class SemanticAnalyzer:
    """Validate AST nodes against read-only catalog metadata."""

    def __init__(self, catalog: Catalog) -> None:
        self.catalog = catalog

    def validate(self, statement: Statement | ExplainStatement) -> Result[None]:
        """Return success or the first semantic error found."""
        try:
            self._validate(statement)
        except SemanticError as error:
            return Result.fail(error)
        return Result.ok(None)

    def _validate(self, statement: Statement | ExplainStatement) -> None:
        if isinstance(statement, ExplainStatement):
            self._validate(statement.statement)
        elif isinstance(statement, CreateTableStatement):
            self._validate_create_table(statement)
        elif isinstance(statement, CreateIndexStatement):
            self._validate_create_index(statement)
        elif isinstance(statement, InsertStatement):
            self._validate_insert(statement)
        elif isinstance(statement, SelectStatement):
            self._validate_select(statement)
        elif isinstance(statement, UpdateStatement):
            self._validate_update(statement)
        elif isinstance(statement, DeleteStatement):
            self._validate_delete(statement)
        elif isinstance(statement, TransactionStatement):
            return

    def _validate_create_table(self, statement: CreateTableStatement) -> None:
        names = [column.name for column in statement.columns]
        self._require_unique(names, "column definition")
        primary_keys = [column for column in statement.columns if column.primary_key]
        if len(primary_keys) > 1:
            raise SemanticError("a table can have only one primary key")

    def _validate_create_index(self, statement: CreateIndexStatement) -> None:
        table = self._table(statement.table)
        self._column(table, statement.column)
        if statement.index_type not in {"HASH", "BTREE"}:
            raise SemanticError(f"unsupported index type {statement.index_type}")

    def _validate_insert(self, statement: InsertStatement) -> None:
        table = self._table(statement.table)
        columns = list(statement.columns or tuple(column.name for column in table.columns))
        self._require_unique(columns, "INSERT column")
        schema_columns = [self._column(table, name) for name in columns]
        for values in statement.values:
            if len(values) != len(schema_columns):
                raise SemanticError("INSERT value count does not match column count")
            for value, column in zip(values, schema_columns):
                self._validate_value_type(value, column)

    def _validate_select(self, statement: SelectStatement) -> None:
        table = self._table(statement.table)
        if statement.columns != ("*",):
            for column in statement.columns:
                self._column(table, column)
        self._validate_conditions(table, statement.conditions)

    def _validate_update(self, statement: UpdateStatement) -> None:
        table = self._table(statement.table)
        self._require_unique([name for name, _ in statement.assignments], "SET column")
        for name, value in statement.assignments:
            self._validate_value_type(value, self._column(table, name))
        self._validate_conditions(table, statement.conditions)

    def _validate_delete(self, statement: DeleteStatement) -> None:
        table = self._table(statement.table)
        self._validate_conditions(table, statement.conditions)

    def _validate_conditions(
        self, table: TableSchema, conditions: Iterable[Condition]
    ) -> None:
        for condition in conditions:
            self._validate_value_type(condition.value, self._column(table, condition.column))

    def _table(self, name: str) -> TableSchema:
        table = self.catalog.get_table(name)
        if table is None:
            raise SemanticError(f"unknown table {name!r}", context="table")
        return table

    @staticmethod
    def _column(table: TableSchema, name: str) -> ColumnSchema:
        column = table.get_column(name)
        if column is None:
            raise SemanticError(
                f"unknown column {name!r}",
                context=f"table {table.name!r}",
            )
        return column

    @staticmethod
    def _require_unique(names: list[str], subject: str) -> None:
        if len(names) != len(set(names)):
            raise SemanticError(f"duplicate {subject}")

    @staticmethod
    def _validate_value_type(value: Value, column: ColumnSchema) -> None:
        if value is None:
            if not column.nullable:
                raise SemanticError(f"column {column.name!r} cannot be NULL")
            return
        compatible = {
            DataType.INT: type(value) is int,
            DataType.FLOAT: type(value) in {int, float},
            DataType.TEXT: type(value) is str,
            DataType.BOOL: type(value) is bool,
        }[column.data_type]
        if not compatible:
            raise SemanticError(
                f"value {value!r} does not match {column.data_type.value}",
                context=f"column {column.name!r}",
            )
