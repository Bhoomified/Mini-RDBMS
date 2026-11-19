import unittest

from mini_rdbms.optimizer.hash_index import HashIndex


class HashIndexTest(unittest.TestCase):
    def test_insert_lookup_update_and_remove(self) -> None:
        index = HashIndex()
        index.insert("A", 1)
        index.insert("A", 2)
        index.update("A", "B", 1)
        index.remove("A", 2)
        self.assertEqual(index.search("A"), set())
        self.assertEqual(index.search("B"), {1})


if __name__ == "__main__":
    unittest.main()
