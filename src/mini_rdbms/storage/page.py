"""Fixed-size page primitives."""

from __future__ import annotations

import struct
from dataclasses import dataclass

from mini_rdbms.common.errors import StorageError

PAGE_SIZE = 4096
PAGE_MAGIC = b"MRPG"
HEADER_FORMAT = ">4sIHHI"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)


@dataclass
class PageHeader:
    """Header fields common to every page."""

    page_id: int
    slot_count: int
    free_start: int
    free_end: int

    def pack(self) -> bytes:
        return struct.pack(
            HEADER_FORMAT, PAGE_MAGIC, self.page_id, self.slot_count, self.free_start, self.free_end
        )

    @classmethod
    def unpack(cls, data: bytes) -> "PageHeader":
        if len(data) < HEADER_SIZE:
            raise StorageError("page header is truncated")
        magic, page_id, slots, free_start, free_end = struct.unpack(
            HEADER_FORMAT, data[:HEADER_SIZE]
        )
        if magic != PAGE_MAGIC or not HEADER_SIZE <= free_start <= free_end <= PAGE_SIZE:
            raise StorageError("invalid page header")
        return cls(page_id, slots, free_start, free_end)
