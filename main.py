"""Root launcher for the Mini RDBMS command-line interface."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent / "src"))
from mini_rdbms.main import main

if __name__ == "__main__":
    main()
