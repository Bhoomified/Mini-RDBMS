import unittest

from mini_rdbms.integration.database import Database
from mini_rdbms.integration.session import Session


class IndexExplainGuidanceTest(unittest.TestCase):
    def test_explain_guides_missing_index_and_uses_created_hash_index(self) -> None:
        session = Session(Database())
        session.execute("CREATE TABLE menu_items (item_name TEXT, price INT)")
        before = session.execute(
            "EXPLAIN SELECT item_name FROM menu_items WHERE price = 100"
        ).unwrap()
        self.assertEqual(before["plan"]["access_path"], "HASH_LOOKUP")
        self.assertIn("automatic hash index", before["plan"]["reason"])

        session.execute(
            "CREATE INDEX menu_items_price ON menu_items (price) USING HASH"
        )
        after = session.execute(
            "EXPLAIN SELECT item_name FROM menu_items WHERE price = 100"
        ).unwrap()
        self.assertEqual(after["plan"]["access_path"], "HASH_LOOKUP")


if __name__ == "__main__":
    unittest.main()
