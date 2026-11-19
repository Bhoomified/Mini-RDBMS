import threading
import unittest

from mini_rdbms.integration.database import Database
from mini_rdbms.integration.session import Session


class ConcurrencyTest(unittest.TestCase):
    def test_conflicting_transactions_complete_without_lost_updates(self) -> None:
        database = Database()
        setup = Session(database)
        setup.execute("CREATE TABLE counters (id INT PRIMARY KEY, value INT)")
        setup.execute("INSERT INTO counters VALUES (1, 0)")
        barrier = threading.Barrier(2)
        results = []

        def worker(value):
            session = Session(database)
            session.execute("BEGIN")
            barrier.wait()
            results.append(session.execute(
                f"UPDATE counters SET value = {value} WHERE id = 1"
            ).is_ok)
            session.execute("COMMIT")

        threads = [
            threading.Thread(target=worker, args=(1,)),
            threading.Thread(target=worker, args=(2,)),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(sorted(results), [True, True])


if __name__ == "__main__":
    unittest.main()
