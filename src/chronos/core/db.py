import os
import sqlite3
import json
from datetime import datetime

class DB:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            # Enable foreign keys
            conn.execute("PRAGMA foreign_keys = ON;")

            # Checkpoints Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS checkpoints (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    message TEXT,
                    git_commit TEXT,
                    git_branch TEXT,
                    git_status TEXT,
                    snapshot_path TEXT
                );
            """)

            # Environment Variables Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS environment_variables (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    checkpoint_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    value TEXT NOT NULL,
                    FOREIGN KEY (checkpoint_id) REFERENCES checkpoints (id) ON DELETE CASCADE
                );
            """)

            # Packages Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS packages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    checkpoint_id TEXT NOT NULL,
                    manager TEXT NOT NULL, -- e.g., pip, npm, cargo, go
                    name TEXT NOT NULL,
                    version TEXT NOT NULL,
                    FOREIGN KEY (checkpoint_id) REFERENCES checkpoints (id) ON DELETE CASCADE
                );
            """)

            # Files Table (Tracks file metadata at checkpoint)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tracked_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    checkpoint_id TEXT NOT NULL,
                    filepath TEXT NOT NULL,
                    sha256 TEXT NOT NULL,
                    size INTEGER NOT NULL,
                    modified_time REAL NOT NULL,
                    FOREIGN KEY (checkpoint_id) REFERENCES checkpoints (id) ON DELETE CASCADE
                );
            """)

            conn.commit()

    def create_checkpoint(self, checkpoint_id: str, message: str, git_commit: str = None,
                          git_branch: str = None, git_status: str = None, snapshot_path: str = None):
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO checkpoints (id, timestamp, message, git_commit, git_branch, git_status, snapshot_path)
                VALUES (?, ?, ?, ?, ?, ?, ?);
            """, (checkpoint_id, datetime.now().isoformat(), message, git_commit, git_branch, git_status, snapshot_path))
            conn.commit()

    def add_environment_variables(self, checkpoint_id: str, env_vars: dict):
        with self._get_conn() as conn:
            conn.executemany("""
                INSERT INTO environment_variables (checkpoint_id, name, value)
                VALUES (?, ?, ?);
            """, [(checkpoint_id, k, v) for k, v in env_vars.items()])
            conn.commit()

    def add_packages(self, checkpoint_id: str, packages: list):
        # packages list should be elements of (manager, name, version)
        with self._get_conn() as conn:
            conn.executemany("""
                INSERT INTO packages (checkpoint_id, manager, name, version)
                VALUES (?, ?, ?, ?);
            """, [(checkpoint_id, mgr, name, ver) for mgr, name, ver in packages])
            conn.commit()

    def add_tracked_files(self, checkpoint_id: str, tracked_files: list):
        # tracked_files is a list of (filepath, sha256, size, modified_time)
        with self._get_conn() as conn:
            conn.executemany("""
                INSERT INTO tracked_files (checkpoint_id, filepath, sha256, size, modified_time)
                VALUES (?, ?, ?, ?, ?);
            """, [(checkpoint_id, filepath, sha256, size, mtime) for filepath, sha256, size, mtime in tracked_files])
            conn.commit()

    def get_latest_checkpoint(self):
        with self._get_conn() as conn:
            cursor = conn.execute("SELECT * FROM checkpoints ORDER BY timestamp DESC LIMIT 1;")
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_checkpoint(self, checkpoint_id: str):
        with self._get_conn() as conn:
            cursor = conn.execute("SELECT * FROM checkpoints WHERE id = ? OR id LIKE ?;", (checkpoint_id, f"{checkpoint_id}%"))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_checkpoints(self):
        with self._get_conn() as conn:
            cursor = conn.execute("SELECT * FROM checkpoints ORDER BY timestamp DESC;")
            return [dict(row) for row in cursor.fetchall()]

    def get_environment_variables(self, checkpoint_id: str):
        with self._get_conn() as conn:
            cursor = conn.execute("SELECT name, value FROM environment_variables WHERE checkpoint_id = ?;", (checkpoint_id,))
            return {row["name"]: row["value"] for row in cursor.fetchall()}

    def get_packages(self, checkpoint_id: str):
        with self._get_conn() as conn:
            cursor = conn.execute("SELECT manager, name, version FROM packages WHERE checkpoint_id = ?;", (checkpoint_id,))
            return [dict(row) for row in cursor.fetchall()]

    def get_tracked_files(self, checkpoint_id: str):
        with self._get_conn() as conn:
            cursor = conn.execute("SELECT filepath, sha256, size, modified_time FROM tracked_files WHERE checkpoint_id = ?;", (checkpoint_id,))
            return [dict(row) for row in cursor.fetchall()]

    def delete_checkpoint(self, checkpoint_id: str):
        with self._get_conn() as conn:
            conn.execute("DELETE FROM checkpoints WHERE id = ?;", (checkpoint_id,))
            conn.commit()
