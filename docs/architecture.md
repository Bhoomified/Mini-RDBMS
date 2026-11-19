# Architecture

The current data flow is:

1. `Session` receives SQL text.
2. `Lexer` produces position-aware tokens.
3. `Parser` builds dataclass AST nodes.
4. `SemanticAnalyzer` checks the AST against `Catalog` metadata.
5. `Planner` selects a full scan or applicable index path.
6. `Executor` retrieves candidate rows and evaluates all predicates.
7. `StorageEngine` applies schema and integrity checks.
8. `TransactionManager` coordinates undo callbacks and table locks.

`Database` owns the catalog, storage engine, index manager, and transaction
manager. The CLI and localhost web GUI use this same integration path. The
default database path is anchored to the project installation, so launch
location does not change which database is opened. Tests can create an
in-memory database by passing no path.

The binary save format persists table schemas, rows, and index definitions.
WAL-backed atomic image commits recover the last committed image after an
interrupted replacement.
