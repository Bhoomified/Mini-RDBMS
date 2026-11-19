"""Session facade for executing SQL statements."""

from __future__ import annotations

from mini_rdbms.common.result import Result
from mini_rdbms.execution.statement_executor import StatementExecutor

from .database import Database


class Session:
    """Hold transaction state for one client session."""

    def __init__(self, database: Database) -> None:
        self.database = database
        self.executor = StatementExecutor(database)

    def execute(self, sql: str) -> Result:
        """Tokenize, parse, validate, and execute one SQL statement."""
        return self.executor.execute(sql)

    def close(self) -> None:
        """Rollback an unfinished transaction before releasing the session."""
        if self.executor.transaction is not None:
            self.execute("ROLLBACK")
