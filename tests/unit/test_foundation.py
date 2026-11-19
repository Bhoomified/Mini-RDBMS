import unittest

from mini_rdbms import __version__
from mini_rdbms.common.errors import ErrorPosition, LexicalError
from mini_rdbms.common.result import Result
from mini_rdbms.common.types import ColumnSchema, DataType, TableSchema


class FoundationTest(unittest.TestCase):
    """Verify that the initial package foundation is importable."""

    def test_package_version_is_defined(self) -> None:
        self.assertEqual(__version__, "0.1.0")

    def test_result_can_unwrap_success_and_failure(self) -> None:
        success = Result.ok(42)
        failure = Result.fail(LexicalError("invalid character"))

        self.assertTrue(success.is_ok)
        self.assertEqual(success.unwrap(), 42)
        self.assertFalse(failure.is_ok)
        with self.assertRaises(LexicalError):
            failure.unwrap()

    def test_schema_exposes_columns_and_primary_key(self) -> None:
        schema = TableSchema(
            name="students",
            columns=(
                ColumnSchema("id", DataType.INT, nullable=False, primary_key=True),
                ColumnSchema("name", DataType.TEXT),
            ),
        )

        self.assertTrue(schema.has_column("name"))
        self.assertEqual(schema.primary_key.name, "id")

    def test_error_includes_source_position(self) -> None:
        error = LexicalError(
            "unexpected character",
            position=ErrorPosition(line=2, column=4),
        )

        self.assertIn("line 2, column 4", str(error))


if __name__ == "__main__":
    unittest.main()
