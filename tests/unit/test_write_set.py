import unittest

from mini_rdbms.transactions.transaction_manager import TransactionManager


class WriteSetTest(unittest.TestCase):
    def test_transaction_tracks_rows_and_pages(self) -> None:
        transaction = TransactionManager().begin()
        transaction.record_write("items", 4, page_id=2)
        transaction.record_write("items", 5, page_id=3)
        self.assertEqual(transaction.write_set, {"items": {4, 5}})
        self.assertEqual(transaction.modified_pages, {"items": {2, 3}})


if __name__ == "__main__":
    unittest.main()
