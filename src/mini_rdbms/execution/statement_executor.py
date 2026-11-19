"""SQL statement execution over the shared engine components."""

from __future__ import annotations

from mini_rdbms.common.errors import DeadlockError, MiniRdbmsError, SemanticError
from mini_rdbms.common.result import Result
from mini_rdbms.common.types import ColumnSchema, IndexSchema, TableSchema
from mini_rdbms.parser.ast_nodes import (
    CreateIndexStatement,
    CreateTableStatement,
    DeleteStatement,
    ExplainStatement,
    InsertStatement,
    SelectStatement,
    TransactionStatement,
    UpdateStatement,
)
from mini_rdbms.parser.ast_printer import format_ast
from mini_rdbms.parser.lexer import Lexer
from mini_rdbms.parser.parser import Parser
from mini_rdbms.parser.semantic import SemanticAnalyzer
from mini_rdbms.optimizer.executor import Executor
from mini_rdbms.optimizer.planner import Planner


class StatementExecutor:
    """Execute parsed statements and expose expected errors as Results."""

    def __init__(self, database) -> None:
        self.database = database
        self.transaction = None
        self.last_trace: list[dict[str, str]] = []

    def execute(self, sql: str) -> Result:
        self.last_trace = [{"engine": "E1", "stage": "received", "detail": "SQL text received"}]
        try:
            statement = Parser(Lexer(sql).tokenize()).parse()
            self.last_trace.append({"engine": "E1", "stage": "parsed", "detail": type(statement).__name__})
            validation = SemanticAnalyzer(self.database.catalog).validate(statement)
            if not validation.is_ok:
                self.last_trace.append({"engine": "E1", "stage": "semantic-error", "detail": str(validation.error)})
                return validation
            self.last_trace.append({"engine": "E1", "stage": "semantic", "detail": "catalog validation passed"})
            if isinstance(statement, ExplainStatement):
                self.last_trace.append({"engine": "E2", "stage": "planning", "detail": "access path selected"})
            elif isinstance(statement, (SelectStatement, UpdateStatement, DeleteStatement)):
                self.last_trace.append({"engine": "E2", "stage": "planning", "detail": "scan or index path selected"})
            if isinstance(statement, (InsertStatement, UpdateStatement, DeleteStatement, TransactionStatement)):
                self.last_trace.append({"engine": "E3", "stage": "transaction", "detail": "transaction/undo/lock path checked"})
            self.last_trace.append({"engine": "E4", "stage": "storage", "detail": "storage operation ready"})
            write_statement = isinstance(statement, (InsertStatement, UpdateStatement, DeleteStatement))
            auto_transaction = write_statement and self.transaction is None
            if auto_transaction:
                self.transaction = self.database.transactions.begin()
            result = Result.ok(self._execute(statement, sql))
            if auto_transaction and self.transaction is not None:
                self.database.transactions.commit(self.transaction)
                self.transaction = None
            if self.database.path and (
                self.transaction is None
                or not isinstance(statement, (InsertStatement, UpdateStatement, DeleteStatement))
            ):
                self.database.persist()
            return result
        except MiniRdbmsError as error:
            self.last_trace.append({"engine": "E4", "stage": "error", "detail": str(error)})
            if self.transaction is not None:
                self.database.transactions.rollback(self.transaction)
                self.database.indexes.rebuild_all(self.database.storage)
                self.transaction = None
            return Result.fail(error)
        except (KeyError, ValueError) as error:
            self.last_trace.append({"engine": "E4", "stage": "error", "detail": str(error)})
            return Result.fail(SemanticError(str(error)))

    def _execute(self, statement, source_sql: str = ""):
        if isinstance(statement, ExplainStatement):
            details = {
                "tokens": [
                    str(token)
                    for token in Lexer(source_sql.strip()[7:].strip()).tokenize()
                ],
                "ast": format_ast(statement.statement),
                "semantic": "valid",
            }
            if isinstance(statement.statement, SelectStatement):
                plan = Planner(
                    self.database.catalog,
                    self.database.storage,
                    self.database.indexes,
                ).plan(statement.statement)
                details["plan"] = {
                    "access_path": plan.access_path.value,
                    "index": plan.index_name,
                    "reason": plan.reason,
                }
                if plan.index_name is None:
                    details["plan"]["automatic_index"] = (
                        f"__auto_{statement.statement.table}_"
                        f"{statement.statement.conditions[0].column}_"
                        f"{'hash' if statement.statement.conditions[0].operator == '=' else 'btree'}"
                        if statement.statement.conditions
                        and statement.statement.conditions[0].operator in
                        {"=", "!=", "<>", "<", "<=", ">", ">="}
                        else None
                    )
            return details
        if isinstance(statement, (SelectStatement, UpdateStatement, DeleteStatement)):
            self._ensure_automatic_indexes(statement)
        if isinstance(statement, CreateTableStatement):
            schema = TableSchema(
                statement.table,
                tuple(
                    ColumnSchema(column.name, column.data_type, column.nullable, column.primary_key)
                    for column in statement.columns
                ),
            )
            self.database.catalog.create_table(schema)
            self.database.storage.create_table(schema)
            return {"affected": 0}
        if isinstance(statement, CreateIndexStatement):
            self.database.catalog.create_index(
                IndexSchema(statement.name, statement.table, statement.column, statement.index_type)
            )
            self.database.indexes.create(
                statement.name, statement.index_type, statement.table, statement.column
            )
            for record_id, row in self.database.storage.scan(statement.table):
                self.database.indexes.insert(statement.name, row[statement.column], record_id)
            return {"affected": 0}
        if isinstance(statement, TransactionStatement):
            return self._transaction(statement.action)
        if isinstance(statement, InsertStatement):
            return self._insert(statement)
        if isinstance(statement, SelectStatement):
            return self._select(statement)
        if isinstance(statement, UpdateStatement):
            return self._update(statement)
        if isinstance(statement, DeleteStatement):
            return self._delete(statement)
        raise SemanticError("unsupported statement")

    def _ensure_automatic_indexes(self, statement) -> None:
        """Create a hash index for an unindexed equality predicate."""
        table = statement.table
        indexes = self.database.catalog.list_indexes()
        for condition in statement.conditions:
            if condition.operator not in {"=", "!=", "<>", "<", "<=", ">", ">="}:
                continue
            required_type = "HASH" if condition.operator == "=" else "BTREE"
            if any(
                index.table_name == table
                and index.column_name == condition.column
                and index.index_type == required_type
                for index in indexes
            ):
                continue
            index_type = "HASH" if condition.operator == "=" else "BTREE"
            suffix_name = "hash" if index_type == "HASH" else "btree"
            base_name = f"__auto_{table}_{condition.column}_{suffix_name}"
            name = base_name
            suffix = 2
            while self.database.catalog.get_index(name) is not None:
                name = f"{base_name}_{suffix}"
                suffix += 1
            index = IndexSchema(name, table, condition.column, index_type)
            self.database.catalog.create_index(index)
            self.database.indexes.create(name, index_type, table, condition.column)
            for record_id, row in self.database.storage.scan(table):
                self.database.indexes.insert(name, row[condition.column], record_id)
            indexes = (*indexes, index)

    def _transaction(self, action: str):
        if action == "BEGIN":
            if self.transaction is not None:
                raise SemanticError("transaction already active")
            self.transaction = self.database.transactions.begin()
        elif action == "COMMIT" and self.transaction:
            self.database.transactions.commit(self.transaction)
            self.transaction = None
            self.database.persist()
        elif action == "ROLLBACK" and self.transaction:
            self.database.transactions.rollback(self.transaction)
            self.database.indexes.rebuild_all(self.database.storage)
            self.transaction = None
        return {"transaction": action}

    def _insert(self, statement: InsertStatement):
        self._lock_write(statement.table)
        schema = self.database.catalog.get_table(statement.table)
        columns = list(statement.columns or tuple(column.name for column in schema.columns))
        primary_key = schema.primary_key
        if primary_key is not None:
            existing = {
                row[primary_key.name]
                for _record_id, row in self.database.storage.scan(statement.table)
            }
            pending = set()
            for values in statement.values:
                row = dict(zip(columns, values))
                key = row[primary_key.name]
                if key in existing or key in pending:
                    raise SemanticError(f"duplicate primary key value {key!r}")
                pending.add(key)
        record_ids = []
        for values in statement.values:
            row = dict(zip(columns, values))
            record_id = self.database.storage.insert(statement.table, row)
            record_ids.append(record_id)
            if self.transaction:
                self.transaction.record_write(statement.table, record_id)
                self.database.transactions.undo_log(self.transaction).append(
                    lambda rid=record_id: self.database.storage.delete(statement.table, rid)
                )
        return {"affected": len(record_ids), "record_ids": record_ids}

    def _select(self, statement: SelectStatement):
        self._lock_read(statement.table)
        plan = Planner(
            self.database.catalog,
            self.database.storage,
            self.database.indexes,
        ).plan(statement)
        result = Executor(self.database.storage, self.database.indexes).select(statement, plan)
        return result.rows

    def _update(self, statement):
        affected = 0
        candidates = self._candidate_ids(statement)
        records = (
            (record_id, row) for record_id, row in self.database.storage.scan(statement.table)
            if candidates is None or record_id in candidates
        )
        for record_id, row in list(records):
            if self._matches(row, statement.conditions):
                self._lock_write(statement.table, record_id)
                old = dict(row)
                row.update(dict(statement.assignments))
                self.database.storage.update(statement.table, record_id, row)
                self.database.indexes.update_row(statement.table, record_id, old, row)
                affected += 1
                if self.transaction:
                    self.transaction.record_write(statement.table, record_id)
                    self.database.transactions.undo_log(self.transaction).append(
                        lambda rid=record_id, previous=old: self.database.storage.update(
                            statement.table, rid, previous
                        )
                    )
        return {"affected": affected}

    def _delete(self, statement):
        affected = 0
        candidates = self._candidate_ids(statement)
        records = (
            (record_id, row) for record_id, row in self.database.storage.scan(statement.table)
            if candidates is None or record_id in candidates
        )
        for record_id, row in list(records):
            if self._matches(row, statement.conditions):
                self._lock_write(statement.table, record_id)
                self.database.storage.delete(statement.table, record_id)
                self.database.indexes.delete_row(statement.table, record_id, row)
                affected += 1
                if self.transaction:
                    self.transaction.record_write(statement.table, record_id)
                    self.database.transactions.undo_log(self.transaction).append(
                        lambda rid=record_id, previous=dict(row): self.database.storage.insert_with_id(
                            statement.table, rid, previous
                        )
                    )
        return {"affected": affected}

    @staticmethod
    def _matches(row, conditions):
        operators = {
            "=": lambda left, right: left == right,
            "!=": lambda left, right: left != right,
            "<>": lambda left, right: left != right,
            "<": lambda left, right: left < right,
            "<=": lambda left, right: left <= right,
            ">": lambda left, right: left > right,
            ">=": lambda left, right: left >= right,
        }
        return all(operators[item.operator](row[item.column], item.value) for item in conditions)

    def _lock_read(self, table: str) -> None:
        if self.transaction:
            self.database.transactions.lock_manager.acquire_shared(
                self.transaction, f"table:{table}"
            )

    def _lock_write(self, table: str, record_id: int | None = None) -> None:
        if self.transaction:
            self.database.transactions.lock_manager.acquire_exclusive(
                self.transaction,
                f"table:{table}",
            )
            if record_id is not None:
                self.database.transactions.lock_manager.acquire_exclusive(
                    self.transaction, f"row:{table}:{record_id}"
                )

    def _candidate_ids(self, statement):
        plan = Planner(
            self.database.catalog,
            self.database.storage,
            self.database.indexes,
        ).plan(
            SelectStatement(statement.table, ("*",), statement.conditions)
        )
        return Executor(self.database.storage, self.database.indexes).candidate_ids(
            SelectStatement(statement.table, ("*",), statement.conditions), plan
        )
