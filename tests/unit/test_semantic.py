import unittest

from mini_rdbms.common.types import ColumnSchema, DataType, TableSchema
from mini_rdbms.parser.lexer import Lexer
from mini_rdbms.parser.parser import Parser
from mini_rdbms.parser.semantic import SemanticAnalyzer


class CatalogStub:
    def __init__(self) -> None:
        self.tables = {
            "students": TableSchema(
                "students",
                (
                    ColumnSchema("id", DataType.INT, nullable=False, primary_key=True),
                    ColumnSchema("name", DataType.TEXT, nullable=False),
                    ColumnSchema("age", DataType.INT),
                ),
            )
        }

    def get_table(self, name):
        return self.tables.get(name)

    def get_index(self, name):
        return None

    def list_tables(self):
        return tuple(self.tables.values())


def validate(sql: str):
    ast = Parser(Lexer(sql).tokenize()).parse()
    return SemanticAnalyzer(CatalogStub()).validate(ast)


class SemanticTest(unittest.TestCase):
    def test_accepts_valid_select(self) -> None:
        self.assertTrue(validate("SELECT name FROM students WHERE age >= 18").is_ok)

    def test_rejects_unknown_table_and_column(self) -> None:
        self.assertFalse(validate("SELECT name FROM missing").is_ok)
        self.assertFalse(validate("SELECT missing FROM students").is_ok)

    def test_rejects_invalid_literal_type(self) -> None:
        result = validate("INSERT INTO students (id, name, age) VALUES ('bad', 'A', 1)")
        self.assertFalse(result.is_ok)

    def test_rejects_duplicate_create_table_columns(self) -> None:
        ast = Parser(Lexer("CREATE TABLE t (id INT, id TEXT)").tokenize()).parse()
        self.assertFalse(SemanticAnalyzer(CatalogStub()).validate(ast).is_ok)


if __name__ == "__main__":
    unittest.main()
