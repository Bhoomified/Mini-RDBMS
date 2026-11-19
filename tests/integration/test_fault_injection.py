import os
import tempfile
import unittest

from mini_rdbms.common.errors import StorageError
from mini_rdbms.integration.database import Database
from mini_rdbms.integration.session import Session


class FaultInjectionTest(unittest.TestCase):
    def test_wal_replays_after_injected_post_wal_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "database.db")
            database = Database(path)
            session = Session(database)
            session.execute("CREATE TABLE t (id INT PRIMARY KEY)")
            with self.assertRaises(StorageError):
                database.persist("after_wal")
            recovered = Database(path)
            self.assertIsNotNone(recovered.catalog.get_table("t"))


if __name__ == "__main__":
    unittest.main()
