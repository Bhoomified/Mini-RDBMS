import unittest

from mini_rdbms.integration.database import Database
from mini_rdbms.integration.session import Session


class TransactionIntegrityTest(unittest.TestCase):
    def test_update_rollback_restores_index_lookup(self) -> None:
        session = Session(Database())
        session.execute("CREATE TABLE items (id INT PRIMARY KEY, price INT)")
        session.execute("INSERT INTO items VALUES (1, 100)")
        session.execute("CREATE INDEX items_price ON items (price) USING HASH")
        session.execute("BEGIN")
        session.execute("UPDATE items SET price = 200 WHERE id = 1")
        session.execute("ROLLBACK")

        self.assertEqual(
            session.execute("SELECT id FROM items WHERE price = 100").unwrap(),
            [{"id": 1}],
        )
        self.assertEqual(
            session.execute("SELECT id FROM items WHERE price = 200").unwrap(),
            [],
        )

    def test_duplicate_multi_insert_is_atomic(self) -> None:
        session = Session(Database())
        session.execute("CREATE TABLE students (id INT PRIMARY KEY, name TEXT)")
        result = session.execute(
            "INSERT INTO students VALUES (1, 'A'), (1, 'B')"
        )
        self.assertFalse(result.is_ok)
        self.assertEqual(session.execute("SELECT * FROM students").unwrap(), [])

    def test_failed_statement_rolls_back_explicit_transaction(self) -> None:
        session = Session(Database())
        session.execute("CREATE TABLE students (id INT PRIMARY KEY, name TEXT)")
        session.execute("BEGIN")
        session.execute("INSERT INTO students VALUES (1, 'A')")
        failed = session.execute("INSERT INTO students VALUES (1, 'B')")
        self.assertFalse(failed.is_ok)
        self.assertEqual(session.execute("SELECT * FROM students").unwrap(), [])


if __name__ == "__main__":
    unittest.main()
