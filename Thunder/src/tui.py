"""Terminal UI primitives for Thunder."""

import shutil
import sys
from os import terminal_size


ANSI_COLORS = {
    "black": "\033[30m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
    "white": "\033[37m",
}

ANSI_STYLES = {
    "bold": "\033[1m",
    "italic": "\033[3m",
    "underline": "\033[4m",
    "inverse": "\033[7m",
    "invert": "\033[7m",
}


def _color_code(color: str) -> str:
    code = ANSI_COLORS.get(color.lower())
    if code is None:
        allowed = ", ".join(sorted(ANSI_COLORS))
        raise ValueError(f"Unknown color {color!r}. Available colors: {allowed}.")
    return code


def _style_codes(styles: list[str]) -> str:
    codes = []
    for style in styles:
        code = ANSI_STYLES.get(style.lower())
        if code is None:
            allowed = ", ".join(sorted(ANSI_STYLES))
            raise ValueError(f"Unknown text style {style!r}. Available styles: {allowed}.")
        codes.append(code)
    return "".join(codes)


def render_text(
    text: str,
    color: str,
    styles: list[str] | None = None,
    *,
    color_output: bool = True,
) -> str:
    prefix = _color_code(color) + _style_codes(styles or [])
    return f"{prefix}{text}\033[0m" if color_output else text


def _terminal_size() -> terminal_size:
    return shutil.get_terminal_size(fallback=(80, 24))


def get_terminal_width() -> int:
    return _terminal_size().columns


def get_terminal_height() -> int:
    return _terminal_size().lines


def render_box(
    width: int,
    height: int,
    x: int,
    y: int,
    color: str,
    text: str | None = None,
    alignment: str = "center",
    *,
    color_output: bool = True,
) -> None:
    """Draw a bordered rectangle at a one-based terminal position."""
    if width < 2 or height < 2:
        raise ValueError("box width and height must be at least 2.")
    if x < 1 or y < 1:
        raise ValueError("box x and y positions must be at least 1.")
    if x + width - 1 > get_terminal_width() or y + height - 1 > get_terminal_height():
        raise ValueError("box does not fit inside the current terminal dimensions.")
    code = _color_code(color)

    inner_width = width - 2
    if text is not None:
        if len(text) > inner_width:
            text = text[:inner_width]
        if alignment == "left":
            text = text.ljust(inner_width)
        elif alignment == "right":
            text = text.rjust(inner_width)
        elif alignment == "center":
            text = text.center(inner_width)
        else:
            raise ValueError("box alignment must be center, left, or right.")

    lines = [
        "┌" + "─" * inner_width + "┐",
        *(
            "│" + (text if index == (height - 2) // 2 else " " * inner_width) + "│"
            for index in range(height - 2)
        ),
        "└" + "─" * inner_width + "┘",
    ]
    output = []
    for offset, line in enumerate(lines):
        rendered = f"{code}{line}\033[0m" if color_output else line
        output.append(f"\033[{y + offset};{x}H{rendered}")

    stdout = sys.stdout
    if hasattr(stdout, "reconfigure") and getattr(stdout, "encoding", "").lower() != "utf-8":
        try:
            stdout.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    stdout.write("".join(output))
    stdout.flush()


def render_line(
    direction: str,
    length: int,
    x: int,
    y: int,
    color: str,
    *,
    color_output: bool = True,
) -> None:
    if length < 1 or x < 1 or y < 1:
        raise ValueError("line length and coordinates must be positive.")
    normalized = direction.lower()
    if normalized not in {"horizontal", "vertical"}:
        raise ValueError("line direction must be horizontal or vertical.")
    if normalized == "horizontal" and x + length - 1 > get_terminal_width():
        raise ValueError("horizontal line exceeds terminal width.")
    if normalized == "vertical" and y + length - 1 > get_terminal_height():
        raise ValueError("vertical line exceeds terminal height.")

    rendered = "─" * length if normalized == "horizontal" else "│" * length
    rendered = f"{_color_code(color)}{rendered}\033[0m" if color_output else rendered
    stdout = sys.stdout
    if hasattr(stdout, "reconfigure") and getattr(stdout, "encoding", "").lower() != "utf-8":
        try:
            stdout.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    position = f"\033[{y};{x}H"
    stdout.write(position + rendered)
    stdout.flush()
