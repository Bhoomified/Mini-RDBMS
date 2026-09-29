import pytest

from engine.optimizer.index import HashIndex, IndexManager
from engine.optimizer.planner import make_execution_plan

SCHEMA = {"students": {"id": "INT", "name": "TEXT", "age": "INT"}}


def select(conds):
    return {"type": "SELECT", "table": "students", "columns": ["*"], "conditions": conds}


def cond(col, op, val):
    return {"column": col, "op": op, "value": val}


def indexed(*cols):
    im = IndexManager()
    for c in cols:
        im.create_index("students", c, [])
    return im.indexes


# ---------- planner ----------
def test_equality_on_indexed_column_uses_index():
    plan = make_execution_plan(select([cond("id", "=", 5)]), SCHEMA, indexed("id"))
    assert plan["access_path"] == "index_lookup"
    assert plan["index_column"] == "id" and plan["index_value"] == 5
    assert plan["estimated_cost"] == "O(1) avg"
    assert plan["residual_conditions"] == []


def test_range_on_indexed_column_falls_back_to_full_scan():
    plan = make_execution_plan(select([cond("id", ">", 5)]), SCHEMA, indexed("id"))
    assert plan["access_path"] == "full_scan"
    assert plan["residual_conditions"] == [cond("id", ">", 5)]


def test_equality_on_unindexed_column_full_scan():
    plan = make_execution_plan(select([cond("age", "=", 20)]), SCHEMA, indexed("id"))
    assert plan["access_path"] == "full_scan"


def test_no_where_clause_full_scan():
    plan = make_execution_plan(select([]), SCHEMA, indexed("id"))
    assert plan["access_path"] == "full_scan" and plan["estimated_cost"] == "O(n)"


def test_no_indexes_at_all():
    assert make_execution_plan(select([cond("id", "=", 1)]), SCHEMA, {})["access_path"] == "full_scan"


def test_mixed_conditions_index_used_and_rest_are_residual():
    a, b = cond("age", ">", 18), cond("id", "=", 7)
    plan = make_execution_plan(select([a, b]), SCHEMA, indexed("id"))
    assert plan["access_path"] == "index_lookup" and plan["index_column"] == "id"
    assert plan["residual_conditions"] == [a]


def test_update_and_delete_can_use_index():
    for t in ("UPDATE", "DELETE"):
        q = {"type": t, "table": "students", "conditions": [cond("id", "=", 3)], "set": {"age": 1}}
        assert make_execution_plan(q, SCHEMA, indexed("id"))["access_path"] == "index_lookup"


def test_insert_and_control_plans():
    ins = make_execution_plan({"type": "INSERT", "table": "students", "values": [1, "a", 2]}, SCHEMA, {})
    assert ins["operation"] == "INSERT" and ins["values"] == [1, "a", 2]
    assert make_execution_plan({"type": "BEGIN"}, SCHEMA, {})["access_path"] == "control"


def test_unknown_table_and_column_rejected():
    with pytest.raises(ValueError):
        make_execution_plan({"type": "SELECT", "table": "nope", "conditions": []}, SCHEMA, {})
    with pytest.raises(ValueError):
        make_execution_plan(select([cond("ghost", "=", 1)]), SCHEMA, {})
    with pytest.raises(ValueError):
        make_execution_plan({"columns": ["*"]}, SCHEMA, {})


# ---------- index ----------
def test_hash_index_insert_lookup_remove_update():
    idx = HashIndex("age")
    idx.insert(20, 1); idx.insert(20, 2); idx.insert(21, 3)
    assert idx.lookup(20) == [1, 2]
    idx.remove(20, 1)
    assert idx.lookup(20) == [2]
    idx.update(21, 22, 3)
    assert idx.lookup(21) == [] and idx.lookup(22) == [3]
    assert idx.lookup(999) == []


def test_lookup_returns_copy():
    idx = HashIndex("age"); idx.insert(1, 10)
    idx.lookup(1).append(999)
    assert idx.lookup(1) == [10]


def test_index_manager_stays_in_sync_with_writes():
    im = IndexManager()
    im.create_index("students", "age", [])
    row = {"id": 1, "name": "A", "age": 20}
    im.on_insert("students", row, 1)
    assert im.indexes["students"]["age"].lookup(20) == [1]
    new = {"id": 1, "name": "A", "age": 25}
    im.on_update("students", row, new, 1)
    assert im.indexes["students"]["age"].lookup(20) == []
    assert im.indexes["students"]["age"].lookup(25) == [1]
    im.on_delete("students", new, 1)
    assert im.indexes["students"]["age"].lookup(25) == []


def test_create_index_on_existing_rows():
    rows = [{"id": i, "name": "x", "age": i % 3} for i in range(1, 7)]
    idx = IndexManager().create_index("students", "age", rows)
    assert sorted(idx.lookup(0)) == [3, 6]


def test_index_path_matches_full_scan_results():
    """Correctness first: both access paths must return the same rows."""
    from engine.optimizer.demo import make_data, run_plan
    rows = make_data(500)
    by_id = {r["id"]: r for r in rows}
    im = IndexManager(); im.create_index("students", "id", rows)
    q = select([cond("id", "=", 250), cond("age", ">", 0)])
    p_idx, p_scan = make_execution_plan(q, SCHEMA, im.indexes), make_execution_plan(q, SCHEMA, {})
    assert run_plan(p_idx, by_id, rows, im.indexes) == run_plan(p_scan, by_id, rows, {})
