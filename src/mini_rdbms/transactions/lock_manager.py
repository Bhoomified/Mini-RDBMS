"""Condition-based shared and exclusive lock manager."""

from __future__ import annotations

import threading

from mini_rdbms.common.errors import DeadlockError, TransactionError

from .transaction import Transaction, TransactionState
from .wait_for_graph import WaitForGraph


class LockManager:
    """Coordinate S/X locks without busy waiting."""

    def __init__(self) -> None:
        self._condition = threading.Condition(threading.Lock())
        self._shared: dict[str, set[int]] = {}
        self._exclusive: dict[str, int] = {}
        self._graph = WaitForGraph()
        self._victim_handler = None

    def set_victim_handler(self, handler) -> None:
        """Register a callback invoked outside the condition for deadlock victims."""
        self._victim_handler = handler

    def acquire_shared(self, transaction: Transaction, resource: str) -> None:
        self._acquire(transaction, resource, exclusive=False)

    def acquire_exclusive(self, transaction: Transaction, resource: str) -> None:
        self._acquire(transaction, resource, exclusive=True)

    def release_all(self, transaction: Transaction) -> None:
        with self._condition:
            for resource, holder in list(self._exclusive.items()):
                if holder == transaction.transaction_id:
                    del self._exclusive[resource]
            for resource, holders in list(self._shared.items()):
                holders.discard(transaction.transaction_id)
                if not holders:
                    del self._shared[resource]
            self._graph.remove_wait(transaction.transaction_id)
            self._graph.remove_holder(transaction.transaction_id)
            self._condition.notify_all()

    def _acquire(self, transaction: Transaction, resource: str, exclusive: bool) -> None:
        while True:
            victim_id = None
            with self._condition:
                if transaction.state != TransactionState.ACTIVE:
                    raise DeadlockError(
                        f"transaction {transaction.transaction_id} is no longer active"
                    )
                holders = self._holders(resource, transaction.transaction_id)
                if not holders or (not exclusive and self._exclusive.get(resource) == transaction.transaction_id):
                    if exclusive:
                        self._exclusive[resource] = transaction.transaction_id
                        self._shared.get(resource, set()).discard(transaction.transaction_id)
                    else:
                        self._shared.setdefault(resource, set()).add(transaction.transaction_id)
                    transaction.locks.add((resource, "X" if exclusive else "S"))
                    self._graph.remove_wait(transaction.transaction_id)
                    return
                for holder in holders:
                    self._graph.add_wait(transaction.transaction_id, holder)
                if self._graph.has_cycle():
                    cycle = self._graph.cycle_nodes()
                    victim_id = max(cycle)
                    self._graph.remove_wait(victim_id)
                else:
                    self._condition.wait()
            if victim_id is not None:
                if self._victim_handler is not None:
                    self._victim_handler(victim_id)
                if victim_id == transaction.transaction_id:
                    raise DeadlockError(
                        f"transaction {transaction.transaction_id} aborted as deadlock victim"
                    )

    def _holders(self, resource: str, transaction_id: int) -> set[int]:
        holders = set(self._shared.get(resource, set()))
        if resource in self._exclusive:
            holders.add(self._exclusive[resource])
        holders.discard(transaction_id)
        return holders
