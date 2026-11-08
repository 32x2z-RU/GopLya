# Узлы AST (абстрактное синтаксическое дерево)

from dataclasses import dataclass, field
from typing import List, Optional, Union
from .tokens import Token


class Node:
    """Базовый узел AST."""
    token: Optional[Token] = None

    def line(self) -> int:
        return self.token.line if self.token else 0


# Forward declarations for type hints
class Expression(Node):
    pass


class Statement(Node):
    pass


class Declaration(Node):
    pass


@dataclass
class Program(Node):
    header: 'Header'
    declarations: List['Declaration'] = field(default_factory=list)


@dataclass
class Header(Node):
    version: str
    strict: bool  # мадмуазель в шапке


# --- Объявления верхнего уровня ---

@dataclass
class PivasDecl(Declaration):
    name: str
    type_ann: Optional['TypeAnn']
    value: 'Expression'


@dataclass
class SemkaDecl(Declaration):
    name: str
    type_ann: Optional['TypeAnn']
    value: Optional['Expression']


@dataclass
class KortanDecl(Declaration):
    name: str
    params: List['Parameter']
    return_type: Optional['TypeAnn']
    body: Union['Block', 'Expression']  # Block или выражение после типа
    is_async: bool
    is_strict: bool
    is_lambda: bool = False


@dataclass
class Parameter(Node):
    name: str
    type_ann: Optional['TypeAnn']
    default: Optional['Expression']


@dataclass
class GopDecl(Declaration):
    name: str
    parent: Optional[str]
    interfaces: List[str]
    members: List['GopMember']
    is_strict: bool


@dataclass
class GopMember(Node):
    modifier: Optional[str]  # у_подъезда, по_семейному, за_гаражами
    field: Optional['FieldDecl']
    method: Optional['KortanDecl']


@dataclass
class FieldDecl(Node):
    name: str
    type_ann: Optional['TypeAnn']
    value: Optional['Expression']


@dataclass
class DogovornyakDecl(Declaration):
    name: str
    methods: List['KortanDecl']  # Только сигнатуры


@dataclass
class PozvatDecl(Declaration):
    module: str
    alias: Optional[str]
    names: Optional[List[str]]  # None = все, иначе выборочный импорт


@dataclass
class VynesiDecl(Declaration):
    decl: Declaration  # Помечает следующее объявление как публичное


# --- Типы ---

@dataclass
class TypeAnn(Node):
    name: str
    nullable: bool  # суффикс ?


# --- Выражения ---

@dataclass
class Literal(Expression):
    value: Union[int, float, str, bool, None]
    lit_type: str  # 'int', 'float', 'string', 'bool', 'null'


@dataclass
class Identifier(Expression):
    name: str


@dataclass
class SelfExpr(Expression):
    pass


@dataclass
class BatyaExpr(Expression):
    pass


@dataclass
class BinaryOp(Expression):
    left: Expression
    operator: str  # '+', '-', '*', '/', '%', '**', '==', '!=', '<', '>', '<=', '>=', '&&', '||', '??', 'и_ещё', 'или_чё'
    right: Expression


@dataclass
class UnaryOp(Expression):
    operator: str  # '-', '!', 'не_а', 'подожди_пивас'
    operand: Expression


@dataclass
class TernaryOp(Expression):
    condition: Expression
    then_expr: Expression
    else_expr: Expression


@dataclass
class CallExpr(Expression):
    callee: Expression
    args: List['Arg']


@dataclass
class Arg(Node):
    name: Optional[str]  # None для позиционных
    value: Expression


@dataclass
class IndexExpr(Expression):
    object: Expression
    index: Expression


@dataclass
class MemberExpr(Expression):
    object: Expression
    name: str
    safe: bool  # ?. оператор


@dataclass
class NewExpr(Expression):
    class_name: str
    args: List[Arg]
    is_ring: bool  # по_кругу


@dataclass
class ListLiteral(Expression):
    elements: List[Expression]


@dataclass
class DictLiteral(Expression):
    entries: List[tuple[Expression, Expression]]  # (key, value)


@dataclass
class Interpolation(Expression):
    parts: List[Union[str, Expression]]  # чередуются строка/выражение


@dataclass
class LambdaExpr(Expression):
    params: List['Parameter']
    body: Union['Block', 'Expression']
    is_async: bool
    is_strict: bool = False


@dataclass
class PoBratskiExpr(Expression):
    source: Expression
    targets: List['PoBratskiTarget']


@dataclass
class PoBratskiTarget(Node):
    target: Expression  # lvalue
    weight: Optional[Expression]


# --- Операторы (Statements) ---

@dataclass
class Block(Statement):
    statements: List[Statement]


@dataclass
class IfStmt(Statement):
    condition: Expression
    then_block: Block
    elif_branches: List[tuple[Expression, Block]]  # (condition, block)
    else_block: Optional[Block]


@dataclass
class WhileStmt(Statement):
    condition: Expression
    body: Block


@dataclass
class ForStmt(Statement):
    var_name: str
    iterable: Optional[Expression] = None  # для 'из'
    range_start: Optional[Expression] = None  # для 'от'
    range_end: Optional[Expression] = None
    range_inclusive: bool = True  # до=True, мимо=False
    body: 'Block' = None


@dataclass
class TryStmt(Statement):
    try_block: Block
    catch_blocks: List['CatchBlock']
    finally_block: Optional[Block]


@dataclass
class CatchBlock(Node):
    exception_type: str
    var_name: str
    block: Block


@dataclass
class NaPotomStmt(Statement):
    statement: Statement


@dataclass
class ReturnStmt(Statement):
    value: Optional[Expression]


@dataclass
class ThrowStmt(Statement):
    value: Expression


@dataclass
class BreakStmt(Statement):
    pass


@dataclass
class ContinueStmt(Statement):
    pass


@dataclass
class BazarStmt(Statement):
    args: List[Expression]


@dataclass
class AssignStmt(Statement):
    target: Expression
    operator: str  # '=', '+=', '-=', '*=', '/=', '%='
    value: Expression


@dataclass
class ExpressionStmt(Statement):
    expression: Expression


@dataclass
class SlushaiStmt(Node):
    event_name: str
    handler: Expression


@dataclass
class KinKlichStmt(Node):
    event_name: str
    args: List[Expression]


@dataclass
class OtstanStmt(Node):
    event_name: str


# Типы для объединения
Declaration = Union[
    PivasDecl, SemkaDecl, KortanDecl, GopDecl, 
    DogovornyakDecl, PozvatDecl, VynesiDecl
]

Statement = Union[
    Block, PivasDecl, SemkaDecl, IfStmt, WhileStmt, ForStmt,
    TryStmt, NaPotomStmt, ReturnStmt, ThrowStmt, BreakStmt,
    ContinueStmt, BazarStmt, AssignStmt, ExpressionStmt,
    SlushaiStmt, KinKlichStmt, OtstanStmt, PoBratskiExpr
]

Expression = Union[
    Literal, Identifier, SelfExpr, BatyaExpr, BinaryOp, UnaryOp,
    TernaryOp, CallExpr, IndexExpr, MemberExpr, NewExpr,
    ListLiteral, DictLiteral, Interpolation, LambdaExpr,
    PoBratskiExpr
]