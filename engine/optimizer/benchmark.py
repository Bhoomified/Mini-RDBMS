"""
benchmark.py  -  evidence for the complexity-analysis section of the report.

Run from the repo root:
    python -m engine.optimizer.benchmark
"""
import timeit

from engine.optimizer.demo import make_data, run_plan
from engine.optimizer.index import IndexManager
from engine.optimizer.planner import make_execution_plan


def main():
    print(f"{'rows':>8} | {'full_scan (ms)':>15} | {'index (ms)':>11} | speedup")
    print("-" * 52)
    for n in (1_000, 10_000, 100_000):
        rows = make_data(n)
        by_id = {r["id"]: r for r in rows}
        im = IndexManager()
        im.create_index("students", "id", rows)
        query = {"type": "SELECT", "table": "students", "columns": ["*"],
                 "conditions": [{"column": "id", "op": "=", "value": n // 2}]}
        p_idx = make_execution_plan(query, None, im.indexes)
        p_scan = make_execution_plan(query, None, {})
        runs = 200
        t_scan = timeit.timeit(lambda: run_plan(p_scan, by_id, rows, {}), number=runs) / runs * 1000
        t_idx = timeit.timeit(lambda: run_plan(p_idx, by_id, rows, im.indexes), number=runs) / runs * 1000
        print(f"{n:>8} | {t_scan:>15.4f} | {t_idx:>11.5f} | {t_scan / t_idx:>6.0f}x")


if __name__ == "__main__":
    main()
