import os
import subprocess
import sys
import tempfile
import unittest

from mini_rdbms.integration.database import Database
from mini_rdbms.integration.session import Session
from mini_rdbms.storage.wal import COMMIT, PAGE_IMAGE


class WalCrashRecoveryTest(unittest.TestCase):
    def test_committed_wal_image_is_replayed_when_database_replace_is_interrupted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "database.db")
            source = Database(path)
            session = Session(source)
            session.execute("CREATE TABLE t (id INT PRIMARY KEY)")
            session.execute("INSERT INTO t VALUES (7)")
            source.persist()
            with open(path, "rb") as file:
                image = file.read()
            source.wal.append(99, PAGE_IMAGE, image)
            source.wal.append(99, COMMIT, b"")
            os.remove(path)

            recovered = Database(path)
            self.assertEqual(Session(recovered).execute("SELECT * FROM t").unwrap(), [{"id": 7}])

    def test_uncommitted_wal_image_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "database.db")
            database = Database(path)
            session = Session(database)
            session.execute("CREATE TABLE t (id INT PRIMARY KEY)")
            database.persist()
            with open(path, "rb") as file:
                image = file.read()
            database.wal.append(100, PAGE_IMAGE, image + b"uncommitted")
            reopened = Database(path)
            self.assertEqual(Session(reopened).execute("SELECT * FROM t").unwrap(), [])

    def test_subprocess_exit_after_commit_record_is_recovered(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "database.db")
            database = Database(path)
            session = Session(database)
            session.execute("CREATE TABLE t (id INT PRIMARY KEY)")
            session.execute("INSERT INTO t VALUES (9)")
            database.persist()
            with open(path, "rb") as file:
                image = file.read()
            script = (
                "import sys; sys.path.insert(0, 'src'); "
                "from mini_rdbms.storage.wal import WriteAheadLog, PAGE_IMAGE, COMMIT; "
                "wal=WriteAheadLog(sys.argv[1]); wal.append(55, PAGE_IMAGE, open(sys.argv[2], 'rb').read()); "
                "wal.append(55, COMMIT, b''); import os; os._exit(7)"
            )
            image_path = os.path.join(directory, "image")
            with open(image_path, "wb") as file:
                file.write(image)
            completed = subprocess.run(
                [sys.executable, "-c", script, f"{path}.wal", image_path],
                capture_output=True,
            )
            self.assertEqual(completed.returncode, 7)
            os.remove(path)
            recovered = Database(path)
            self.assertEqual(Session(recovered).execute("SELECT * FROM t").unwrap(), [{"id": 9}])


if __name__ == "__main__":
    unittest.main()
