"""
planner.py  -  Query Optimizer (Bhoomi / DAA)

Input : Query object (from Subham's parser)  +  schema  +  indexes
Output: Execution Plan dict (goes to Soumya's transaction manager)

Decision rule (simple, explainable, defensible in the report):
  * Only SELECT / UPDATE / DELETE with a WHERE clause can use an index.
  * Conditions are treated as AND-ed together.
  * If ANY condition is  column = value  AND that column has a HashIndex
        -> access_path = "index_lookup"   (O(1) average to find candidate rows)
     every other condition is kept in "residual_conditions" and must still
     be checked on the rows the index returns.
  * Otherwise -> "full_scan" (O(n)), and ALL conditions are residual.
"""

EQUALITY_OPS = {"=", "=="}
FILTERABLE = {"SELECT", "UPDATE", "DELETE"}          # operations that read rows via WHERE
PASSTHROUGH_KEYS = ("columns", "values", "set", "order_by")   # payload the executor needs


def _validate(query, schema):
    if not isinstance(query, dict) or "type" not in query:
        raise ValueError("Invalid query object: missing 'type'")
    if query["type"] in ("BEGIN", "COMMIT", "ROLLBACK"):
        return
    if not query.get("table"):
        raise ValueError(f"Invalid {query['type']} query: missing 'table'")
    if schema is None:
        return
    table = query["table"]
    if query["type"] != "CREATE" and table not in schema:
        raise ValueError(f"Unknown table: {table}")
    for cond in query.get("conditions") or []:
        if cond["column"] not in schema.get(table, {}):
            raise ValueError(f"Unknown column '{cond['column']}' in table '{table}'")


def _pick_index_condition(table, conditions, indexes):
    """Return the first equality condition whose column is indexed, else None."""
    table_indexes = (indexes or {}).get(table, {})
    for cond in conditions:
        if cond["op"] in EQUALITY_OPS and cond["column"] in table_indexes:
            return cond
    return None


def make_execution_plan(query, schema=None, indexes=None):
    """
    query   : Query object,  e.g. {'type':'SELECT','table':'students','columns':['name'],
                                   'conditions':[{'column':'id','op':'=','value':5}]}
    schema  : {table: {column: type}}          (optional; enables validation)
    indexes : {table: {column: HashIndex}}     (IndexManager().indexes)
    """
    _validate(query, schema)
    qtype = query["type"]
    plan = {"operation": qtype, "table": query.get("table")}

    if qtype in FILTERABLE:
        conditions = query.get("conditions") or []
        chosen = _pick_index_condition(query["table"], conditions, indexes)
        if chosen is not None:
            plan.update(
                access_path="index_lookup",
                index_column=chosen["column"],
                index_value=chosen["value"],
                residual_conditions=[c for c in conditions if c is not chosen],
                estimated_cost="O(1) avg",
            )
        else:
            plan.update(
                access_path="full_scan",
                residual_conditions=list(conditions),
                estimated_cost="O(n)",
            )
    elif qtype == "INSERT":
        plan.update(access_path="append", estimated_cost="O(1)")
    elif qtype == "CREATE":
        plan.update(access_path="catalog", estimated_cost="O(1)")
    else:  # BEGIN / COMMIT / ROLLBACK
        plan.update(access_path="control", estimated_cost="O(1)")

    for key in PASSTHROUGH_KEYS:
        if key in query:
            plan[key] = query[key]
    return plan
