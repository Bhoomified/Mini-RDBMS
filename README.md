# Mini RDBMS Engine

Mini RDBMS Engine with Query Processing & Transaction Support — KLE Tech mini project.

## Team
- Subham — Query Parsing Engine (POCD)
- Bhoomi — Query Optimization Engine (DAA)
- Soumya — Transaction & Concurrency Manager (OSPP)
- Sneha — Storage Engine (DBMS)

## Branches
Each member works on their own feature branch:
- feature/parser
- feature/optimizer
- feature/transactions
- feature/storage

Merge into `main` only after your module's own tests pass. See the team's Interface Contracts doc before changing any shared function signature.

## Run
python main.py

## Test
pytest tests/

main.py — structural stub only, no engine logic yet:

python
"""
Entry point for the Mini RDBMS Engine.
Each import below stays commented out until that member's module is ready.
Nobody should uncomment someone else's line without checking with them first.
"""

# from engine.parser.parser import parse
# from engine.optimizer.planner import make_execution_plan
# from engine.transactions.transaction_manager import TransactionManager
# from engine.storage.storage_engine import StorageEngine


def run_engine():
    """Will eventually wire parser -> optimizer -> transaction manager -> storage."""
    print("Mini RDBMS Engine — scaffolding only, engines not yet connected.")


if __name__ == "__main__":
    run_engine()