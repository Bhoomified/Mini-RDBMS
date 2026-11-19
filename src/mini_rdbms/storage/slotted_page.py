"""Variable-length records stored in a fixed-size slotted page."""

from __future__ import annotations

import struct

from mini_rdbms.common.errors import StorageError

from .page import HEADER_SIZE, PAGE_SIZE, PageHeader

SLOT_FORMAT = ">HH"
SLOT_SIZE = struct.calcsize(SLOT_FORMAT)


class SlottedPage:
    """Store records with stable slot identifiers and compaction."""

    def __init__(self, page_id: int, raw: bytes | None = None) -> None:
        self.page_id = page_id
        self._records: list[bytes | None] = []
        if raw is not None:
            self._load(raw)

    def insert(self, record: bytes) -> int:
        """Insert a record and return its stable slot ID."""
        reusable = next((i for i, item in enumerate(self._records) if item is None), None)
        if reusable is not None:
            candidate = list(self._records)
            candidate[reusable] = record
            if self._fits(candidate):
                self._records = candidate
                return reusable
        candidate = self._records + [record]
        if not self._fits(candidate):
            raise StorageError("record does not fit on page")
        self._records = candidate
        return len(candidate) - 1

    def fetch(self, slot_id: int) -> bytes | None:
        """Return a record or None for a deleted slot."""
        self._check_slot(slot_id)
        return self._records[slot_id]

    def delete(self, slot_id: int) -> None:
        """Delete a slot while preserving its logical slot ID."""
        self._check_slot(slot_id)
        self._records[slot_id] = None

    def update(self, slot_id: int, record: bytes) -> None:
        """Replace a record, relocating it through compaction if needed."""
        self._check_slot(slot_id)
        candidate = list(self._records)
        candidate[slot_id] = record
        if not self._fits(candidate):
            raise StorageError("updated record does not fit on page")
        self._records = candidate

    def to_bytes(self) -> bytes:
        """Serialize this page to exactly PAGE_SIZE bytes."""
        slot_count = len(self._records)
        slot_end = HEADER_SIZE + slot_count * SLOT_SIZE
        data_end = PAGE_SIZE
        slots: list[tuple[int, int]] = []
        data = bytearray(PAGE_SIZE)
        for record in reversed(self._records):
            if record is None:
                slots.append((0, 0))
                continue
            data_end -= len(record)
            data[data_end : data_end + len(record)] = record
            slots.append((data_end, len(record)))
        slots.reverse()
        header = PageHeader(self.page_id, slot_count, slot_end, data_end)
        data[:HEADER_SIZE] = header.pack()
        for index, (offset, length) in enumerate(slots):
            start = HEADER_SIZE + index * SLOT_SIZE
            data[start : start + SLOT_SIZE] = struct.pack(SLOT_FORMAT, offset, length)
        return bytes(data)

    def _load(self, raw: bytes) -> None:
        if len(raw) != PAGE_SIZE:
            raise StorageError("page must be exactly 4096 bytes")
        header = PageHeader.unpack(raw)
        if header.page_id != self.page_id:
            raise StorageError("page ID mismatch")
        self._records = []
        for index in range(header.slot_count):
            start = HEADER_SIZE + index * SLOT_SIZE
            offset, length = struct.unpack(SLOT_FORMAT, raw[start : start + SLOT_SIZE])
            if length == 0:
                self._records.append(None)
            else:
                if offset < header.free_end or offset + length > PAGE_SIZE:
                    raise StorageError("invalid slot bounds")
                self._records.append(bytes(raw[offset : offset + length]))

    @staticmethod
    def _fits(records: list[bytes | None]) -> bool:
        slot_end = HEADER_SIZE + len(records) * SLOT_SIZE
        data_size = sum(len(record) for record in records if record is not None)
        return slot_end + data_size <= PAGE_SIZE

    def _check_slot(self, slot_id: int) -> None:
        if not 0 <= slot_id < len(self._records):
            raise StorageError(f"invalid slot ID {slot_id}")
