"""Wait-for graph deadlock detection."""

from __future__ import annotations


class WaitForGraph:
    """Directed graph where an edge means one transaction waits for another."""

    def __init__(self) -> None:
        self._edges: dict[int, set[int]] = {}

    def add_wait(self, waiter: int, holder: int) -> None:
        self._edges.setdefault(waiter, set()).add(holder)

    def remove_wait(self, waiter: int, holder: int | None = None) -> None:
        if waiter not in self._edges:
            return
        if holder is None:
            self._edges.pop(waiter, None)
        else:
            self._edges[waiter].discard(holder)
            if not self._edges[waiter]:
                self._edges.pop(waiter)

    def remove_holder(self, holder: int) -> None:
        """Remove edges waiting on a transaction that has been aborted."""
        for waiter in list(self._edges):
            self._edges[waiter].discard(holder)
            if not self._edges[waiter]:
                self._edges.pop(waiter, None)

    def has_cycle(self) -> bool:
        return bool(self.cycle_nodes())

    def cycle_nodes(self) -> set[int]:
        """Return transactions participating in one detected cycle."""
        visiting: set[int] = set()
        visited: set[int] = set()
        cycle: set[int] = set()
        stack: list[int] = []

        def visit(node: int) -> bool:
            if node in visiting:
                cycle.update(stack[stack.index(node) :])
                return True
            if node in visited:
                return False
            visiting.add(node)
            stack.append(node)
            if any(visit(child) for child in self._edges.get(node, ())):
                return True
            stack.pop()
            visiting.remove(node)
            visited.add(node)
            return False

        for node in self._edges:
            if visit(node):
                break
        return cycle
