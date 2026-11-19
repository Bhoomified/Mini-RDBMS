"""Schema-driven binary record encoding."""

from __future__ import annotations

import struct

from mini_rdbms.common.errors import StorageError
from mini_rdbms.common.types import Row, TableSchema


class RecordCodec:
    """Encode and decode rows without object serialization."""

    def __init__(self, schema: TableSchema) -> None:
        self.schema = schema

    def encode(self, row: Row) -> bytes:
        """Encode a row according to the table schema."""
        expected = {column.name for column in self.schema.columns}
        if set(row) != expected:
            raise StorageError("row columns do not match table schema")
        nulls = bytearray((len(self.schema.columns) + 7) // 8)
        payload = bytearray()
        for index, column in enumerate(self.schema.columns):
            value = row[column.name]
            if value is None:
                if not column.nullable:
                    raise StorageError(f"column {column.name!r} cannot be NULL")
                nulls[index // 8] |= 1 << (index % 8)
                continue
            if column.data_type.value == "INT":
                if type(value) is not int:
                    raise StorageError(f"invalid INT value for {column.name!r}")
                payload.extend(struct.pack(">q", value))
            elif column.data_type.value == "FLOAT":
                if type(value) not in {int, float}:
                    raise StorageError(f"invalid FLOAT value for {column.name!r}")
                payload.extend(struct.pack(">d", float(value)))
            elif column.data_type.value == "BOOL":
                if type(value) is not bool:
                    raise StorageError(f"invalid BOOL value for {column.name!r}")
                payload.extend(b"\x01" if value else b"\x00")
            elif column.data_type.value == "TEXT":
                if type(value) is not str:
                    raise StorageError(f"invalid TEXT value for {column.name!r}")
                encoded = value.encode("utf-8")
                payload.extend(struct.pack(">I", len(encoded)))
                payload.extend(encoded)
        return bytes(nulls + payload)

    def decode(self, data: bytes) -> Row:
        """Decode one binary row and reject truncated data."""
        null_length = (len(self.schema.columns) + 7) // 8
        if len(data) < null_length:
            raise StorageError("truncated record null bitmap")
        nulls, offset = data[:null_length], null_length
        row: Row = {}
        for index, column in enumerate(self.schema.columns):
            if nulls[index // 8] & (1 << (index % 8)):
                row[column.name] = None
                continue
            try:
                if column.data_type.value == "INT":
                    row[column.name] = struct.unpack_from(">q", data, offset)[0]
                    offset += 8
                elif column.data_type.value == "FLOAT":
                    row[column.name] = struct.unpack_from(">d", data, offset)[0]
                    offset += 8
                elif column.data_type.value == "BOOL":
                    row[column.name] = bool(data[offset])
                    offset += 1
                else:
                    length = struct.unpack_from(">I", data, offset)[0]
                    offset += 4
                    row[column.name] = data[offset : offset + length].decode("utf-8")
                    offset += length
            except (IndexError, struct.error, UnicodeDecodeError) as error:
                raise StorageError("truncated or invalid record") from error
        if offset != len(data):
            raise StorageError("record contains trailing bytes")
        return row
