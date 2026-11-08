# Типы токенов и таблица ключевых слов

from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional


class TokenType(Enum):
    # Литералы
    INTEGER = auto()
    FLOAT = auto()
    STRING = auto()
    TRUE = auto()
    FALSE = auto()
    NULL = auto()

    # Идентификаторы
    IDENTIFIER = auto()

    # Операторы
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    PERCENT = auto()
    POWER = auto()  # **

    PLUS_EQ = auto()
    MINUS_EQ = auto()
    STAR_EQ = auto()
    SLASH_EQ = auto()
    PERCENT_EQ = auto()

    EQ = auto()  # ==
    NE = auto()  # !=
    LT = auto()  # <
    GT = auto()  # >
    LE = auto()  # <=
    GE = auto()  # >=
    ASSIGN = auto()  # =

    ARROW = auto()  # =>
    TERNARY_Q = auto()  # ?
    TERNARY_C = auto()  # :
    NULL_COALESCE = auto()  # ??
    SAFE_DOT = auto()  # ?.
    LOGICAL_AND = auto()  # &&
    LOGICAL_OR = auto()  # ||
    LOGICAL_NOT = auto()  # !

    # Пунктуация
    DOT = auto()
    COMMA = auto()
    COLON = auto()
    LPAREN = auto()
    RPAREN = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    LBRACE = auto()
    RBRACE = auto()

    # Специальные
    UNDERSCORE = auto()  # _ в числах
    NEWLINE = auto()
    EOF = auto()


# Ключевые слова (полная таблица из спецификации)
KEYWORDS = {
    # Шапка
    "слыш": "SLESH",
    "ГопЛя": "GOPLYA",
    "мадмуазель": "MADMUASELLE",

    # Объявления
    "пивас": "PIVAS",
    "семка": "SEMEK",
    "кортан": "KORTAN",
    "гоп": "GOP",
    "договорняк": "DOGOVORNYAK",
    "вынеси": "VYNESI",

    # ООП
    "от_бати": "OT_BATI",
    "по_договорняку": "PO_DOGVORNYAKU",
    "новый": "NOVYI",
    "сам": "SAM",
    "батя": "BATYA",
    "у_подъезда": "U_PODEZDA",
    "по_семейному": "PO_SEMEYNOMU",
    "за_гаражами": "ZA_GARAZHAMI",

    # Управление
    "чё_если": "CHO_ESLI",
    "а_чё_если": "A_CHO_ESLI",
    "а_нет": "A_NET",
    "грызи_пока": "GRYZI_POKA",
    "по_каждому": "PO_KAZHDOmU",
    "хватит_епт": "HVATIT_EPT",
    "дальше_епт": "DALSHE_EPT",
    "отдай": "OTDAI",
    "типа": "TIPA",

    # Контекстные
    "из": "IZ",
    "от": "OT",
    "до": "DO",
    "мимо": "MIMO",
    "как": "KAK",

    # Ошибки
    "попробуй": "POPROBUY",
    "предъявил": "PREDYAVIL",
    "по_понятиям": "PO_PONYATIYAM",
    "кидай": "KIDAI",

    # Асинхронность
    "сгоняй": "SGONYAI",
    "подожди_пивас": "PODZHDI_PIVAS",

    # Модули
    "позвать": "POZVAT",

    # Значения
    "правда": "PRAVDA",
    "неправда": "NEPRAVDA",
    "пусто": "PUSTO",

    # Операторы-слова
    "и_ещё": "I_ESHCHE",
    "или_чё": "ILI_CHE",
    "не_а": "NE_A",

    # Вывод
    "базарь": "BAZAR",

    # Фирменные
    "по_братски": "PO_BRATSKI",
    "шухер": "SHUHER",
    "отбой": "OTBOI",
    "на_потом": "NA_POTOM",
    "кинь_клич": "KIN_KLICH",
    "слушай": "SLUSHAI",
    "отстань": "OTSTAN",
    "по_кругу": "PO_KRUGU",

    # Встроенные имена (типы/константы/классы)
    "Косяк": "KOSYAK",
    "БамперКосяк": "BAMPER_KOSYAK",
    "Сижка": "SIZHKA",
    "сигара": "SIGARA",
    "папироска": "PAPIROSKA",
    "Буфера": "BUFFERA",
    "Вот_это_буфера": "VOT_ETO_BUFFERA",
    "Гонец": "GONETS",
    "братва": "BRATVA",

    # Имена типов
    "целое": "TYPE_INT",
    "дробь": "TYPE_FLOAT",
    "текст": "TYPE_TEXT",
    "логика": "TYPE_BOOL",
    "пусто": "TYPE_NULL",
    "кучка": "TYPE_LIST",
    "общак": "TYPE_DICT",
    "Гонец": "TYPE_GONETS",
}

# Обратное отображение для токенов ключевых слов
KEYWORD_TOKENS = {v: k for k, v in KEYWORDS.items()}


@dataclass
class Token:
    type: TokenType
    value: str
    line: int
    column: int

    def __repr__(self):
        return f"Token({self.type.name}, {self.value!r}, line={self.line}, col={self.column})"


# Операторы и их токены (для лексера)
OPERATORS = {
    "**": TokenType.POWER,
    "==": TokenType.EQ,
    "!=": TokenType.NE,
    "<=": TokenType.LE,
    ">=": TokenType.GE,
    "+=": TokenType.PLUS_EQ,
    "-=": TokenType.MINUS_EQ,
    "*=": TokenType.STAR_EQ,
    "/=": TokenType.SLASH_EQ,
    "%=": TokenType.PERCENT_EQ,
    "=>": TokenType.ARROW,
    "??": TokenType.NULL_COALESCE,
    "?.": TokenType.SAFE_DOT,
    "&&": TokenType.LOGICAL_AND,
    "||": TokenType.LOGICAL_OR,
    "+": TokenType.PLUS,
    "-": TokenType.MINUS,
    "*": TokenType.STAR,
    "/": TokenType.SLASH,
    "%": TokenType.PERCENT,
    "=": TokenType.ASSIGN,
    "<": TokenType.LT,
    ">": TokenType.GT,
    "?": TokenType.TERNARY_Q,
    ":": TokenType.TERNARY_C,
    "!": TokenType.LOGICAL_NOT,
    ".": TokenType.DOT,
    ",": TokenType.COMMA,
    "(": TokenType.LPAREN,
    ")": TokenType.RPAREN,
    "[": TokenType.LBRACKET,
    "]": TokenType.RBRACKET,
    "{": TokenType.LBRACE,
    "}": TokenType.RBRACE,
}

# Сортируем операторы по длине убывания для правильного матчинга
OPERATOR_KEYS = sorted(OPERATORS.keys(), key=len, reverse=True)