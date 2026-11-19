"""Integrity-checking table storage facade."""

from __future__ import annotations

import os
import struct
import io
import hashlib

from mini_rdbms.common.errors import ConstraintError
from mini_rdbms.common.types import DataType, IndexSchema, RecordId, Row, TableSchema

from .heap_file import HeapFile
from .page import PAGE_SIZE
from .page_manager import PageManager
from .record_codec import RecordCodec


class StorageEngine:
    """Apply schema constraints before modifying table rows."""

    def __init__(self) -> None:
        self._tables: dict[str, tuple[TableSchema, HeapFile]] = {}
        self.loaded_indexes: list[IndexSchema] = []

    def save(self, path: str, indexes: tuple[IndexSchema, ...] = ()) -> None:
        """Persist schemas and slotted-page images in a page-framed file."""
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        payload = io.BytesIO()
        payload.write(b"MRDB\x02")
        payload.write(struct.pack(">I", len(self._tables)))
        for table_name, (schema, heap) in self._tables.items():
            heap.validate_pages()
            self._write_string(payload, table_name)
            payload.write(struct.pack(">I", len(schema.columns)))
            for column in schema.columns:
                self._write_string(payload, column.name)
                type_id = list(DataType).index(column.data_type)
                payload.write(
                    struct.pack(
                        ">BBBB", type_id, int(column.nullable), int(column.primary_key), 0
                    )
                )
            images = heap.page_images()
            payload.write(struct.pack(">I", len(images)))
            for image in images:
                payload.write(image)
            locations = heap.locations()
            payload.write(struct.pack(">I", len(locations)))
            for record_id, page_id, slot_id in locations:
                payload.write(struct.pack(">QII", record_id, page_id, slot_id))
        payload.write(struct.pack(">I", len(indexes)))
        for index in indexes:
            self._write_string(payload, index.name)
            self._write_string(payload, index.table_name)
            self._write_string(payload, index.column_name)
            self._write_string(payload, index.index_type)
        raw = payload.getvalue()
        page_count = (len(raw) + PAGE_SIZE - 1) // PAGE_SIZE + 1
        manager = PageManager(path)
        digest = hashlib.sha256(raw).digest()
        superblock = b"MRDP\x01" + struct.pack(">Q", len(raw)) + digest
        manager.write_page(0, superblock.ljust(PAGE_SIZE, b"\x00"))
        for page_id in range(1, page_count):
            start = (page_id - 1) * PAGE_SIZE
            manager.write_page(page_id, raw[start : start + PAGE_SIZE].ljust(PAGE_SIZE, b"\x00"))
        with open(path, "r+b") as file:
            file.truncate(page_count * PAGE_SIZE)
            file.flush()
            os.fsync(file.fileno())

    def load(self, path: str) -> None:
        """Load the custom binary database state if it exists."""
        if not os.path.exists(path):
            return
        from .schema import ColumnSchema, DataType

        with open(path, "rb") as file:
            prefix = file.read(5)
        page_file = prefix == b"MRDP\x01"
        if page_file:
            manager = PageManager(path)
            superblock = manager.read_page(0)
            payload_length = struct.unpack(">Q", superblock[5:13])[0]
            expected_digest = superblock[13:45]
            page_count = (payload_length + PAGE_SIZE - 1) // PAGE_SIZE
            raw = b"".join(manager.read_page(page_id) for page_id in range(1, page_count + 1))
            raw = raw[:payload_length]
            if hashlib.sha256(raw).digest() != expected_digest:
                raise ConstraintError("database page checksum mismatch")
            file = io.BytesIO(raw)
        else:
            file = open(path, "rb")
        with file:
            header = file.read(5)
            if header not in {b"MRDB\x01", b"MRDB\x02"}:
                raise ConstraintError("invalid database file header")
            if header == b"MRDB\x01" and page_file:
                raise ConstraintError("invalid database payload version")
            table_count = struct.unpack(">I", file.read(4))[0]
            for _ in range(table_count):
                name = self._read_string(file)
                columns = []
                raw_columns = []
                column_count = struct.unpack(">I", file.read(4))[0]
                for _ in range(column_count):
                    column_name = self._read_string(file)
                    type_id, nullable, primary_key, _reserved = struct.unpack(">BBBB", file.read(4))
                    data_type = list(DataType)[type_id]
                    raw_columns.append(ColumnSchema(column_name, data_type, bool(nullable), bool(primary_key)))
                schema = TableSchema(name, tuple(raw_columns))
                heap = HeapFile(RecordCodec(schema))
                row_count = struct.unpack(">I", file.read(4))[0]
                if page_file:
                    images = [file.read(PAGE_SIZE) for _ in range(row_count)]
                    location_count = struct.unpack(">I", file.read(4))[0]
                    locations = [struct.unpack(">QII", file.read(16)) for _ in range(location_count)]
                    heap.load_pages(images, locations)
                else:
                    for _ in range(row_count):
                        record_id, value_count = struct.unpack(">QI", file.read(12))
                        if value_count != column_count:
                            raise ConstraintError("invalid persisted row")
                        row = {column.name: self._read_value(file) for column in schema.columns}
                        heap.insert_with_id(record_id, row)
                self._tables[name] = (schema, heap)
            self.loaded_indexes = []
            index_count_data = file.read(4)
            if index_count_data:
                index_count = struct.unpack(">I", index_count_data)[0]
                for _ in range(index_count):
                    self.loaded_indexes.append(
                        IndexSchema(
                            self._read_string(file),
                            self._read_string(file),
                            self._read_string(file),
                            self._read_string(file),
                        )
                    )

    @staticmethod
    def _write_string(file, value: str) -> None:
        encoded = value.encode("utf-8")
        file.write(struct.pack(">I", len(encoded)))
        file.write(encoded)

    @staticmethod
    def _read_string(file) -> str:
        length = struct.unpack(">I", file.read(4))[0]
        return file.read(length).decode("utf-8")

    @staticmethod
    def _write_value(file, value) -> None:
        if value is None:
            file.write(b"\x00")
        elif type(value) is bool:
            file.write(b"\x03" + (b"\x01" if value else b"\x00"))
        elif type(value) is int:
            file.write(b"\x01" + struct.pack(">q", value))
        elif type(value) is float:
            file.write(b"\x02" + struct.pack(">d", value))
        elif type(value) is str:
            encoded = value.encode("utf-8")
            file.write(b"\x04" + struct.pack(">I", len(encoded)) + encoded)
        else:
            raise ConstraintError("unsupported persisted value")

    @staticmethod
    def _read_value(file):
        kind = file.read(1)
        if kind == b"\x00":
            return None
        if kind == b"\x01":
            return struct.unpack(">q", file.read(8))[0]
        if kind == b"\x02":
            return struct.unpack(">d", file.read(8))[0]
        if kind == b"\x03":
            return bool(file.read(1)[0])
        if kind == b"\x04":
            length = struct.unpack(">I", file.read(4))[0]
            return file.read(length).decode("utf-8")
        raise ConstraintError("invalid persisted value")

    def create_table(self, schema: TableSchema) -> None:
        self._tables[schema.name] = (schema, HeapFile(RecordCodec(schema)))

    def schemas(self) -> tuple[TableSchema, ...]:
        return tuple(schema for schema, _heap in self._tables.values())

    def insert(self, table_name: str, row: Row) -> RecordId:
        schema, heap = self._tables[table_name]
        RecordCodec(schema).encode(row)
        primary_key = schema.primary_key
        if primary_key is not None:
            value = row[primary_key.name]
            if any(existing[primary_key.name] == value for _, existing in heap.scan()):
                raise ConstraintError(f"duplicate primary key value {value!r}")
        return heap.insert(row)

    def scan(self, table_name: str):
        return self._tables[table_name][1].scan()

    def fetch(self, table_name: str, record_id: RecordId) -> Row | None:
        return self._tables[table_name][1].fetch(record_id)

    def insert_with_id(self, table_name: str, record_id: RecordId, row: Row) -> None:
        self._tables[table_name][1].insert_with_id(record_id, row)

    def update(self, table_name: str, record_id: RecordId, row: Row) -> None:
        schema, heap = self._tables[table_name]
        RecordCodec(schema).encode(row)
        primary_key = schema.primary_key
        if primary_key is not None:
            value = row[primary_key.name]
            if any(
                rid != record_id and existing[primary_key.name] == value
                for rid, existing in heap.scan()
            ):
                raise ConstraintError(f"duplicate primary key value {value!r}")
        heap.update(record_id, row)

    def delete(self, table_name: str, record_id: RecordId) -> None:
        self._tables[table_name][1].delete(record_id)
