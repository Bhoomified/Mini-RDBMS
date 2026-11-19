"""Database facade combining catalog, storage, and transactions."""

from __future__ import annotations

import os
import tempfile

from mini_rdbms.storage.catalog import Catalog
from mini_rdbms.storage.storage_engine import StorageEngine
from mini_rdbms.storage.wal import BEGIN, COMMIT, PAGE_IMAGE, WriteAheadLog
from mini_rdbms.storage.page import PAGE_SIZE
from mini_rdbms.storage.page_manager import PageManager
from mini_rdbms.common.errors import StorageError
from mini_rdbms.transactions.transaction_manager import TransactionManager


class Database:
    """Own shared database components for multiple sessions."""

    def __init__(self, path: str | None = None) -> None:
        self.path = path
        self.catalog = Catalog()
        self.storage = StorageEngine()
        self.wal = WriteAheadLog(f"{path}.wal") if path else None
        from mini_rdbms.optimizer.index_manager import IndexManager
        self.indexes = IndexManager()
        if self.path:
            self._recover_wal()
            self.storage.load(self.path)
            for schema in self.storage.schemas():
                self.catalog.create_table(schema)
            for index in self.storage.loaded_indexes:
                self.catalog.create_index(index)
                self.indexes.create(index.name, index.index_type, index.table_name, index.column_name)
                for record_id, row in self.storage.scan(index.table_name):
                    self.indexes.insert(index.name, row[index.column_name], record_id)
        self.transactions = TransactionManager()

    def close(self) -> None:
        """Close the database facade."""
        if self.path:
            self.persist()

    def persist(self, failure_stage: str | None = None) -> None:
        """Durably commit one complete binary database image through the WAL."""
        if not self.path or self.wal is None:
            return
        directory = os.path.dirname(self.path) or "."
        fd, temporary_path = tempfile.mkstemp(prefix=".minirdb-", dir=directory)
        os.close(fd)
        try:
            self.storage.save(temporary_path, self.catalog.indexes())
            with open(temporary_path, "rb") as file:
                image = file.read()
            self.wal.append(1, BEGIN, b"")
            for page_id in range(0, len(image), PAGE_SIZE):
                page = image[page_id : page_id + PAGE_SIZE]
                self.wal.append(1, PAGE_IMAGE, page.ljust(PAGE_SIZE, b"\x00"), page_id=page_id // PAGE_SIZE)
            self.wal.append(1, COMMIT, b"")
            if failure_stage == "after_wal":
                raise StorageError("injected failure after WAL commit")
            with open(self.path, "wb"):
                pass
            manager = PageManager(self.path)
            for page_id in range(0, len(image), PAGE_SIZE):
                manager.write_page(
                    page_id // PAGE_SIZE,
                    image[page_id : page_id + PAGE_SIZE].ljust(PAGE_SIZE, b"\x00"),
                )
            if failure_stage == "after_replace":
                raise StorageError("injected failure after database replace")
            self.wal.clear()
        finally:
            if os.path.exists(temporary_path):
                os.remove(temporary_path)

    def _recover_wal(self) -> None:
        if not self.path or self.wal is None:
            return
        recovered = self.wal.recover_pages()
        if recovered:
            if len(recovered) == 1 and len(recovered[0][2]) != PAGE_SIZE:
                with open(self.path, "wb") as file:
                    file.write(recovered[0][2])
                    file.flush()
                    os.fsync(file.fileno())
            else:
                with open(self.path, "wb"):
                    pass
                manager = PageManager(self.path)
                for _transaction_id, page_id, payload in recovered:
                    if len(payload) != PAGE_SIZE:
                        raise StorageError("committed WAL page has invalid size")
                    manager.write_page(page_id, payload)
            self.wal.clear()
