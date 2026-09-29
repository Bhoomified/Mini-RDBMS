"""
index.py  -  Hash indexes for the Query Optimizer (Bhoomi / DAA)

A HashIndex maps  column value -> list of row ids  for ONE column.
It only helps with EQUALITY lookups (col = value):  O(1) average
instead of scanning every row (O(n)).  It can NOT answer  > < >=  <=
(a hash has no ordering), so the planner never uses it for those.

IndexManager keeps all indexes of all tables and keeps them in sync
with INSERT / UPDATE / DELETE.  An index that is not kept in sync
gives silently wrong answers, so every write path must call it.
"""


class HashIndex:
    def __init__(self, column=None):
        self.column = column
        self.map = {}  # value -> list of row ids

    def insert(self, value, row_id):
        self.map.setdefault(value, []).append(row_id)

    def remove(self, value, row_id):
        ids = self.map.get(value)
        if not ids or row_id not in ids:
            return
        ids.remove(row_id)
        if not ids:                      # don't leave empty buckets behind
            del self.map[value]

    def update(self, old_value, new_value, row_id):
        if old_value == new_value:
            return
        self.remove(old_value, row_id)
        self.insert(new_value, row_id)

    def lookup(self, value):
        return list(self.map.get(value, []))   # copy, so callers can't corrupt the index

    def build(self, rows, id_key="id"):
        """(Re)build from existing rows, e.g. when CREATE INDEX runs on a table that already has data."""
        self.map = {}
        for row in rows:
            self.insert(row[self.column], row[id_key])


class IndexManager:
    def __init__(self):
        self.indexes = {}   # {table_name: {column_name: HashIndex}}  <- shape the planner expects

    def create_index(self, table, column, rows=(), id_key="id"):
        idx = HashIndex(column)
        idx.build(rows, id_key)
        self.indexes.setdefault(table, {})[column] = idx
        return idx

    def has_index(self, table, column):
        return column in self.indexes.get(table, {})

    # ---- call these from the write path (INSERT / UPDATE / DELETE) ----
    def on_insert(self, table, row, row_id):
        for col, idx in self.indexes.get(table, {}).items():
            idx.insert(row[col], row_id)

    def on_delete(self, table, row, row_id):
        for col, idx in self.indexes.get(table, {}).items():
            idx.remove(row[col], row_id)

    def on_update(self, table, old_row, new_row, row_id):
        for col, idx in self.indexes.get(table, {}).items():
            idx.update(old_row[col], new_row[col], row_id)
