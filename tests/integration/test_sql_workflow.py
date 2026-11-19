import unittest

from mini_rdbms.integration.database import Database
from mini_rdbms.integration.session import Session


class SqlWorkflowTest(unittest.TestCase):
    def test_create_insert_select_update_rollback(self) -> None:
        session = Session(Database())
        self.assertTrue(session.execute("CREATE TABLE t (id INT PRIMARY KEY, name TEXT)").is_ok)
        self.assertTrue(session.execute("INSERT INTO t VALUES (1, 'A')").is_ok)
        self.assertEqual(session.execute("SELECT * FROM t").unwrap(), [{"id": 1, "name": "A"}])
        session.execute("BEGIN")
        session.execute("UPDATE t SET name = 'B' WHERE id = 1")
        session.execute("ROLLBACK")
        self.assertEqual(session.execute("SELECT name FROM t").unwrap(), [{"name": "A"}])


if __name__ == "__main__":
    unittest.main()
