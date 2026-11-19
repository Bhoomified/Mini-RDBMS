"""Result type used at integration boundaries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar, cast

from .errors import MiniRdbmsError

T = TypeVar("T")


@dataclass(frozen=True)
class Result(Generic[T]):
    """Represent either a successful value or an expected domain error."""

    value: T | None = None
    error: MiniRdbmsError | None = None
    _successful: bool = False

    def __post_init__(self) -> None:
        if self._successful == (self.error is not None):
            raise ValueError("Result must contain exactly one value or error")

    @classmethod
    def ok(cls, value: T) -> "Result[T]":
        """Create a successful result."""
        return cls(value=value, _successful=True)

    @classmethod
    def fail(cls, error: MiniRdbmsError) -> "Result[T]":
        """Create a failed result."""
        return cls(error=error)

    @property
    def is_ok(self) -> bool:
        """Return whether the result contains a value."""
        return self._successful

    def unwrap(self) -> T:
        """Return the value or raise the contained domain error."""
        if self.error is not None:
            raise self.error
        return cast(T, self.value)
