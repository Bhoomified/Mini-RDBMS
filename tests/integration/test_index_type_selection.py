import unittest

from mini_rdbms.integration.database import Database
from mini_rdbms.integration.session import Session


class IndexTypeSelectionTest(unittest.TestCase):
    def test_range_query_adds_btree_even_when_hash_index_exists(self) -> None:
        session = Session(Database())
        session.execute("CREATE TABLE menu_items (price INT)")
        session.execute("INSERT INTO menu_items VALUES (80), (100), (150)")
        session.execute("CREATE INDEX menu_price_hash ON menu_items (price) USING HASH")
        result = session.execute(
            "EXPLAIN SELECT * FROM menu_items WHERE price >= 100"
        ).unwrap()
        self.assertEqual(result["plan"]["access_path"], "BTREE_RANGE")
        session.execute("SELECT * FROM menu_items WHERE price >= 100")
        self.assertTrue(
            any(index.index_type == "BTREE" for index in session.database.catalog.indexes())
        )


if __name__ == "__main__":
    unittest.main()
