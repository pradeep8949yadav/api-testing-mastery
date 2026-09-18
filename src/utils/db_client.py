from __future__ import annotations
import sqlite3
import os
from typing import Any, Optional

DB_FILE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "atlassian_test.db"))


class DatabaseClient:
    """
    Direct SQL Database Client for Automated Persistence Testing & Invariant Assertions.
    """

    def __init__(self, db_path: str = DB_FILE_PATH):
        self.db_path = db_path
        self._init_schema()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        """Ensure test tables exist with proper constraints and audit fields."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sql_projects (
                    id TEXT PRIMARY KEY,
                    key TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    lead_email TEXT NOT NULL,
                    description TEXT,
                    tenant_id TEXT NOT NULL,
                    version INTEGER DEFAULT 1,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    deleted_at TIMESTAMP NULL
                );
            """)
            conn.commit()

    def get_project_by_id(self, project_id: str) -> Optional[dict[str, Any]]:
        """Fetch raw row state directly from database table."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sql_projects WHERE id = ?", (project_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_project_by_key(self, key: str) -> Optional[dict[str, Any]]:
        """Fetch project by unique key directly from database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sql_projects WHERE key = ?", (key.upper(),))
            row = cursor.fetchone()
            return dict(row) if row else None

    def count_projects_by_key(self, key: str) -> int:
        """Count how many rows exist with a specific key (useful for ghost-write negative tests)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM sql_projects WHERE key = ?", (key.upper(),))
            return int(cursor.fetchone()[0])

    def reset_database(self) -> None:
        """Truncate table to ensure test state isolation."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM sql_projects;")
            conn.commit()


# Singleton instance for tests
db_client = DatabaseClient()
