import unittest

from mini_rdbms.integration.database import Database
from mini_rdbms.integration.session import Session


class IndexWorkflowTest(unittest.TestCase):
    def test_hash_index_and_explain(self) -> None:
        session = Session(Database())
        session.execute("CREATE TABLE t (id INT PRIMARY KEY, name TEXT)")
        session.execute("INSERT INTO t VALUES (1, 'A'), (2, 'B')")
        self.assertTrue(session.execute("CREATE INDEX t_id ON t (id) USING HASH").is_ok)
        explanation = session.execute("EXPLAIN SELECT name FROM t WHERE id = 2").unwrap()
        self.assertEqual(explanation["plan"]["access_path"], "HASH_LOOKUP")
        self.assertEqual(session.execute("SELECT name FROM t WHERE id = 2").unwrap(), [{"name": "B"}])


if __name__ == "__main__":
    unittest.main()
