"""Recursive-descent parser for the supported SQL grammar."""

from __future__ import annotations

from collections.abc import Sequence

from mini_rdbms.common.errors import ErrorPosition, SyntaxError
from mini_rdbms.common.types import DataType, Value

from .ast_nodes import (
    ColumnDefinition,
    Condition,
    CreateIndexStatement,
    CreateTableStatement,
    DeleteStatement,
    ExplainStatement,
    InsertStatement,
    SelectStatement,
    Statement,
    TransactionStatement,
    UpdateStatement,
)
from .tokens import Token, TokenType


class Parser:
    """Parse a sequence of lexer tokens into a typed AST."""

    def __init__(self, tokens: Sequence[Token]) -> None:
        self.tokens = list(tokens)
        self._index = 0

    def parse(self) -> Statement | ExplainStatement:
        """Parse one statement and require end-of-input."""
        statement = self.parse_statement()
        self._match(TokenType.SEMICOLON)
        self._expect(TokenType.EOF)
        return statement

    def parse_statement(self) -> Statement | ExplainStatement:
        """Dispatch to the parser for the current statement keyword."""
        keyword = self._keyword_value()
        parsers = {
            "CREATE": self.parse_create,
            "INSERT": self.parse_insert,
            "SELECT": self.parse_select,
            "UPDATE": self.parse_update,
            "DELETE": self.parse_delete,
            "BEGIN": self.parse_begin,
            "COMMIT": self.parse_commit,
            "ROLLBACK": self.parse_rollback,
            "EXPLAIN": self.parse_explain,
        }
        parser = parsers.get(keyword)
        if parser is None:
            self._raise("expected a SQL statement")
        return parser()

    def parse_create(self) -> Statement:
        self._expect_keyword("CREATE")
        if self._match_keyword("TABLE"):
            return self._parse_create_table_body()
        if self._match_keyword("INDEX"):
            return self._parse_create_index_body()
        self._raise("expected TABLE or INDEX after CREATE")

    def parse_insert(self) -> InsertStatement:
        self._expect_keyword("INSERT")
        self._expect_keyword("INTO")
        table = self._expect_identifier()
        columns = None
        if self._match(TokenType.LPAREN):
            columns = tuple(self._parse_identifier_list())
            self._expect(TokenType.RPAREN)
        self._expect_keyword("VALUES")
        values = [self._parse_value_tuple()]
        while self._match(TokenType.COMMA):
            values.append(self._parse_value_tuple())
        return InsertStatement(table, columns, tuple(values))

    def parse_select(self) -> SelectStatement:
        self._expect_keyword("SELECT")
        if self._match_operator("*"):
            columns = ("*",)
        else:
            columns = tuple(self._parse_identifier_list())
        self._expect_keyword("FROM")
        table = self._expect_identifier()
        return SelectStatement(table, columns, self._parse_where())

    def parse_update(self) -> UpdateStatement:
        self._expect_keyword("UPDATE")
        table = self._expect_identifier()
        self._expect_keyword("SET")
        assignments = [self._parse_assignment()]
        while self._match(TokenType.COMMA):
            assignments.append(self._parse_assignment())
        return UpdateStatement(table, tuple(assignments), self._parse_where())

    def parse_delete(self) -> DeleteStatement:
        self._expect_keyword("DELETE")
        self._expect_keyword("FROM")
        table = self._expect_identifier()
        return DeleteStatement(table, self._parse_where())

    def parse_begin(self) -> TransactionStatement:
        self._expect_keyword("BEGIN")
        self._match_keyword("TRANSACTION")
        return TransactionStatement("BEGIN")

    def parse_commit(self) -> TransactionStatement:
        self._expect_keyword("COMMIT")
        return TransactionStatement("COMMIT")

    def parse_rollback(self) -> TransactionStatement:
        self._expect_keyword("ROLLBACK")
        return TransactionStatement("ROLLBACK")

    def parse_explain(self) -> ExplainStatement:
        self._expect_keyword("EXPLAIN")
        return ExplainStatement(self.parse_statement())

    def _parse_create_table_body(self) -> CreateTableStatement:
        table = self._expect_identifier()
        self._expect(TokenType.LPAREN)
        columns = [self._parse_column_definition()]
        while self._match(TokenType.COMMA):
            columns.append(self._parse_column_definition())
        self._expect(TokenType.RPAREN)
        return CreateTableStatement(table, tuple(columns))

    def _parse_create_index_body(self) -> CreateIndexStatement:
        name = self._expect_identifier()
        self._expect_keyword("ON")
        table = self._expect_identifier()
        self._expect(TokenType.LPAREN)
        column = self._expect_identifier()
        self._expect(TokenType.RPAREN)
        index_type = "HASH"
        if self._match_keyword("USING"):
            index_type = self._expect_keyword_value("HASH", "BTREE")
        return CreateIndexStatement(name, table, column, index_type)

    def _parse_column_definition(self) -> ColumnDefinition:
        name = self._expect_identifier()
        data_type = self._parse_data_type()
        nullable = True
        primary_key = False
        if self._match_keyword("NOT"):
            self._expect_keyword("NULL")
            nullable = False
        if self._match_keyword("PRIMARY"):
            self._expect_keyword("KEY")
            primary_key = True
            nullable = False
        return ColumnDefinition(name, data_type, nullable, primary_key)

    def _parse_data_type(self) -> DataType:
        value = self._expect_keyword_value(
            "INT", "INTEGER", "FLOAT", "REAL", "TEXT", "BOOL", "BOOLEAN"
        )
        return {
            "INT": DataType.INT,
            "INTEGER": DataType.INT,
            "FLOAT": DataType.FLOAT,
            "REAL": DataType.FLOAT,
            "TEXT": DataType.TEXT,
            "BOOL": DataType.BOOL,
            "BOOLEAN": DataType.BOOL,
        }[value]

    def _parse_identifier_list(self) -> list[str]:
        identifiers = [self._expect_identifier()]
        while self._match(TokenType.COMMA):
            identifiers.append(self._expect_identifier())
        return identifiers

    def _parse_value_tuple(self) -> tuple[Value, ...]:
        self._expect(TokenType.LPAREN)
        values = [self._parse_value()]
        while self._match(TokenType.COMMA):
            values.append(self._parse_value())
        self._expect(TokenType.RPAREN)
        return tuple(values)

    def _parse_assignment(self) -> tuple[str, Value]:
        column = self._expect_identifier()
        self._expect_operator("=")
        return column, self._parse_value()

    def _parse_where(self) -> tuple[Condition, ...]:
        if not self._match_keyword("WHERE"):
            return ()
        conditions = [self._parse_condition()]
        while self._match_keyword("AND"):
            conditions.append(self._parse_condition())
        return tuple(conditions)

    def _parse_condition(self) -> Condition:
        column = self._expect_identifier()
        operator = self._expect_operator_value("=", "!=", "<>", "<", "<=", ">", ">=")
        return Condition(column, operator, self._parse_value())

    def _parse_value(self) -> Value:
        token = self._current()
        if token.token_type in {
            TokenType.INTEGER,
            TokenType.FLOAT,
            TokenType.STRING,
        }:
            self._index += 1
            return token.value
        if token.token_type is TokenType.KEYWORD and token.value == "NULL":
            self._index += 1
            return None
        if token.token_type is TokenType.KEYWORD and token.value in {"TRUE", "FALSE"}:
            self._index += 1
            return token.value == "TRUE"
        self._raise("expected a literal value")

    def _current(self) -> Token:
        return self.tokens[min(self._index, len(self.tokens) - 1)]

    def _keyword_value(self) -> str | None:
        token = self._current()
        return token.value if token.token_type is TokenType.KEYWORD else None

    def _expect_identifier(self) -> str:
        token = self._current()
        if token.token_type is not TokenType.IDENTIFIER:
            self._raise("expected an identifier")
        self._index += 1
        return token.value

    def _expect(self, token_type: TokenType) -> Token:
        token = self._current()
        if token.token_type is not token_type:
            self._raise(f"expected {token_type.value}")
        self._index += 1
        return token

    def _expect_keyword(self, keyword: str) -> None:
        if not self._match_keyword(keyword):
            self._raise(f"expected keyword {keyword}")

    def _expect_keyword_value(self, *keywords: str) -> str:
        token = self._current()
        if token.token_type is not TokenType.KEYWORD or token.value not in keywords:
            self._raise(f"expected one of {', '.join(keywords)}")
        self._index += 1
        return token.value

    def _expect_operator(self, operator: str) -> None:
        if not self._match_operator(operator):
            self._raise(f"expected operator {operator}")

    def _expect_operator_value(self, *operators: str) -> str:
        token = self._current()
        if token.token_type is not TokenType.OPERATOR or token.value not in operators:
            self._raise(f"expected one of {', '.join(operators)}")
        self._index += 1
        return token.value

    def _match(self, token_type: TokenType) -> bool:
        if self._current().token_type is token_type:
            self._index += 1
            return True
        return False

    def _match_keyword(self, keyword: str) -> bool:
        if self._keyword_value() == keyword:
            self._index += 1
            return True
        return False

    def _match_operator(self, operator: str) -> bool:
        token = self._current()
        if token.token_type is TokenType.OPERATOR and token.value == operator:
            self._index += 1
            return True
        return False

    def _raise(self, message: str) -> None:
        token = self._current()
        raise SyntaxError(
            message,
            position=ErrorPosition(
                offset=token.offset,
                line=token.line,
                column=token.column,
            ),
        )
