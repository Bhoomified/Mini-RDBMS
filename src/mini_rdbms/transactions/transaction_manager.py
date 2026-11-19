"""Transaction lifecycle coordinator."""

from __future__ import annotations

import itertools

from .lock_manager import LockManager
from .transaction import Transaction
from .undo_log import UndoLog


class TransactionManager:
    """Create transactions and coordinate commit or rollback."""

    def __init__(self) -> None:
        self.lock_manager = LockManager()
        self._ids = itertools.count(1)
        self._undo: dict[int, UndoLog] = {}
        self._transactions: dict[int, Transaction] = {}
        self.lock_manager.set_victim_handler(self._abort_victim)

    def begin(self) -> Transaction:
        transaction = Transaction(next(self._ids))
        self._undo[transaction.transaction_id] = UndoLog()
        self._transactions[transaction.transaction_id] = transaction
        return transaction

    def undo_log(self, transaction: Transaction) -> UndoLog:
        return self._undo[transaction.transaction_id]

    def commit(self, transaction: Transaction) -> None:
        transaction.commit()
        self._undo.pop(transaction.transaction_id, None)
        self._transactions.pop(transaction.transaction_id, None)
        self.lock_manager.release_all(transaction)

    def rollback(self, transaction: Transaction) -> None:
        undo = self._undo.pop(transaction.transaction_id, None)
        if undo is not None:
            undo.rollback()
        transaction.abort()
        self._transactions.pop(transaction.transaction_id, None)
        self.lock_manager.release_all(transaction)

    def _abort_victim(self, transaction_id: int) -> None:
        transaction = self._transactions.get(transaction_id)
        if transaction is not None:
            self.rollback(transaction)
