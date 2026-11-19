import unittest

from mini_rdbms.integration.database import Database
from mini_rdbms.integration.session import Session


class AutomaticBTreeTest(unittest.TestCase):
    def test_comparator_creates_and_uses_ordered_index(self) -> None:
        session = Session(Database())
        session.execute("CREATE TABLE menu_items (item_name TEXT, price INT)")
        session.execute(
            "INSERT INTO menu_items VALUES ('Tea', 100), ('Cake', 150), ('Soup', 80)"
        )
        rows = session.execute(
            "SELECT item_name FROM menu_items WHERE price >= 100"
        ).unwrap()
        self.assertEqual(
            {row["item_name"] for row in rows},
            {"Tea", "Cake"},
        )
        plan = session.execute(
            "EXPLAIN SELECT item_name FROM menu_items WHERE price >= 100"
        ).unwrap()["plan"]
        self.assertEqual(plan["access_path"], "BTREE_RANGE")


if __name__ == "__main__":
    unittest.main()
