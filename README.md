# Mini RDBMS Engine

A lightweight relational database implementation with
query processing, query optimization and transaction support.

## Project Goal

To build a transparent Mini RDBMS that demonstrates how a
database interprets SQL queries, validates them, selects
execution strategies, manages transactions and stores data.

## Technology

- Python 3.10+
- Python Standard Library
- SQL subset implemented from scratch
- unittest for automated testing

## Architecture

The project contains four primary engines:

1. Query Parsing Engine (E1)
2. Query Optimization Engine (E2)
3. Transaction and Concurrency Engine (E3)
4. Storage and Integrity Engine (E4)

Supporting components include query execution, integration
and the command-line interface.

## Project Structure

The new implementation is maintained under:

src/mini_rdbms/

Tests are maintained under:

tests/

Technical documentation is maintained under:

docs/rebuild/

## Development Setup

Create a virtual environment:

python3 -m venv .venv

Activate it:

source .venv/bin/activate

Run tests:

PYTHONPATH=src python -m unittest discover -s tests -v

## Current Development Status

Stage 1: Repository and project foundation.

The database engines are being implemented incrementally.
Each component will be tested independently before integration.

## Scope

The project focuses on a bounded SQL subset, relational
data storage, indexing, query execution, transaction
management and concurrency control.

It is an educational database implementation, not a
production replacement for established RDBMS software.