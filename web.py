"""Root launcher for the Mini RDBMS web interface."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent / "src"))
from mini_rdbms.web import serve


if __name__ == "__main__":
    serve()
