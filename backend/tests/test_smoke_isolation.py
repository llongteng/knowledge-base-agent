import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class SmokeIsolationTests(unittest.TestCase):
    def test_smoke_test_uses_temporary_database(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "real_demo.db"
            sqlite3.connect(db_path).execute(
                "create table marker (id integer primary key, name text)"
            ).connection.close()

            env = {
                **os.environ,
                "DATABASE_URL": f"sqlite:///{db_path}",
            }
            result = subprocess.run(
                [sys.executable, "smoke_test.py"],
                cwd=Path(__file__).resolve().parents[1],
                env=env,
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            tables = sqlite3.connect(db_path).execute(
                "select name from sqlite_master where type='table' order by name"
            ).fetchall()
            self.assertEqual(tables, [("marker",)])
