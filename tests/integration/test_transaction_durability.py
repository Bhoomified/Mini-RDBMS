import os
import tempfile
import unittest

from mini_rdbms.integration.database import Database
from mini_rdbms.integration.session import Session


class TransactionDurabilityTest(unittest.TestCase):
    def test_uncommitted_write_is_not_persisted_after_session_close(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "database.db")
            database = Database(path)
            session = Session(database)
            session.execute("CREATE TABLE t (id INT PRIMARY KEY)")
            session.execute("BEGIN")
            session.execute("INSERT INTO t VALUES (1)")
            session.close()
            database.close()

            reopened = Session(Database(path))
            self.assertEqual(reopened.execute("SELECT * FROM t").unwrap(), [])


if __name__ == "__main__":
    unittest.main()
