import threading
import unittest

from mini_rdbms.common.errors import DeadlockError
from mini_rdbms.integration.database import Database


class DeadlockVictimTest(unittest.TestCase):
    def test_youngest_transaction_is_aborted_and_waiter_resumes(self) -> None:
        manager = Database().transactions
        older = manager.begin()
        younger = manager.begin()
        manager.lock_manager.acquire_exclusive(older, "row:a")
        manager.lock_manager.acquire_exclusive(younger, "row:b")
        barrier = threading.Barrier(2)
        outcomes = []

        def acquire(transaction, resource):
            barrier.wait()
            try:
                manager.lock_manager.acquire_exclusive(transaction, resource)
                outcomes.append((transaction.transaction_id, "acquired"))
            except DeadlockError:
                outcomes.append((transaction.transaction_id, "aborted"))

        first = threading.Thread(target=acquire, args=(older, "row:b"))
        second = threading.Thread(target=acquire, args=(younger, "row:a"))
        first.start()
        second.start()
        first.join()
        second.join()

        self.assertIn((younger.transaction_id, "aborted"), outcomes)
        self.assertIn((older.transaction_id, "acquired"), outcomes)
        self.assertEqual(younger.state.value, "ABORTED")


if __name__ == "__main__":
    unittest.main()
