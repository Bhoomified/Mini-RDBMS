# Engine design

## Parsing engine

The lexer scans left to right with anchored regular expressions. Keywords are
looked up in a dictionary after a word is recognized. The recursive-descent
parser has one method for each statement family and creates typed AST nodes.

## Semantic validation

The analyzer uses the read-only catalog protocol to validate tables, columns,
literal types, duplicate definitions, and index declarations. Storage repeats
type and constraint checks before writes.

## Optimization engine

The planner prefers a hash index for equality predicates and an ordered index
for equality or range predicates. A full scan remains the fallback. The
executor always evaluates every `WHERE` condition after candidate retrieval.

## Transactions and concurrency

Transactions maintain state, acquired locks, and reverse-order undo callbacks.
The lock manager uses a `Condition` rather than polling. The wait-for graph
detects cycles when incompatible table locks conflict.

## Storage engine

Records have schema-driven binary encoding. The slotted page implementation
uses a header, slot directory, and record data area. Storage persistence writes
the heap's fixed-size page images and RID locations through `PageManager`,
then restores them before the catalog and indexes are rebuilt.
