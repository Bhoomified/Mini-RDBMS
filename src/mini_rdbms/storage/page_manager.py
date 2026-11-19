"""Thread-safe fixed-page file manager."""

from __future__ import annotations

import os
import threading

from mini_rdbms.common.errors import StorageError

from .page import PAGE_SIZE


class PageManager:
    """Read and write exactly one fixed-size page at a time."""

    def __init__(self, path: str) -> None:
        self.path = path
        self._lock = threading.RLock()
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

    def read_page(self, page_id: int) -> bytes:
        """Read a complete page from disk."""
        if page_id < 0:
            raise StorageError("page ID cannot be negative")
        with self._lock, open(self.path, "rb") as file:
            file.seek(page_id * PAGE_SIZE)
            data = file.read(PAGE_SIZE)
        if len(data) != PAGE_SIZE:
            raise StorageError("requested page is missing or truncated")
        return data

    def write_page(self, page_id: int, data: bytes) -> None:
        """Write one complete page and flush it to disk."""
        if page_id < 0 or len(data) != PAGE_SIZE:
            raise StorageError("page ID or page size is invalid")
        with self._lock, open(self.path, "a+b") as file:
            file.seek(page_id * PAGE_SIZE)
            file.write(data)
            file.flush()
            os.fsync(file.fileno())
