"""TUI API exposed through the Thunder package."""

from src.tui import (
    get_terminal_height,
    get_terminal_width,
    render_box,
    render_line,
    render_text,
)

__all__ = [
    "get_terminal_height",
    "get_terminal_width",
    "render_box",
    "render_line",
    "render_text",
]
