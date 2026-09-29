"""SQLite connection manager."""
from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


class Database:
    """Wraps a SQLite connection and makes sure the schema exists.

    Use ":memory:" as the path for a throwaway database (handy for tests).
    """

    def __init__(self, path: str = "thon.db"):
        self.path = path
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row          # rows behave like dicts
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._create_schema()

    def _create_schema(self) -> None:
        self.conn.executescript(SCHEMA_PATH.read_text())
        self.conn.commit()

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        cur = self.conn.execute(sql, params)
        self.conn.commit()
        return cur

    def query(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        return self.conn.execute(sql, params).fetchall()

    def close(self) -> None:
        self.conn.close()

    # Allow: with Database("thon.db") as db: ...
    def __enter__(self) -> "Database":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
