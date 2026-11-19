import unittest
import threading
import time

from mini_rdbms.transactions.transaction_manager import TransactionManager
from mini_rdbms.transactions.wait_for_graph import WaitForGraph


class TransactionTest(unittest.TestCase):
    def test_undo_runs_in_reverse_order(self) -> None:
        manager = TransactionManager()
        transaction = manager.begin()
        events = []
        manager.undo_log(transaction).append(lambda: events.append("first"))
        manager.undo_log(transaction).append(lambda: events.append("second"))
        manager.rollback(transaction)
        self.assertEqual(events, ["second", "first"])

    def test_wait_for_graph_detects_cycle(self) -> None:
        graph = WaitForGraph()
        graph.add_wait(1, 2)
        graph.add_wait(2, 1)
        self.assertTrue(graph.has_cycle())

    def test_shared_readers_block_exclusive_writer(self) -> None:
        manager = TransactionManager()
        reader = manager.begin()
        writer = manager.begin()
        manager.lock_manager.acquire_shared(reader, "table:items")
        acquired = threading.Event()

        def write() -> None:
            manager.lock_manager.acquire_exclusive(writer, "table:items")
            acquired.set()

        thread = threading.Thread(target=write)
        thread.start()
        time.sleep(0.01)
        self.assertFalse(acquired.is_set())
        manager.rollback(reader)
        thread.join(timeout=1)
        self.assertTrue(acquired.is_set())
        manager.rollback(writer)

    def test_transaction_can_upgrade_its_shared_lock(self) -> None:
        manager = TransactionManager()
        transaction = manager.begin()
        manager.lock_manager.acquire_shared(transaction, "table:items")
        manager.lock_manager.acquire_exclusive(transaction, "table:items")
        manager.commit(transaction)


if __name__ == "__main__":
    unittest.main()
