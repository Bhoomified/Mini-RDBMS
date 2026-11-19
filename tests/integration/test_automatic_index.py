import unittest

from mini_rdbms.integration.database import Database
from mini_rdbms.integration.session import Session


class AutomaticIndexTest(unittest.TestCase):
    def test_equality_query_creates_and_uses_hash_index_automatically(self) -> None:
        session = Session(Database())
        session.execute("CREATE TABLE menu_items (item_name TEXT, price INT)")
        session.execute("INSERT INTO menu_items VALUES ('Tea', 100)")

        result = session.execute(
            "SELECT item_name FROM menu_items WHERE price = 100"
        )
        self.assertEqual(result.unwrap(), [{"item_name": "Tea"}])

        explanation = session.execute(
            "EXPLAIN SELECT item_name FROM menu_items WHERE price = 100"
        ).unwrap()
        self.assertEqual(explanation["plan"]["access_path"], "HASH_LOOKUP")


if __name__ == "__main__":
    unittest.main()
