"""Common domain exceptions shared by all Mini RDBMS components."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ErrorPosition:
    """Source location attached to an error when one is available."""

    offset: int | None = None
    line: int | None = None
    column: int | None = None

    def __str__(self) -> str:
        if self.line is not None and self.column is not None:
            return f"line {self.line}, column {self.column}"
        if self.offset is not None:
            return f"offset {self.offset}"
        return "unknown position"


class MiniRdbmsError(Exception):
    """Base class for expected Mini RDBMS failures."""

    category = "database"

    def __init__(
        self,
        message: str,
        *,
        position: ErrorPosition | None = None,
        context: str | None = None,
    ) -> None:
        self.message = message
        self.position = position
        self.context = context
        details = message
        if context:
            details = f"{context}: {details}"
        if position:
            details = f"{details} ({position})"
        super().__init__(details)


class LexicalError(MiniRdbmsError):
    """Raised when SQL text cannot be tokenized."""

    category = "lexical"


class SyntaxError(MiniRdbmsError):
    """Raised when tokens do not match the SQL grammar."""

    category = "syntax"


class SemanticError(MiniRdbmsError):
    """Raised when a syntactically valid statement is not meaningful."""

    category = "semantic"


class ConstraintError(MiniRdbmsError):
    """Raised when a data integrity constraint is violated."""

    category = "constraint"


class StorageError(MiniRdbmsError):
    """Raised when storage cannot complete an operation safely."""

    category = "storage"


class TransactionError(MiniRdbmsError):
    """Raised when a transaction operation is invalid or fails."""

    category = "transaction"


class DeadlockError(TransactionError):
    """Raised when the wait-for graph detects a deadlock."""

    category = "deadlock"


class RecoveryError(StorageError):
    """Raised when crash recovery cannot restore a valid state."""

    category = "recovery"
