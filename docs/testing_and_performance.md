# Testing and performance

Run the complete test suite from the project directory:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

After editable installation, applications can be launched from any directory
with `minirdb` and `minirdb-web`. The root `main.py` and `web.py` launchers
work without manually setting `PYTHONPATH`.

The tests cover common contracts, lexical positions and errors, AST parsing,
semantic validation, binary records, fixed pages, slotted pages, indexes,
transactions, locking, SQL workflows, persistence reopening, WAL record
recovery, indexed `EXPLAIN` execution, atomic multi-row DML, failed
transaction rollback, and index consistency after rollback.

Run the benchmark with:

```bash
PYTHONPATH=src python3 benchmarks/benchmark.py
```

The benchmark inserts 10,000 rows, creates a hash index, and measures one
equality lookup using `time.perf_counter`. It reports an observed value only;
the project does not claim that a target is met until it is measured on the
target hardware.

The expanded benchmark also measures B+Tree equality/range access, a genuine
full scan, parsing, planning, persistence, and reopen time. One observed run
in this workspace (Python 3.9.6 on macOS) reported:

```text
hash equality       0.041 ms
B+Tree equality     0.019 ms
B+Tree range       27.558 ms
full scan          58.137 ms
parse               0.090 ms
plan               39.863 ms
persist            40.905 ms
reopen             18.577 ms
```

The project metadata targets Python 3.10 or newer; the timings above document
the available runtime rather than a performance guarantee.

Known limitations include limited SQL grammar and a logical heap facade that is
simpler than a production buffer manager. The test suite includes committed,
uncommitted, and subprocess WAL-image recovery cases; it does not forcibly
terminate a process during every filesystem write boundary.
