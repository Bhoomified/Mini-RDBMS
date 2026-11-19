import unittest

from mini_rdbms.optimizer.bplus_tree import BPlusTree


class BPlusTreeTest(unittest.TestCase):
    def test_duplicate_and_range_search(self) -> None:
        tree = BPlusTree()
        for key, record_id in [(1, 10), (2, 20), (2, 21), (3, 30)]:
            tree.insert(key, record_id)
        self.assertEqual(tree.search(2), {20, 21})
        self.assertEqual(tree.range_search(2, 3), {20, 21, 30})
        tree.delete(2, 20)
        self.assertEqual(tree.search(2), {21})

    def test_many_keys_split_across_internal_nodes(self) -> None:
        tree = BPlusTree(order=3)
        reference = {}
        for key in range(100):
            tree.insert(key, key * 10)
            reference[key] = {key * 10}
        for key, values in reference.items():
            self.assertEqual(tree.search(key), values)
        self.assertEqual(tree.range_search(25, 74), {key * 10 for key in range(25, 75)})

    def test_delete_redistributes_and_merges_underfull_leaves(self) -> None:
        tree = BPlusTree(order=4)
        for key in range(20):
            tree.insert(key, key)

        for key in (0, 1, 2, 3, 4, 5, 6):
            tree.delete(key, key)

        self.assertEqual(tree.range_search(), set(range(7, 20)))
        self.assertEqual(tree.search(6), set())

    def test_delete_shrinks_root(self) -> None:
        tree = BPlusTree(order=3)
        for key in range(30):
            tree.insert(key, key)
        for key in range(1, 30):
            tree.delete(key, key)

        self.assertEqual(tree.search(0), {0})
        self.assertEqual(tree.range_search(), {0})
        self.assertEqual(len(tree.root.keys), 1)


if __name__ == "__main__":
    unittest.main()
