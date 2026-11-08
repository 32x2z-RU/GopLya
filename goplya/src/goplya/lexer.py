# Лексер (ручной, по спецификации)

from typing import List, Optional
from .tokens import (
    Token, TokenType, KEYWORDS, OPERATORS, OPERATOR_KEYS
)


class LexerError(Exception):
    def __init__(self, message: str, line: int, column: int):
        self.message = message
        self.line = line
        self.column = column
        super().__init__(f"{message} (строка {line}, колонка {column})")


class Lexer:
    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens: List[Token] = []

    def current_char(self) -> Optional[str]:
        if self.pos >= len(self.source):
            return None
        return self.source[self.pos]

    def peek_char(self, offset: int = 1) -> Optional[str]:
        peek_pos = self.pos + offset
        if peek_pos >= len(self.source):
            return None
        return self.source[peek_pos]

    def advance(self) -> Optional[str]:
        char = self.current_char()
        if char is not None:
            if char == '\n':
                self.line += 1
                self.column = 1
            elif char == '\r':
                # Обрабатываем \r\n как один перевод строки
                if self.peek_char() == '\n':
                    self.advance()  # пропускаем \n
                self.line += 1
                self.column = 1
            else:
                self.column += 1
            self.pos += 1
        return char

    def add_token(self, type_: TokenType, value: str):
        self.tokens.append(Token(type_, value, self.line, self.column - len(value)))

    def skip_whitespace(self):
        while True:
            char = self.current_char()
            if char in (' ', '\t', '\r'):
                self.advance()
            else:
                break

    def skip_comment(self):
        char = self.current_char()
        if char == '/':
            next_char = self.peek_char()
            if next_char == '/':
                # Однострочный комментарий
                while self.current_char() not in ('\n', None):
                    self.advance()
            elif next_char == '*':
                # Многострочный комментарий
                self.advance()  # /
                self.advance()  # *
                while True:
                    char = self.current_char()
                    if char is None:
                        raise LexerError("Незакрытый многострочный комментарий", self.line, self.column)
                    if char == '*' and self.peek_char() == '/':
                        self.advance()  # *
                        self.advance()  # /
                        break
                    self.advance()
            else:
                return False
            return True
        return False

    def read_number(self) -> Token:
        start_line = self.line
        start_col = self.column
        value = ""
        has_dot = False
        has_underscore = False

        while True:
            char = self.current_char()
            if char is not None and char.isdigit():
                value += char
                self.advance()
            elif char == '_':
                # Подчёркивание в числах
                next_char = self.peek_char()
                if next_char is not None and next_char.isdigit():
                    value += char
                    self.advance()
                    has_underscore = True
                else:
                    break
            elif char == '.' and not has_dot:
                next_char = self.peek_char()
                if next_char is not None and next_char.isdigit():
                    value += char
                    self.advance()
                    has_dot = True
                else:
                    break
            else:
                break

        # Удаляем подчёркивания для парсинга
        clean_value = value.replace('_', '')

        if has_dot:
            return Token(TokenType.FLOAT, clean_value, start_line, start_col)
        else:
            return Token(TokenType.INTEGER, clean_value, start_line, start_col)

    def read_string(self) -> Token:
        start_line = self.line
        start_col = self.column
        self.advance()  # пропускаем открывающую кавычку
        value = ""

        while True:
            char = self.current_char()
            if char is None:
                raise LexerError("Незакрытая строка", start_line, start_col)
            if char == '\n':
                raise LexerError("Строка не может содержать перенос строки", self.line, self.column)
            if char == '"':
                # Проверяем экранирование
                if value.endswith('\\') and not value.endswith('\\\\'):
                    value += char
                    self.advance()
                    continue
                self.advance()  # закрывающая кавычка
                break
            if char == '\\':
                self.advance()
                next_char = self.current_char()
                if next_char is None:
                    raise LexerError("Незакрытая строка (экранирование в конце)", start_line, start_col)
                escape_map = {
                    '"': '"',
                    '\\': '\\',
                    'n': '\n',
                    't': '\t',
                    '{': '{',
                    '}': '}',
                }
                value += escape_map.get(next_char, next_char)
                self.advance()
            else:
                value += char
                self.advance()

        return Token(TokenType.STRING, value, start_line, start_col)

    def read_identifier(self) -> Token:
        start_line = self.line
        start_col = self.column
        value = ""

        while True:
            char = self.current_char()
            if char is not None and (char.isalpha() or char.isdigit() or char == '_' or ord(char) > 127):
                value += char
                self.advance()
            else:
                break

        # Проверяем ключевые слова
        keyword_type = KEYWORDS.get(value)
        if keyword_type:
            # Специальные типы для некоторых ключевых слов
            if keyword_type in ("PRAVDA",):
                return Token(TokenType.TRUE, value, start_line, start_col)
            elif keyword_type in ("NEPRAVDA",):
                return Token(TokenType.FALSE, value, start_line, start_col)
            elif keyword_type in ("PUSTO", "TYPE_NULL"):
                return Token(TokenType.NULL, value, start_line, start_col)
            else:
                # Для идентификаторов-ключевых слов возвращаем IDENTIFIER с указанием ключевого слова
                return Token(TokenType.IDENTIFIER, value, start_line, start_col)
        
        return Token(TokenType.IDENTIFIER, value, start_line, start_col)

    def read_operator(self) -> Optional[Token]:
        # Пытаемся прочитать самый длинный оператор
        for op in OPERATOR_KEYS:
            if self.source.startswith(op, self.pos):
                start_line = self.line
                start_col = self.column
                for _ in op:
                    self.advance()
                return Token(OPERATORS[op], op, start_line, start_col)
        return None

    def tokenize(self) -> List[Token]:
        while self.pos < len(self.source):
            self.skip_whitespace()
            
            if self.skip_comment():
                continue

            char = self.current_char()
            if char is None:
                break

            if char == '\n':
                self.add_token(TokenType.NEWLINE, '\n')
                self.advance()
                continue

            # Числа
            if char.isdigit():
                self.tokens.append(self.read_number())
                continue

            # Строки
            if char == '"':
                self.tokens.append(self.read_string())
                continue

            # Идентификаторы и ключевые слова
            if char.isalpha() or char == '_' or ord(char) > 127:
                self.tokens.append(self.read_identifier())
                continue

            # Операторы и пунктуация
            op_token = self.read_operator()
            if op_token:
                self.tokens.append(op_token)
                continue

            # Неизвестный символ
            raise LexerError(f"Неизвестный символ: {char!r}", self.line, self.column)

        self.add_token(TokenType.EOF, "")
        return self.tokens