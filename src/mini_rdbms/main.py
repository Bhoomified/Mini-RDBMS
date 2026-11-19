"""Command-line SQL shell."""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    """Run an interactive SQL shell or execute a SQL script."""
    from mini_rdbms.integration.database import Database
    from mini_rdbms.integration.session import Session

    arguments = argparse.ArgumentParser(description="Mini RDBMS SQL shell")
    arguments.add_argument("script", nargs="?", help="SQL script file to execute")
    default_database = Path(__file__).resolve().parents[2] / "data" / "minirdb.db"
    arguments.add_argument("--database", default=str(default_database))
    options = arguments.parse_args()
    session = Session(Database(options.database))
    if options.script:
        with open(options.script, encoding="utf-8") as file:
            for statement in file.read().split(";"):
                if statement.strip():
                    result = session.execute(statement)
                    if result.is_ok:
                        print(result.value)
                    else:
                        print(f"{result.error.category} error: {result.error}")
        return
    print("Mini RDBMS. Enter SQL, or EXIT to quit.")
    while True:
        try:
            line = input("minirdb> ")
        except EOFError:
            print()
            break
        if line.strip().upper() in {"EXIT", "QUIT"}:
            break
        if not line.strip():
            continue
        result = session.execute(line)
        if result.is_ok:
            print(result.value)
        else:
            print(f"{result.error.category} error: {result.error}")


if __name__ == "__main__":
    main()
