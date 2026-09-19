"""A small interpreter for Thunder v0.1.

Supported syntax:

    hello {
        text = "Hello, Thunder!"
        color = "green"
        printt(text, color)
        for i in range(3) {
            printt(i)
        }
    }
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Iterable

try:
    from .tui import (
        get_terminal_height,
        get_terminal_width,
        render_box,
        render_line,
        render_text,
    )
except ImportError:
    from tui import (
        get_terminal_height,
        get_terminal_width,
        render_box,
        render_line,
        render_text,
    )


class ThunderError(Exception):
    """Base class for errors reported by the Thunder frontend or runtime."""


class ThunderSyntaxError(ThunderError):
    """Raised when source code does not follow the Thunder grammar."""


class ThunderRuntimeError(ThunderError):
    """Raised when a valid program cannot be executed."""


@dataclass(frozen=True)
class Token:
    kind: str
    value: str
    line: int
    column: int


@dataclass(frozen=True)
class Assignment:
    name: str
    value: Any


@dataclass(frozen=True)
class BinaryExpression:
    left: Any
    operator: str
    right: Any


@dataclass(frozen=True)
class IndexExpression:
    collection: Any
    index: Any


@dataclass(frozen=True)
class CallExpression:
    name: str
    arguments: list[Any]


@dataclass(frozen=True)
class ImportStatement:
    module: str


@dataclass(frozen=True)
class FunctionDefinition:
    name: str
    parameters: list[str]
    statements: list[Any]


@dataclass(frozen=True)
class FunctionCall:
    name: str
    arguments: list[Any]


@dataclass(frozen=True)
class PrintCall:
    arguments: list[Any]


@dataclass(frozen=True)
class InputCall:
    prompt: str
    variable: str


@dataclass(frozen=True)
class ForStatement:
    variable: str
    limit: Any
    statements: list[Any]


@dataclass(frozen=True)
class WhileStatement:
    condition: Any
    statements: list[Any]


@dataclass(frozen=True)
class IfStatement:
    condition: Any
    if_statements: list[Any]
    else_statements: list[Any]


@dataclass(frozen=True)
class Program:
    name: str
    statements: list[Any]


TOKEN_RE = re.compile(
    r"""
    (?P<newline>\r?\n)
  | (?P<space>[ \t]+)
  | (?P<comment>\#[^\r\n]*)
  | (?P<string>"(?:\\.|[^"\\])*")
  | (?P<number>(?:\d+(?:\.\d*)?|\.\d+))
  | (?P<identifier>[A-Za-z_][A-Za-z0-9_]*)
  | (?P<comparison>==|!=|>=|<=|>|<)
  | (?P<symbol>[{}(),=;+*/-\[\]])
  | (?P<unknown>.)
    """,
    re.VERBOSE,
)


def tokenize(source: str) -> list[Token]:
    tokens: list[Token] = []
    line = 1
    column = 1

    for match in TOKEN_RE.finditer(source):
        kind = match.lastgroup
        value = match.group()
        start_line, start_column = line, column

        if kind == "unknown":
            raise ThunderSyntaxError(
                f"Unexpected character {value!r} at {start_line}:{start_column}"
            )
        if kind in {"space", "comment"}:
            pass
        elif kind == "newline":
            tokens.append(Token("newline", value, start_line, start_column))
        elif kind == "symbol":
            tokens.append(Token(value, value, start_line, start_column))
        else:
            tokens.append(Token(kind, value, start_line, start_column))

        line += value.count("\n")
        if "\n" in value:
            column = len(value.rsplit("\n", 1)[1]) + 1
        else:
            column += len(value)

    tokens.append(Token("eof", "", line, column))
    return tokens


class Parser:
    def __init__(self, tokens: Iterable[Token]):
        self.tokens = list(tokens)
        self.position = 0

    def parse(self) -> Program:
        name = self.consume("identifier", "Expected a program name.")
        self.consume("{", "Expected '{' after the program name.")

        statements = self.parse_block()
        self.skip_separators()
        self.consume("eof", "Unexpected content after the program block.")
        return Program(name.value, statements)

    def parse_block(
        self,
    ) -> list[Assignment | PrintCall | InputCall | ForStatement | IfStatement]:
        statements: list[Assignment | PrintCall | InputCall | ForStatement | IfStatement] = []
        self.skip_separators()
        while not self.check("}") and not self.check("eof"):
            statements.append(self.parse_statement())
            self.skip_separators()
        self.consume("}", "Expected '}' at the end of the block.")
        return statements

    def parse_statement(
        self,
    ) -> Any:
        if self.check("identifier") and self.current.value == "import":
            self.advance()
            module = self.consume("identifier", "Expected a module name after import.")
            return ImportStatement(module.value)

        if self.check("identifier") and self.current.value == "fn":
            return self.parse_function_definition()

        if self.check("identifier") and self.current.value == "if":
            return self.parse_if()

        if self.check("identifier") and self.current.value == "for":
            return self.parse_for()

        if self.check("identifier") and self.current.value == "while":
            return self.parse_while()

        if self.check("identifier") and self.peek(1).kind == "=":
            name = self.advance().value
            self.advance()
            return Assignment(name, self.parse_expression())

        if self.check("identifier") and self.current.value == "printt":
            return self.parse_print_call()

        if self.check("identifier") and self.current.value == "printl":
            return self.parse_input_call()

        if self.check("identifier") and self.peek(1).kind == "(":
            return self.parse_function_call()

        self.fail("Expected a function, assignment, printt(...), or printl(...).")

    def parse_function_definition(self) -> FunctionDefinition:
        self.advance()
        name = self.consume("identifier", "Expected a function name after fn.")
        self.consume("(", "Expected '(' after the function name.")
        parameters: list[str] = []
        if not self.check(")"):
            parameter = self.consume("identifier", "Expected a parameter name.")
            parameters.append(parameter.value)
            while self.match(","):
                parameter = self.consume("identifier", "Expected a parameter name.")
                parameters.append(parameter.value)
        self.consume(")", "Expected ')' after function parameters.")
        self.consume("{", "Expected '{' after the function declaration.")
        return FunctionDefinition(name.value, parameters, self.parse_block())

    def parse_function_call(self) -> FunctionCall:
        name = self.advance().value
        self.consume("(", "Expected '(' after the function name.")
        arguments: list[Any] = []
        if not self.check(")"):
            arguments.append(self.parse_expression())
            while self.match(","):
                arguments.append(self.parse_expression())
        self.consume(")", "Expected ')' after function arguments.")
        return FunctionCall(name, arguments)

    def parse_for(self) -> ForStatement:
        self.advance()
        variable = self.consume("identifier", "Expected a loop variable after for.")
        keyword_in = self.consume("identifier", "Expected 'in' after the loop variable.")
        if keyword_in.value != "in":
            self.fail_at(keyword_in, "Expected 'in' after the loop variable.")

        range_name = self.consume("identifier", "Expected range(...) after 'in'.")
        if range_name.value != "range":
            self.fail_at(range_name, "Expected range(...) after 'in'.")
        self.consume("(", "Expected '(' after range.")
        limit = self.parse_expression()
        self.consume(")", "Expected ')' after the range limit.")
        self.consume("{", "Expected '{' after the for range.")
        statements = self.parse_block()
        return ForStatement(variable.value, limit, statements)

    def parse_while(self) -> WhileStatement:
        self.advance()
        condition = self.parse_expression()
        self.consume("{", "Expected '{' after the while condition.")
        return WhileStatement(condition, self.parse_block())

    def parse_if(self) -> IfStatement:
        self.advance()
        condition = self.parse_expression()
        self.consume("{", "Expected '{' after the if condition.")
        if_statements = self.parse_block()

        else_statements: list[Assignment | PrintCall | IfStatement] = []
        self.skip_separators()
        if self.check("identifier") and self.current.value == "else":
            self.advance()
            if self.check("identifier") and self.current.value == "if":
                else_statements = [self.parse_if()]
            else:
                self.consume("{", "Expected '{' after else.")
                else_statements = self.parse_block()

        return IfStatement(condition, if_statements, else_statements)

    def parse_print_call(self) -> PrintCall:
        self.advance()
        self.consume("(", "Expected '(' after printt.")
        arguments: list[Any] = []

        if not self.check(")"):
            arguments.append(self.parse_expression())
            while self.match(","):
                arguments.append(self.parse_expression())

        self.consume(")", "Expected ')' after printt arguments.")
        if len(arguments) not in {1, 2, 3}:
            self.fail_at(self.previous(), "printt expects text, color, and optional styles.")
        return PrintCall(arguments)

    def parse_input_call(self) -> InputCall:
        self.advance()
        self.consume("(", "Expected '(' after printl.")
        prompt = self.advance()
        if prompt.kind != "string":
            self.fail_at(prompt, "printl's first argument must be a quoted string.")
        try:
            prompt_value = json.loads(prompt.value)
        except json.JSONDecodeError as error:
            self.fail_at(prompt, f"Invalid string escape: {error}")

        self.consume(",", "Expected ',' between printl arguments.")
        variable = self.consume(
            "identifier", "printl's second argument must be a variable name."
        )
        self.consume(")", "Expected ')' after printl arguments.")
        return InputCall(prompt_value, variable.value)

    def parse_expression(self, minimum_precedence: int = 0) -> Any:
        expression = self.parse_primary()
        precedence = {
            "or": 1,
            "and": 2,
            "==": 3,
            "!=": 3,
            ">": 3,
            "<": 3,
            ">=": 3,
            "<=": 3,
            "+": 4,
            "-": 4,
            "*": 5,
            "/": 5,
        }

        while self.current.value in precedence or (
            self.current.kind == "identifier"
            and self.current.value in {"and", "or"}
        ):
            operator = self.current.value
            if precedence[operator] < minimum_precedence:
                break
            self.advance()
            right = self.parse_expression(precedence[operator] + 1)
            expression = BinaryExpression(expression, operator, right)
        return expression

    def parse_primary(self) -> Any:
        if self.check("identifier") and self.current.value == "not":
            self.advance()
            return BinaryExpression(True, "not", self.parse_primary())

        token = self.advance()
        if token.kind == "-":
            return BinaryExpression(0, "-", self.parse_primary())
        if token.kind == "string":
            try:
                return json.loads(token.value)
            except json.JSONDecodeError as error:
                self.fail_at(token, f"Invalid string escape: {error}")
        if token.kind == "number":
            expression: Any = float(token.value) if "." in token.value else int(token.value)
        elif token.kind == "identifier":
            if token.value == "true":
                expression = True
            elif token.value == "false":
                expression = False
            elif self.check("("):
                self.advance()
                arguments: list[Any] = []
                if not self.check(")"):
                    arguments.append(self.parse_expression())
                    while self.match(","):
                        arguments.append(self.parse_expression())
                self.consume(")", "Expected ')' after function arguments.")
                expression = CallExpression(token.value, arguments)
            else:
                expression = ("variable", token.value)
        elif token.kind == "[":
            expression = self.parse_list_literal()
        elif token.kind == "(":
            expression = self.parse_expression()
            self.consume(")", "Expected ')' after expression.")
        else:
            self.fail_at(token, "Expected a value or expression.")

        while self.match("["):
            index = self.parse_expression()
            self.consume("]", "Expected ']' after list index.")
            expression = IndexExpression(expression, index)
        return expression

    def parse_list_literal(self) -> list[Any]:
        values: list[Any] = []
        if not self.check("]"):
            values.append(self.parse_expression())
            while self.match(","):
                values.append(self.parse_expression())
        self.consume("]", "Expected ']' after list values.")
        return values

    def parse_literal(self) -> Any:
        return self.parse_expression()

    def skip_separators(self) -> None:
        while self.match("newline", ";"):
            pass

    def check(self, kind: str) -> bool:
        return self.current.kind == kind

    def match(self, *kinds: str) -> bool:
        if self.current.kind in kinds:
            self.advance()
            return True
        return False

    def consume(self, kind: str, message: str) -> Token:
        if self.check(kind):
            return self.advance()
        self.fail(message)

    def advance(self) -> Token:
        token = self.current
        if not self.check("eof"):
            self.position += 1
        return token

    def peek(self, distance: int = 0) -> Token:
        index = min(self.position + distance, len(self.tokens) - 1)
        return self.tokens[index]

    @property
    def current(self) -> Token:
        return self.peek()

    def previous(self) -> Token:
        return self.tokens[max(0, self.position - 1)]

    def fail(self, message: str) -> None:
        self.fail_at(self.current, message)

    @staticmethod
    def fail_at(token: Token, message: str) -> None:
        raise ThunderSyntaxError(f"{message} At {token.line}:{token.column}.")


class Interpreter:
    def __init__(
        self,
        *,
        color_output: bool = True,
        base_dir: Path | None = None,
        script_args: list[str] | None = None,
    ):
        self.variables: dict[str, Any] = {"args": list(script_args or [])}
        self.scopes: list[dict[str, Any]] = [self.variables]
        self.functions: dict[str, FunctionDefinition] = {}
        self.color_output = color_output
        self.base_dir = base_dir or Path.cwd()
        self.imported_modules: set[str] = set()

    def run(self, program: Program) -> None:
        self.functions = {
            statement.name: statement
            for statement in program.statements
            if isinstance(statement, FunctionDefinition)
        }
        self.execute_statements(program.statements)

    def execute_statements(
        self,
        statements: list[Any],
    ) -> None:
        for statement in statements:
            if isinstance(statement, FunctionDefinition):
                continue
            if isinstance(statement, ImportStatement):
                self.execute_import(statement)
                continue
            if isinstance(statement, Assignment):
                self.scopes[-1][statement.name] = self.evaluate(statement.value)
            elif isinstance(statement, PrintCall):
                self.execute_print(statement)
            elif isinstance(statement, InputCall):
                self.execute_input(statement)
            elif isinstance(statement, FunctionCall):
                self.execute_function_call(statement)
            elif isinstance(statement, ForStatement):
                self.execute_for(statement)
            elif isinstance(statement, WhileStatement):
                self.execute_while(statement)
            else:
                condition = self.evaluate_condition(statement)
                if condition:
                    self.execute_statements(statement.if_statements)
                else:
                    self.execute_statements(statement.else_statements)

    def execute_import(self, statement: ImportStatement) -> None:
        if statement.module in self.imported_modules:
            return
        path = self.base_dir / f"{statement.module}.th"
        try:
            source = path.read_text(encoding="utf-8")
        except OSError as error:
            raise ThunderRuntimeError(
                f"Could not import module {statement.module!r}: {error}"
            ) from None
        program = Parser(tokenize(source)).parse()
        self.imported_modules.add(statement.module)
        self.functions.update(
            {
                item.name: item
                for item in program.statements
                if isinstance(item, FunctionDefinition)
            }
        )
        self.execute_statements(program.statements)

    def execute_for(self, statement: ForStatement) -> None:
        limit = self.evaluate(statement.limit)
        if not isinstance(limit, int) or isinstance(limit, bool):
            raise ThunderRuntimeError("range's limit must be an integer.")
        if limit < 0:
            raise ThunderRuntimeError("range's limit must not be negative.")

        for value in range(limit):
            self.scopes[-1][statement.variable] = value
            self.execute_statements(statement.statements)

    def execute_while(self, statement: WhileStatement) -> None:
        while self.evaluate(statement.condition):
            self.execute_statements(statement.statements)

    def execute_function_call(self, call: FunctionCall) -> None:
        if call.name == "box":
            if len(call.arguments) not in {5, 6, 7}:
                raise ThunderRuntimeError(
                    "box expects width, height, x, y, color, optional text and alignment."
                )
            values = [self.evaluate(argument) for argument in call.arguments]
            width, height, x, y, color = values[:5]
            if not all(isinstance(value, int) and not isinstance(value, bool)
                       for value in (width, height, x, y)):
                raise ThunderRuntimeError(
                    "box expects integer width, height, x, and y arguments."
                )
            if not isinstance(color, str):
                raise ThunderRuntimeError("box's color argument must be a string.")
            text = values[5] if len(values) >= 6 else None
            alignment = values[6] if len(values) == 7 else "center"
            if text is not None and not isinstance(text, str):
                raise ThunderRuntimeError("box's text argument must be a string.")
            if not isinstance(alignment, str):
                raise ThunderRuntimeError("box's alignment must be a string.")
            try:
                render_box(
                    width,
                    height,
                    x,
                    y,
                    color,
                    text,
                    alignment,
                    color_output=self.color_output,
                )
            except ValueError as error:
                raise ThunderRuntimeError(str(error)) from None
            return

        if call.name == "line":
            if len(call.arguments) != 5:
                raise ThunderRuntimeError(
                    "line expects direction, length, x, y, and color."
                )
            direction, length, x, y, color = [
                self.evaluate(argument) for argument in call.arguments
            ]
            if not isinstance(direction, str) or not isinstance(color, str):
                raise ThunderRuntimeError("line direction and color must be strings.")
            if not all(isinstance(value, int) and not isinstance(value, bool)
                       for value in (length, x, y)):
                raise ThunderRuntimeError("line length, x, and y must be integers.")
            try:
                render_line(
                    direction, length, x, y, color, color_output=self.color_output
                )
            except ValueError as error:
                raise ThunderRuntimeError(str(error)) from None
            return

        if call.name == "write_file":
            if len(call.arguments) != 2:
                raise ThunderRuntimeError("write_file expects two arguments.")
            path = self.evaluate(call.arguments[0])
            content = self.evaluate(call.arguments[1])
            if not isinstance(path, str) or not isinstance(content, str):
                raise ThunderRuntimeError("write_file expects a path and text content.")
            try:
                Path(path).write_text(content, encoding="utf-8")
            except OSError as error:
                raise ThunderRuntimeError(f"Could not write file {path!r}: {error}") from None
            return

        function = self.functions.get(call.name)
        if function is None:
            raise ThunderRuntimeError(f"Unknown function: {call.name}")
        if len(call.arguments) != len(function.parameters):
            raise ThunderRuntimeError(
                f"Function {call.name} expects {len(function.parameters)} "
                f"argument(s), got {len(call.arguments)}."
            )

        local_scope = {
            parameter: self.evaluate(argument)
            for parameter, argument in zip(function.parameters, call.arguments)
        }
        self.scopes.append(local_scope)
        try:
            self.execute_statements(function.statements)
        finally:
            self.scopes.pop()

    def evaluate_condition(self, statement: IfStatement) -> bool:
        return bool(self.evaluate(statement.condition))

    def evaluate(self, value: Any) -> Any:
        if isinstance(value, list):
            return [self.evaluate(item) for item in value]
        if isinstance(value, IndexExpression):
            collection = self.evaluate(value.collection)
            index = self.evaluate(value.index)
            if not isinstance(index, int) or isinstance(index, bool):
                raise ThunderRuntimeError("List index must be an integer.")
            try:
                return collection[index]
            except (IndexError, TypeError):
                raise ThunderRuntimeError("List index is out of range.") from None
        if isinstance(value, CallExpression):
            if value.name == "term_width":
                if value.arguments:
                    raise ThunderRuntimeError("term_width expects no arguments.")
                return get_terminal_width()
            if value.name == "term_height":
                if value.arguments:
                    raise ThunderRuntimeError("term_height expects no arguments.")
                return get_terminal_height()
            if value.name == "read_file":
                if len(value.arguments) != 1:
                    raise ThunderRuntimeError("read_file expects one argument.")
                path = self.evaluate(value.arguments[0])
                if not isinstance(path, str):
                    raise ThunderRuntimeError("read_file expects a file path.")
                try:
                    return Path(path).read_text(encoding="utf-8")
                except OSError as error:
                    raise ThunderRuntimeError(f"Could not read file {path!r}: {error}") from None
            if value.name == "exec":
                if len(value.arguments) != 1:
                    raise ThunderRuntimeError("exec expects one command string.")
                command = self.evaluate(value.arguments[0])
                if not isinstance(command, str):
                    raise ThunderRuntimeError("exec expects a command string.")
                try:
                    result = subprocess.run(
                        command,
                        shell=True,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        check=False,
                    )
                except OSError as error:
                    raise ThunderRuntimeError(
                        f"Could not execute command {command!r}: {error}"
                    ) from None
                if result.returncode != 0:
                    detail = result.stderr.strip() or f"exit code {result.returncode}"
                    raise ThunderRuntimeError(
                        f"Command {command!r} failed: {detail}"
                    )
                return result.stdout
            function = self.functions.get(value.name)
            if function is None:
                raise ThunderRuntimeError(f"Unknown function: {value.name}")
            raise ThunderRuntimeError(
                f"Function {value.name} does not return a value."
            )
        if isinstance(value, BinaryExpression):
            left = self.evaluate(value.left)
            right = self.evaluate(value.right)
            if value.operator == "and":
                return bool(left) and bool(right)
            if value.operator == "or":
                return bool(left) or bool(right)
            if value.operator == "not":
                return not bool(self.evaluate(value.right))
            if value.operator in {"==", "!="}:
                return left == right if value.operator == "==" else left != right
            if value.operator in {">", "<", ">=", "<="}:
                try:
                    if value.operator == ">":
                        return left > right
                    if value.operator == "<":
                        return left < right
                    if value.operator == ">=":
                        return left >= right
                    return left <= right
                except TypeError:
                    raise ThunderRuntimeError(
                        f"Cannot compare {type(left).__name__} and "
                        f"{type(right).__name__}."
                    ) from None
            if value.operator == "+":
                operation = lambda: left + right
            elif value.operator == "-":
                operation = lambda: left - right
            elif value.operator == "*":
                operation = lambda: left * right
            elif value.operator == "/":
                if right == 0:
                    raise ThunderRuntimeError("Division by zero.")
                operation = lambda: left / right
            else:
                raise ThunderRuntimeError(
                    f"Unsupported arithmetic operator: {value.operator}"
                )
            try:
                result = operation()
            except TypeError:
                raise ThunderRuntimeError(
                    f"Cannot apply '{value.operator}' to {type(left).__name__} "
                    f"and {type(right).__name__}."
                ) from None
            return result
        if isinstance(value, tuple) and value[0] == "variable":
            name = value[1]
            for scope in reversed(self.scopes):
                if name in scope:
                    return scope[name]
            raise ThunderRuntimeError(f"Undefined variable: {name}")
        return value

    def execute_print(self, call: PrintCall) -> None:
        text = self.evaluate(call.arguments[0])
        if not isinstance(text, (str, int, float)):
            raise ThunderRuntimeError("printt's first argument must be text or a number.")

        color = "white"
        styles: list[str] = []
        if len(call.arguments) == 2:
            color = self.evaluate(call.arguments[1])
            if not isinstance(color, str):
                raise ThunderRuntimeError("printt's color argument must be a string.")
        elif len(call.arguments) == 3:
            color = self.evaluate(call.arguments[1])
            style = self.evaluate(call.arguments[2])
            if not isinstance(color, str) or not isinstance(style, str):
                raise ThunderRuntimeError("printt color and style must be strings.")
            styles = [style]
        try:
            print(render_text(str(text), color, styles, color_output=self.color_output))
        except ValueError as error:
            raise ThunderRuntimeError(str(error)) from None

    def execute_input(self, call: InputCall) -> None:
        value = input(call.prompt)
        self.scopes[-1][call.variable] = self.convert_input(value)

    @staticmethod
    def convert_input(value: str) -> int | float | str:
        try:
            return int(value)
        except ValueError:
            try:
                return float(value)
            except ValueError:
                return value


def run_source(
    source: str,
    *,
    color_output: bool = True,
    base_dir: Path | None = None,
    script_args: list[str] | None = None,
) -> Program:
    program = Parser(tokenize(source)).parse()
    Interpreter(
        color_output=color_output,
        base_dir=base_dir,
        script_args=script_args,
    ).run(program)
    return program


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a Thunder v0.1 program.")
    parser.add_argument("source", help="Path to a .th source file.")
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI color codes in printt output.",
    )
    parser.add_argument(
        "script_args",
        nargs=argparse.REMAINDER,
        help="Arguments passed to the Thunder program and available as args.",
    )
    args = parser.parse_args(argv)

    if not args.source.lower().endswith(".th"):
        print("Thunder source files must use the .th extension.", file=sys.stderr)
        return 1

    try:
        with open(args.source, encoding="utf-8") as source_file:
            run_source(
                source_file.read(),
                color_output=not args.no_color,
                base_dir=Path(args.source).resolve().parent,
                script_args=args.script_args,
            )
    except OSError as error:
        print(f"Could not read {args.source!r}: {error}", file=sys.stderr)
        return 1
    except (ThunderError, EOFError) as error:
        print(f"Thunder error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
