import os
import subprocess
import sys
import tempfile
import unittest


class ScriptCliTest(unittest.TestCase):
    def test_cli_executes_script_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            script = os.path.join(directory, "demo.sql")
            with open(script, "w", encoding="utf-8") as file:
                file.write("CREATE TABLE t (id INT PRIMARY KEY); INSERT INTO t VALUES (1); SELECT * FROM t;")
            database = os.path.join(directory, "database.db")
            environment = dict(os.environ, PYTHONPATH="src")
            completed = subprocess.run(
                [sys.executable, "-m", "mini_rdbms.main", "--database", database, script],
                capture_output=True,
                text=True,
                env=environment,
                check=True,
            )
            self.assertIn("'id': 1", completed.stdout)


if __name__ == "__main__":
    unittest.main()
