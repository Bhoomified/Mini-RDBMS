"""Token definitions produced by the SQL lexer."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class TokenType(str, Enum):
    """Kinds of lexical units recognized by the SQL lexer."""

    KEYWORD = "KEYWORD"
    IDENTIFIER = "IDENTIFIER"
    INTEGER = "INTEGER"
    FLOAT = "FLOAT"
    STRING = "STRING"
    OPERATOR = "OPERATOR"
    LPAREN = "LPAREN"
    RPAREN = "RPAREN"
    COMMA = "COMMA"
    SEMICOLON = "SEMICOLON"
    EOF = "EOF"


@dataclass(frozen=True)
class Token:
    """A token and its source location."""

    token_type: TokenType
    value: Any
    offset: int
    line: int
    column: int

    def __str__(self) -> str:
        return f"{self.token_type.value}({self.value})"
