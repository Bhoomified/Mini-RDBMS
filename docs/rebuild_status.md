# Rebuild status

## Implemented foundation

Completed:

- Created the `src`-based Python package layout.
- Added standard-library-only project metadata.
- Added setup and testing instructions.
- Added the initial package import test.
- Added common error, result, type, and component contracts.
- Added lexer, parser, AST, grammar, AST printer, and semantic validation.
- Added binary record codec, fixed pages, slotted pages, and page manager.
- Added hash/ordered indexes and transaction/concurrency primitives.
- Added basic catalog, storage, SQL executor, database, and session layers.
- Added integration coverage for create/insert/select/update/rollback.
- Added query-plan data structures, rule-based planner foundation, and CLI shell.
- Added custom binary database save/load and WAL record/recovery primitives.
- Added index-aware SELECT execution and EXPLAIN token/AST/plan output.
- Added table-level transaction lock integration, concurrency coverage, and a
  repeatable equality-lookup benchmark.
- Persisted index definitions and rebuilt index entries after reopening.
- Integrated WAL-backed atomic binary-image commits and session-close rollback.
- Added SQL script-file execution, database-path CLI selection, indexed
  UPDATE/DELETE candidates, and full-scan benchmark output.
- Integrated heap rows with slotted pages, RID location tracking, page
  allocation, and record relocation.
- Added subprocess WAL crash-recovery coverage.
- Integrated heap page images and RID mappings into the page-framed durable
  database file.
- Added WAL BEGIN records, page IDs, CRC32 validation, and safe incomplete-log
  handling.
- Changed indexed execution to fetch selected RIDs directly from heap storage.
- Added youngest-transaction deadlock victim rollback and wake-up behavior.
- Applied committed WAL page images individually during persistence and restart
  recovery, while retaining legacy full-image recovery compatibility.
- Completed B+Tree deletion rebalancing, merging, redistribution, and root
  shrinking.
- Added root launchers, installable `minirdb`/`minirdb-web` commands, and a
  project-anchored default database path.
- Added the localhost GUI with engine cards, execution traces, schema display,
  demo setup, SQL execution, and transaction controls.
- Added automatic HASH indexes for equality predicates and automatic B+Tree
  indexes for comparator predicates.
- Added automatic transactions for standalone DML and atomic multi-row
  primary-key validation.
- Added rollback of failed explicit transactions and index rebuilding from
  restored table rows.

## Remaining work

- Cost-based planning and multi-table query features.
- Broader crash injection during filesystem writes and process termination.
