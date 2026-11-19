import os
import tempfile
import unittest

from mini_rdbms.integration.database import Database
from mini_rdbms.integration.session import Session


class IndexRecoveryTest(unittest.TestCase):
    def test_index_definition_is_reopened_and_used(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "database.db")
            first = Database(path)
            session = Session(first)
            session.execute("CREATE TABLE t (id INT PRIMARY KEY, value TEXT)")
            session.execute("INSERT INTO t VALUES (1, 'one')")
            session.execute("CREATE INDEX t_id ON t (id) USING HASH")
            first.close()

            second = Database(path)
            result = Session(second).execute("EXPLAIN SELECT * FROM t WHERE id = 1")
            self.assertEqual(result.unwrap()["plan"]["access_path"], "HASH_LOOKUP")


if __name__ == "__main__":
    unittest.main()
