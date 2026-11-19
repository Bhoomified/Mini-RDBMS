import unittest

from mini_rdbms.storage.slotted_page import SlottedPage


class SlottedPageTest(unittest.TestCase):
    def test_round_trip_insert_delete_and_slot_reuse(self) -> None:
        page = SlottedPage(3)
        first = page.insert(b"first")
        second = page.insert(b"second")
        page.delete(first)
        reused = page.insert(b"replacement")

        restored = SlottedPage(3, page.to_bytes())
        self.assertEqual(first, reused)
        self.assertEqual(restored.fetch(second), b"second")
        self.assertEqual(restored.fetch(first), b"replacement")

    def test_serialized_page_has_fixed_size(self) -> None:
        page = SlottedPage(1)
        page.insert(b"record")
        self.assertEqual(len(page.to_bytes()), 4096)


if __name__ == "__main__":
    unittest.main()
