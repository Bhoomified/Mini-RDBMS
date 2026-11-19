import unittest

from mini_rdbms.common.errors import SyntaxError
from mini_rdbms.common.types import DataType
from mini_rdbms.parser.ast_nodes import (
    CreateTableStatement,
    ExplainStatement,
    SelectStatement,
)
from mini_rdbms.parser.lexer import Lexer
from mini_rdbms.parser.parser import Parser


def parse(sql: str):
    return Parser(Lexer(sql).tokenize()).parse()


class ParserTest(unittest.TestCase):
    def test_parses_create_table(self) -> None:
        statement = parse(
            "CREATE TABLE students (id INT PRIMARY KEY, name TEXT NOT NULL);"
        )

        self.assertIsInstance(statement, CreateTableStatement)
        self.assertEqual(statement.table, "students")
        self.assertEqual(statement.columns[0].data_type, DataType.INT)
        self.assertTrue(statement.columns[0].primary_key)
        self.assertFalse(statement.columns[1].nullable)

    def test_parses_select_with_multiple_conditions(self) -> None:
        statement = parse(
            "SELECT name, age FROM students WHERE age >= 18 AND id = 5"
        )

        self.assertIsInstance(statement, SelectStatement)
        self.assertEqual(statement.columns, ("name", "age"))
        self.assertEqual(statement.conditions[0].operator, ">=")
        self.assertEqual(statement.conditions[1].value, 5)

    def test_parses_explain_without_changing_inner_ast(self) -> None:
        statement = parse("EXPLAIN SELECT * FROM students;")

        self.assertIsInstance(statement, ExplainStatement)
        self.assertEqual(statement.statement.columns, ("*",))

    def test_rejects_missing_from(self) -> None:
        with self.assertRaises(SyntaxError):
            parse("SELECT name students")


if __name__ == "__main__":
    unittest.main()
