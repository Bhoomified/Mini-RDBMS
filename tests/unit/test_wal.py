import os
import tempfile
import unittest

from mini_rdbms.storage.wal import COMMIT, PAGE_IMAGE, WriteAheadLog


class WalTest(unittest.TestCase):
    def test_only_committed_payloads_are_recovered(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            wal = WriteAheadLog(os.path.join(directory, "wal"))
            wal.append(1, PAGE_IMAGE, b"committed")
            wal.append(1, COMMIT, b"")
            wal.append(2, PAGE_IMAGE, b"uncommitted")
            self.assertEqual(wal.recover(), [(1, b"committed")])

    def test_recovery_preserves_page_ids(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            wal = WriteAheadLog(os.path.join(directory, "wal"))
            wal.append(4, PAGE_IMAGE, b"page", page_id=3)
            wal.append(4, COMMIT, b"")
            self.assertEqual(wal.recover_pages(), [(4, 3, b"page")])


if __name__ == "__main__":
    unittest.main()
