"""Readable AST formatting for diagnostics and EXPLAIN output."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any


def format_ast(node: Any, indent: int = 0) -> str:
    """Format an AST dataclass as a compact, indented tree."""
    prefix = " " * indent
    if is_dataclass(node):
        lines = [f"{prefix}{type(node).__name__}("]
        for field_name, value in asdict(node).items():
            lines.append(f"{' ' * (indent + 2)}{field_name}=")
            lines.append(format_ast(value, indent + 4))
        lines.append(f"{prefix})")
        return "\n".join(lines)
    if isinstance(node, tuple):
        if not node:
            return f"{prefix}()"
        return "\n".join([f"{prefix}("] + [format_ast(item, indent + 2) for item in node] + [f"{prefix})"])
    if isinstance(node, list):
        return format_ast(tuple(node), indent)
    if isinstance(node, Enum):
        return f"{prefix}{node.value!r}"
    return f"{prefix}{node!r}"
