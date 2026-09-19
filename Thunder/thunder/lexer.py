"""Lexer API for Thunder.

The implementation remains compatible with the original single-file MVP while
exposing the frontend by responsibility.
"""

from src.main import Token, tokenize

__all__ = ["Token", "tokenize"]
