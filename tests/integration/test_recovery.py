import os
import tempfile
import unittest

from mini_rdbms.integration.database import Database
from mini_rdbms.integration.session import Session


class RecoveryTest(unittest.TestCase):
    def test_reopens_binary_database_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "database.db")
            first = Database(path)
            session = Session(first)
            session.execute("CREATE TABLE t (id INT PRIMARY KEY, name TEXT)")
            session.execute("INSERT INTO t VALUES (1, 'saved')")
            first.close()

            second = Database(path)
            self.assertEqual(Session(second).execute("SELECT * FROM t").unwrap(), [{"id": 1, "name": "saved"}])


if __name__ == "__main__":
    unittest.main()
