"""Regular-expression-based SQL lexer."""

from __future__ import annotations

import re
from typing import Iterator

from mini_rdbms.common.errors import ErrorPosition, LexicalError

from .keywords import KEYWORDS
from .tokens import Token, TokenType


class Lexer:
    """Tokenize the supported SQL subset from left to right."""

    _identifier = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
    _number = re.compile(r"(?:\d+\.\d+|\d+)")
    _operators = re.compile(r"(?P<long>>=|<=|!=|<>|==)|(?P<short>[=<>*+\-/])")

    def __init__(self, source: str) -> None:
        self.source = source
        self._index = 0
        self._line = 1
        self._column = 1

    def tokenize(self) -> list[Token]:
        """Return all tokens, including a final EOF token."""
        tokens = list(self)
        tokens.append(
            Token(
                TokenType.EOF,
                "",
                self._index,
                self._line,
                self._column,
            )
        )
        return tokens

    def __iter__(self) -> Iterator[Token]:
        while self._index < len(self.source):
            character = self.source[self._index]
            if character.isspace():
                self._advance(character)
                continue
            if self.source.startswith("--", self._index):
                self._skip_comment()
                continue

            token = self._read_token()
            if token is None:
                position = ErrorPosition(
                    offset=self._index,
                    line=self._line,
                    column=self._column,
                )
                raise LexicalError(
                    f"unexpected character {character!r}",
                    position=position,
                )
            yield token

    def _read_token(self) -> Token | None:
        offset, line, column = self._index, self._line, self._column
        character = self.source[self._index]

        if character == "'":
            return self._read_string(offset, line, column)

        identifier = self._identifier.match(self.source, self._index)
        if identifier:
            value = identifier.group(0)
            self._advance_text(value)
            keyword = KEYWORDS.get(value.upper())
            if keyword is not None:
                return Token(TokenType.KEYWORD, keyword, offset, line, column)
            return Token(TokenType.IDENTIFIER, value, offset, line, column)

        number = self._number.match(self.source, self._index)
        if number:
            value = number.group(0)
            self._advance_text(value)
            token_type = TokenType.FLOAT if "." in value else TokenType.INTEGER
            parsed_value = float(value) if token_type is TokenType.FLOAT else int(value)
            return Token(token_type, parsed_value, offset, line, column)

        operator = self._operators.match(self.source, self._index)
        if operator:
            value = operator.group(0)
            self._advance_text(value)
            return Token(TokenType.OPERATOR, value, offset, line, column)

        punctuation = {
            "(": TokenType.LPAREN,
            ")": TokenType.RPAREN,
            ",": TokenType.COMMA,
            ";": TokenType.SEMICOLON,
        }.get(character)
        if punctuation is not None:
            self._advance(character)
            return Token(punctuation, character, offset, line, column)
        return None

    def _read_string(self, offset: int, line: int, column: int) -> Token:
        self._advance("'")
        characters: list[str] = []
        while self._index < len(self.source):
            character = self.source[self._index]
            if character == "'":
                if self._index + 1 < len(self.source) and self.source[self._index + 1] == "'":
                    characters.append("'")
                    self._advance_text("''")
                    continue
                self._advance("'")
                return Token(TokenType.STRING, "".join(characters), offset, line, column)
            characters.append(character)
            self._advance(character)
        raise LexicalError(
            "unterminated string literal",
            position=ErrorPosition(offset=offset, line=line, column=column),
        )

    def _skip_comment(self) -> None:
        self._advance_text("--")
        while self._index < len(self.source) and self.source[self._index] not in "\r\n":
            self._advance(self.source[self._index])

    def _advance_text(self, text: str) -> None:
        for character in text:
            self._advance(character)

    def _advance(self, character: str) -> None:
        self._index += 1
        if character == "\n":
            self._line += 1
            self._column = 1
        else:
            self._column += 1
