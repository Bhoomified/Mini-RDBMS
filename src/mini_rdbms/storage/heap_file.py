"""Heap-file organization over slotted pages."""

from __future__ import annotations

from mini_rdbms.common.types import RecordId, Row
from mini_rdbms.common.errors import StorageError

from .slotted_page import SlottedPage


class HeapFile:
    """Store encoded rows across slotted pages with stable logical RIDs."""

    def __init__(self, codec=None) -> None:
        self.codec = codec
        self._pages: list[SlottedPage] = [SlottedPage(0)]
        self._locations: dict[RecordId, tuple[int, int]] = {}
        self._next_id = 1

    @property
    def page_count(self) -> int:
        """Return the number of allocated heap pages."""
        return len(self._pages)

    def page_images(self) -> tuple[bytes, ...]:
        """Return serialized page images for WAL or diagnostics."""
        return tuple(page.to_bytes() for page in self._pages)

    def locations(self) -> tuple[tuple[RecordId, int, int], ...]:
        """Return stable record-to-page slot mappings for persistence."""
        return tuple(
            (record_id, page_id, slot_id)
            for record_id, (page_id, slot_id) in sorted(self._locations.items())
        )

    def load_pages(
        self,
        images: list[bytes],
        locations: list[tuple[RecordId, int, int]],
    ) -> None:
        """Restore heap pages and logical RIDs from fixed-size page images."""
        if not images:
            raise StorageError("a heap file must contain at least one page")
        pages = [SlottedPage(page_id, image) for page_id, image in enumerate(images)]
        for record_id, page_id, slot_id in locations:
            if not 0 <= page_id < len(pages):
                raise StorageError("record references an invalid page")
            if pages[page_id].fetch(slot_id) is None:
                raise StorageError("record references an empty slot")
        self._pages = pages
        self._locations = {
            record_id: (page_id, slot_id)
            for record_id, page_id, slot_id in locations
        }
        self._next_id = max(self._locations, default=0) + 1

    def validate_pages(self) -> None:
        """Round-trip every page image to detect invalid page state."""
        for page_id, image in enumerate(self.page_images()):
            SlottedPage(page_id, image)

    def insert(self, row: Row) -> RecordId:
        record_id = self._next_id
        self.insert_with_id(record_id, row)
        return record_id

    def insert_with_id(self, record_id: RecordId, row: Row) -> None:
        """Insert or restore a row and preserve its logical RID."""
        encoded = self._encode(row)
        for page_id, page in enumerate(self._pages):
            try:
                slot_id = page.insert(encoded)
                self._locations[record_id] = (page_id, slot_id)
                self._next_id = max(self._next_id, record_id + 1)
                return
            except StorageError:
                continue
        page = SlottedPage(len(self._pages))
        slot_id = page.insert(encoded)
        self._pages.append(page)
        self._locations[record_id] = (len(self._pages) - 1, slot_id)
        self._next_id = max(self._next_id, record_id + 1)

    def fetch(self, record_id: RecordId) -> Row | None:
        location = self._locations.get(record_id)
        if location is None:
            return None
        page_id, slot_id = location
        encoded = self._pages[page_id].fetch(slot_id)
        return None if encoded is None else self._decode(encoded)

    def scan(self):
        for record_id in sorted(self._locations):
            row = self.fetch(record_id)
            if row is not None:
                yield record_id, row

    def update(self, record_id: RecordId, row: Row) -> None:
        page_id, slot_id = self._locations[record_id]
        encoded = self._encode(row)
        try:
            self._pages[page_id].update(slot_id, encoded)
        except Exception:
            self._pages[page_id].delete(slot_id)
            self.insert_with_id(record_id, row)

    def delete(self, record_id: RecordId) -> None:
        location = self._locations.pop(record_id, None)
        if location is not None:
            self._pages[location[0]].delete(location[1])

    def _encode(self, row: Row) -> bytes:
        return self.codec.encode(row) if self.codec else repr(row).encode("utf-8")

    def _decode(self, data: bytes) -> Row:
        if self.codec:
            return self.codec.decode(data)
        raise ValueError("a record codec is required to decode heap rows")
