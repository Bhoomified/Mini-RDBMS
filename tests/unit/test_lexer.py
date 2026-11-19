import unittest

from mini_rdbms.common.errors import LexicalError
from mini_rdbms.parser.lexer import Lexer
from mini_rdbms.parser.tokens import TokenType


class LexerTest(unittest.TestCase):
    def test_tokenizes_query_and_tracks_positions(self) -> None:
        tokens = Lexer("SELECT name FROM students WHERE age >= 18;").tokenize()

        self.assertEqual(
            [token.token_type for token in tokens],
            [
                TokenType.KEYWORD,
                TokenType.IDENTIFIER,
                TokenType.KEYWORD,
                TokenType.IDENTIFIER,
                TokenType.KEYWORD,
                TokenType.IDENTIFIER,
                TokenType.OPERATOR,
                TokenType.INTEGER,
                TokenType.SEMICOLON,
                TokenType.EOF,
            ],
        )
        self.assertEqual(tokens[0].value, "SELECT")
        self.assertEqual(tokens[6].value, ">=")
        self.assertEqual((tokens[7].line, tokens[7].column), (1, 40))

    def test_handles_float_strings_escaped_quotes_and_comments(self) -> None:
        tokens = Lexer("INSERT INTO t VALUES (1, 2.5, 'Bob''s'); -- ignored").tokenize()
        values = [token.value for token in tokens[:-1]]

        self.assertEqual(values, ["INSERT", "INTO", "t", "VALUES", "(", 1, ",", 2.5, ",", "Bob's", ")", ";"])
        self.assertEqual(tokens[9].token_type, TokenType.STRING)

    def test_reports_invalid_character(self) -> None:
        with self.assertRaisesRegex(LexicalError, "unexpected character"):
            Lexer("SELECT @").tokenize()

    def test_reports_unterminated_string(self) -> None:
        with self.assertRaisesRegex(LexicalError, "unterminated string"):
            Lexer("SELECT 'missing").tokenize()


if __name__ == "__main__":
    unittest.main()
