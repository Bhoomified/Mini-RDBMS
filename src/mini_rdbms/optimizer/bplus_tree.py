"""Small node-based B+ Tree for ordered equality and range lookup."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from mini_rdbms.common.types import RecordId


@dataclass
class _Leaf:
    keys: list[Any] = field(default_factory=list)
    values: list[set[RecordId]] = field(default_factory=list)
    next: "_Leaf | None" = None


@dataclass
class _Internal:
    keys: list[Any] = field(default_factory=list)
    children: list[Any] = field(default_factory=list)


class BPlusTree:
    """Educational B+ Tree with bounded nodes and linked leaves."""

    def __init__(self, order: int = 4) -> None:
        if order < 3:
            raise ValueError("B+ Tree order must be at least 3")
        self.order = order
        self.root: _Leaf | _Internal = _Leaf()

    def insert(self, key: Any, record_id: RecordId) -> None:
        """Insert a record ID, splitting a full leaf or internal node."""
        split = self._insert(self.root, key, record_id)
        if split is not None:
            separator, right = split
            self.root = _Internal([separator], [self.root, right])

    def search(self, key: Any) -> set[RecordId]:
        leaf = self._find_leaf(key)
        for index, existing in enumerate(leaf.keys):
            if existing == key:
                return set(leaf.values[index])
        return set()

    def range_search(
        self,
        lower: Any | None = None,
        upper: Any | None = None,
        include_lower: bool = True,
        include_upper: bool = True,
    ) -> set[RecordId]:
        leaf = self._find_leaf(lower) if lower is not None else self._leftmost()
        result: set[RecordId] = set()
        while leaf is not None:
            for key, values in zip(leaf.keys, leaf.values):
                if lower is not None and (key < lower or (key == lower and not include_lower)):
                    continue
                if upper is not None and (key > upper or (key == upper and not include_upper)):
                    return result
                result.update(values)
            leaf = leaf.next
        return result

    def delete(self, key: Any, record_id: RecordId) -> None:
        """Remove one record ID and rebalance nodes which fall below minimum size."""
        self._delete(self.root, key, record_id)
        if isinstance(self.root, _Internal):
            if len(self.root.children) == 1:
                self.root = self.root.children[0]
            if isinstance(self.root, _Internal):
                self.root.keys = self._separators(self.root.children)

    def update(self, old_key: Any, new_key: Any, record_id: RecordId) -> None:
        self.delete(old_key, record_id)
        self.insert(new_key, record_id)

    def rebuild(self, records: list[tuple[Any, RecordId]]) -> None:
        self.root = _Leaf()
        for key, record_id in records:
            self.insert(key, record_id)

    def _insert(self, node, key, record_id):
        if isinstance(node, _Leaf):
            for index, existing in enumerate(node.keys):
                if existing == key:
                    node.values[index].add(record_id)
                    return None
                if key < existing:
                    node.keys.insert(index, key)
                    node.values.insert(index, {record_id})
                    break
            else:
                node.keys.append(key)
                node.values.append({record_id})
            if len(node.keys) <= self.order:
                return None
            midpoint = len(node.keys) // 2
            right = _Leaf(node.keys[midpoint:], node.values[midpoint:], node.next)
            node.keys = node.keys[:midpoint]
            node.values = node.values[:midpoint]
            node.next = right
            return right.keys[0], right

        child_index = 0
        while child_index < len(node.keys) and key >= node.keys[child_index]:
            child_index += 1
        split = self._insert(node.children[child_index], key, record_id)
        if split is None:
            return None
        separator, right = split
        node.keys.insert(child_index, separator)
        node.children.insert(child_index + 1, right)
        if len(node.children) <= self.order:
            return None
        midpoint = len(node.keys) // 2
        promoted = node.keys[midpoint]
        right_internal = _Internal(
            node.keys[midpoint + 1 :],
            node.children[midpoint + 1 :],
        )
        node.keys = node.keys[:midpoint]
        node.children = node.children[: midpoint + 1]
        return promoted, right_internal

    def _find_leaf(self, key: Any) -> _Leaf:
        node = self.root
        while isinstance(node, _Internal):
            child_index = 0
            while child_index < len(node.keys) and key >= node.keys[child_index]:
                child_index += 1
            node = node.children[child_index]
        return node

    def _delete(self, node, key: Any, record_id: RecordId) -> bool:
        """Delete below *node*, returning whether that node is underfull."""
        if isinstance(node, _Leaf):
            for index, existing in enumerate(node.keys):
                if existing == key:
                    node.values[index].discard(record_id)
                    if not node.values[index]:
                        node.keys.pop(index)
                        node.values.pop(index)
                    return len(node.keys) < self._minimum_keys
                if key < existing:
                    break
            return False

        child_index = 0
        while child_index < len(node.keys) and key >= node.keys[child_index]:
            child_index += 1
        child = node.children[child_index]
        child_underfull = self._delete(child, key, record_id)
        if child_underfull:
            self._rebalance_child(node, child_index)
        node.keys = self._separators(node.children)
        return len(node.children) < self._minimum_children

    @property
    def _minimum_keys(self) -> int:
        return (self.order + 1) // 2

    @property
    def _minimum_children(self) -> int:
        return (self.order + 1) // 2

    def _first_key(self, node) -> Any:
        while isinstance(node, _Internal):
            node = node.children[0]
        return node.keys[0]

    def _separators(self, children: list[Any]) -> list[Any]:
        return [self._first_key(child) for child in children[1:]]

    def _rebalance_child(self, parent: _Internal, index: int) -> None:
        """Borrow from a sibling when possible, otherwise merge the child."""
        child = parent.children[index]
        left = parent.children[index - 1] if index else None
        right = parent.children[index + 1] if index + 1 < len(parent.children) else None

        if isinstance(child, _Leaf):
            if isinstance(left, _Leaf) and len(left.keys) > self._minimum_keys:
                child.keys.insert(0, left.keys.pop())
                child.values.insert(0, left.values.pop())
                return
            if isinstance(right, _Leaf) and len(right.keys) > self._minimum_keys:
                child.keys.append(right.keys.pop(0))
                child.values.append(right.values.pop(0))
                return
            if isinstance(left, _Leaf):
                left.keys.extend(child.keys)
                left.values.extend(child.values)
                left.next = child.next
                parent.children.pop(index)
            elif isinstance(right, _Leaf):
                child.keys.extend(right.keys)
                child.values.extend(right.values)
                child.next = right.next
                parent.children.pop(index + 1)
            return

        if isinstance(left, _Internal) and len(left.children) > self._minimum_children:
            child.children.insert(0, left.children.pop())
            left.keys = self._separators(left.children)
            child.keys = self._separators(child.children)
            return
        if isinstance(right, _Internal) and len(right.children) > self._minimum_children:
            child.children.append(right.children.pop(0))
            right.keys = self._separators(right.children)
            child.keys = self._separators(child.children)
            return
        if isinstance(left, _Internal):
            left.children.extend(child.children)
            left.keys = self._separators(left.children)
            parent.children.pop(index)
        elif isinstance(right, _Internal):
            child.children.extend(right.children)
            child.keys = self._separators(child.children)
            parent.children.pop(index + 1)

    def _leftmost(self) -> _Leaf:
        node = self.root
        while isinstance(node, _Internal):
            node = node.children[0]
        return node
