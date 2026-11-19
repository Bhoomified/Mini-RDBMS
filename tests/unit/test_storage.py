import unittest

from mini_rdbms.common.types import ColumnSchema, DataType, TableSchema
from mini_rdbms.storage.record_codec import RecordCodec
from mini_rdbms.storage.heap_file import HeapFile


class RecordCodecTest(unittest.TestCase):
    def test_round_trip_supported_values(self) -> None:
        schema = TableSchema(
            "items",
            (
                ColumnSchema("id", DataType.INT, nullable=False),
                ColumnSchema("price", DataType.FLOAT),
                ColumnSchema("name", DataType.TEXT),
                ColumnSchema("active", DataType.BOOL),
            ),
        )
        row = {"id": 4, "price": 2.5, "name": "café", "active": True}
        self.assertEqual(RecordCodec(schema).decode(RecordCodec(schema).encode(row)), row)

    def test_round_trip_null(self) -> None:
        schema = TableSchema("items", (ColumnSchema("name", DataType.TEXT),))
        codec = RecordCodec(schema)
        self.assertEqual(codec.decode(codec.encode({"name": None})), {"name": None})

    def test_heap_spans_pages_and_preserves_rids_on_relocation(self) -> None:
        schema = TableSchema("items", (ColumnSchema("text", DataType.TEXT),))
        heap = HeapFile(RecordCodec(schema))
        record_id = heap.insert({"text": "small"})
        for _ in range(10):
            heap.insert({"text": "y" * 400})
        heap.update(record_id, {"text": "x" * 3000})
        self.assertGreaterEqual(heap.page_count, 2)
        self.assertEqual(heap.fetch(record_id), {"text": "x" * 3000})


if __name__ == "__main__":
    unittest.main()
