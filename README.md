# Mini RDBMS Rebuild

An educational relational database engine implemented from scratch in Python
using only the standard library. It demonstrates SQL tokenization, parsing,
semantic validation, query planning, indexing, transactions, concurrency,
binary storage, and recovery without using SQLite, an ORM, or an external SQL
parser.

This is a college mini-project implementation, not a production database.
Designs favor readable algorithms and explicit data flow over completeness.

## 1. Problem statement

Database systems combine language processing, data structures, storage
management, integrity rules, and concurrency control. The project implements a
small integrated system to demonstrate those responsibilities in a form that
can be inspected and explained during a project review.

## 2. Objectives

- Accept a documented SQL subset.
- Tokenize and parse SQL into an abstract syntax tree.
- Validate statements against catalog metadata.
- Select full-scan or indexed access paths.
- Enforce basic type and key constraints.
- Support transactions, rollback, locking, and deadlock detection.
- Store records using binary encodings and slotted pages.
- Persist database state and recover committed WAL images.
- Provide tests, demonstrations, and repeatable benchmarks.

## 3. Technology stack

- Python 3.10 or newer
- Python standard library only
- `dataclasses`, `enum`, `struct`, `threading`, `argparse`, `unittest`
- No SQLite, SQLAlchemy, ORM, pickle, JSON database files, or parser library

The current environment used for validation has Python 3.9.6. The project
metadata still requires Python 3.10 or newer.

## 4. Architecture

The execution pipeline is:

```text
SQL text
  -> Lexer
  -> recursive-descent Parser
  -> AST
  -> SemanticAnalyzer + Catalog
  -> Planner
  -> Executor
  -> StorageEngine / IndexManager
  -> Result
```

`Database` owns shared catalog, storage, index, WAL, and transaction
components. Each `Session` owns its transaction state and statement executor.
See `docs/architecture.md` for the component data flow.

## 5. Four primary engines

### E1 — Query parsing engine

`parser/lexer.py` recognizes tokens and source positions. `parser/parser.py`
uses recursive descent to build AST dataclasses. `parser/semantic.py` validates
names, types, columns, and constraints using catalog metadata.

### E2 — Query optimization engine

`optimizer/planner.py` chooses a full scan, hash lookup, B+Tree equality
lookup, or B+Tree range lookup. `optimizer/executor.py` retrieves candidates
and evaluates every remaining predicate.

### E3 — Transaction and concurrency engine

`transactions/` provides transaction state, reverse-order undo callbacks,
shared/exclusive table locks, `Condition` waiting, and wait-for graph cycle
detection.

### E4 — Storage and integrity engine

`storage/` provides schema-driven binary records, fixed pages, slotted pages,
heap organization, catalog metadata, binary database images, and WAL records.
Storage validates types, NULLability, and primary-key uniqueness before writes.

## 6. Project structure

```text
MiniRDBMS_Rebuild/
├── src/mini_rdbms/
│   ├── common/          # Errors, Result, shared types and protocols
│   ├── parser/          # Tokens, lexer, grammar, AST, parser, semantics
│   ├── storage/         # Codec, pages, heap, catalog, WAL, persistence
│   ├── optimizer/       # Hash index, B+Tree, planner, executor
│   ├── transactions/    # Undo, locks, wait-for graph, manager
│   ├── execution/       # SQL statement executor
│   └── integration/     # Database and Session
├── tests/
│   ├── unit/
│   └── integration/
├── docs/
├── benchmarks/
├── examples/
├── data/
├── pyproject.toml
└── main.py
```

## 7. Supported SQL grammar

Supported statements:

```sql
CREATE TABLE table_name (
    column_name INT|FLOAT|TEXT|BOOL [NOT NULL] [PRIMARY KEY],
    ...
);

CREATE INDEX index_name ON table_name (column_name)
    [USING HASH|BTREE];

INSERT INTO table_name [(column, ...)]
    VALUES (value, ...), (value, ...);

SELECT *|column, ... FROM table_name
    [WHERE column operator value [AND ...]];

UPDATE table_name SET column = value [, ...]
    [WHERE column operator value [AND ...]];

DELETE FROM table_name
    [WHERE column operator value [AND ...]];

BEGIN [TRANSACTION];
COMMIT;
ROLLBACK;
EXPLAIN statement;
```

Comparison operators are `=`, `!=`, `<>`, `<`, `<=`, `>`, and `>=`.
Supported literals are integers, floats, strings, `NULL`, `TRUE`, and `FALSE`.
The authoritative grammar is in `docs/sql_grammar.ebnf`.

Not supported: joins, multiple-table queries, subqueries, aggregates, `GROUP
BY`, `HAVING`, and other advanced SQL features.

## 8. Lexer and parser methodology

The lexer scans left to right with anchored regular expressions. It recognizes
identifiers, numeric literals, SQL strings with doubled quote escaping,
operators, punctuation, comments, and whitespace. Invalid characters and
unterminated strings raise position-aware `LexicalError` instances.

The parser is handwritten recursive descent. Each major grammar production has
a corresponding parsing method. It produces typed dataclasses instead of
passing raw SQL strings to execution.

## 9. AST example

```sql
SELECT name FROM students WHERE age >= 18 AND id = 5;
```

is represented conceptually as:

```text
SelectStatement(
  table="students",
  columns=("name",),
  conditions=(
    Condition(column="age", operator=">=", value=18),
    Condition(column="id", operator="=", value=5),
  ),
)
```

`EXPLAIN` prints the token list, AST, semantic result, and selected plan.

## 10. B+Tree indexing methodology

The ordered index uses bounded internal nodes, leaf nodes, linked leaves,
duplicate-key record-ID sets, and node splitting. Equality searches descend
from the root to a leaf. Range searches walk linked leaves.

Hash indexes use a dictionary mapping values to record-ID sets and are intended
for equality predicates.

The B+Tree implements deletion redistribution, merging, separator
maintenance, and root shrinking. It remains an educational implementation
without production buffer-management features. Index definitions are persisted
and rebuilt when the database is reopened.

## 11. Full scan versus index lookup

A full scan visits all logical records and evaluates the complete predicate.
It is always available as a correctness fallback and preserves stable record
order.

An applicable hash or B+Tree condition first produces candidate record IDs.
The executor then evaluates all residual conditions, so an index cannot change
query semantics. `UPDATE` and `DELETE` use the same candidate mechanism.

## 12. Transaction workflow

`BEGIN` creates a transaction for the session. Writes register undo callbacks.
`COMMIT` marks the transaction committed, releases locks, and persists the
database image when using a durable database. `ROLLBACK` runs undo callbacks
in reverse order and releases locks.

A session closes by rolling back an unfinished transaction. Auto-commit
statements are persisted individually when a database path is configured.
Standalone DML is wrapped in an automatic transaction, so a failed statement
does not leave partial writes behind. Multi-row inserts prevalidate primary-key
conflicts, and an error inside an explicit transaction rolls back the whole
transaction. Indexes are rebuilt from the restored rows after rollback so
lookups remain consistent.

## 13. Locking and concurrency

The lock manager supports shared and exclusive table locks using
`threading.Lock` and `threading.Condition`. Waiting transactions sleep on the
condition rather than busy-looping. A wait-for graph records incompatible
waits and detects cycles.

Reads use shared table locks while writes acquire an exclusive table lock and,
for row updates/deletes, an exclusive row lock. A detected cycle selects the
largest transaction ID as the victim, rolls it back outside the condition
lock, releases its locks, and wakes waiting transactions. Shared-to-exclusive
lock upgrades are supported when no other reader holds the resource.

## 14. Page-based storage

`PageManager` reads and writes exactly 4096-byte binary pages. The durable file
has a page-framed superblock with a payload length and checksum, followed by
fixed-size payload pages. The payload stores each table's schema, slotted-page
images, RID-to-page/slot mappings, and index definitions.

This is an educational page layout, not a production buffer-managed file.
There is no checkpointing or page replacement policy.

## 15. Slotted-page organization

Each `SlottedPage` contains a header, slot directory, and record data area.
Variable-length records are packed from the end of the page while slot entries
remain at the front. Deleted slots can be reused. Updates can relocate a
record while preserving its logical RID.

## 16. Heap-file organization

`HeapFile` allocates slotted pages as records are inserted and maintains a
logical RID-to-page/slot location map. Scans return records in RID order.
Updates that no longer fit in their original slot relocate the encoded record.

## 17. Record encoding

`RecordCodec` serializes rows according to `TableSchema` using `struct` and
UTF-8. It stores a NULL bitmap followed by typed values:

- `INT`: signed 64-bit integer
- `FLOAT`: 64-bit floating point
- `BOOL`: one byte
- `TEXT`: 32-bit byte length followed by UTF-8 bytes

Invalid types, invalid NULL values, malformed records, and trailing bytes are
rejected.

## 18. WAL and crash recovery

`WriteAheadLog` stores binary records containing a magic value, transaction ID,
record type (`BEGIN`, `PAGE_IMAGE`, or `COMMIT`), page ID, payload length,
payload, and CRC32 checksum. The commit path appends each 4096-byte database
page as a page image, writes a commit record, flushes the WAL, and applies the
committed pages through `PageManager`.

Startup replays the last committed image if the replacement was interrupted.
Tests cover committed, uncommitted, and subprocess-exit recovery cases.
This is a simplified redo mechanism, not full ARIES recovery.

## 19. Installation and execution

From `MiniRDBMS_Rebuild/`:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --editable .
```

After installation, run the applications from any directory:

```bash
minirdb
minirdb-web
```

Without installation, run the root launchers from the project directory:

```bash
python main.py
python web.py
```

Run the interactive shell directly:

```bash
python main.py
```

Run a SQL script:

```bash
python main.py \
  --database data/minirdb.db examples/demo.sql
```

Run the local pastel web GUI:

```bash
python web.py
```

Open <http://127.0.0.1:8000>. The GUI supports SQL execution, `EXPLAIN`,
transaction buttons, result tables, schema inspection, index visibility, and
the same database file used by the CLI.

The default durable database path is `data/minirdb.db`. Use `--database` to
choose another path.

## 20. Testing commands

Run all tests:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

The suite covers common contracts, lexer errors and positions, parser ASTs,
semantic validation, record encoding, pages, heap relocation, hash indexes,
B+Tree splits and ranges, transactions, locking, persistence, WAL recovery,
indexed execution, and the CLI.

## 21. Benchmarking

Run:

```bash
PYTHONPATH=src python benchmarks/benchmark.py
```

The benchmark inserts 10,000 rows and reports indexed equality lookup and
full-scan timings using `time.perf_counter`. Results depend on hardware,
Python version, filesystem state, dataset size, and workload. The benchmark
does not claim that the original performance targets are universally met.

## 22. Error handling

Expected failures use the common hierarchy in `common/errors.py`, including
lexical, syntax, semantic, constraint, storage, transaction, deadlock, and
recovery errors. Integration boundaries return `Result` objects containing
either a value or a domain error.

## 23. Current implementation status

Implemented and tested:

- SQL lexer, parser, AST, grammar, and semantic validation
- Binary records, fixed pages, slotted pages, and heap relocation
- Hash indexes and node-based B+Tree insertion/range lookup
- Query planning, indexed SELECT/UPDATE/DELETE candidates, and `EXPLAIN`
- Transactions, undo logging, table locks, and wait-for cycle detection
- Atomic standalone and multi-row DML, failed-transaction rollback, and index
  restoration after rollback
- Binary persistence, index restoration, WAL commits, and recovery
- Interactive and script-based CLI

## 24. Current limitations

The following are intentionally incomplete:

- Full cost-based optimization and selectivity modeling
- Transaction page overlays/write sets
- Buffer replacement, checkpoints, and production-grade page management
- Full process fault injection at every filesystem write boundary
- Advanced SQL features listed as unsupported above

See `docs/rebuild_status.md`, `docs/architecture.md`,
`docs/engine_design.md`, `docs/storage_format.md`, and
`docs/testing_and_performance.md` for focused technical details.
