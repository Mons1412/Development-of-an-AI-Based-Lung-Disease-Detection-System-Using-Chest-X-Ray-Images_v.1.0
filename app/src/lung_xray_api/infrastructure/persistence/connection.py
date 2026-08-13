"""Short-lived SQLite connections with consistent safety pragmas."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import sqlite3
from typing import Iterator

from lung_xray_api.core.exceptions import DatabaseBusyError, PersistenceError


class SQLiteConnectionFactory:
    """Own local SQLite connection setup without sharing connections across requests."""

    def __init__(self, database_path: Path, busy_timeout_ms: int = 5_000) -> None:
        if busy_timeout_ms <= 0:
            raise ValueError("busy_timeout_ms phai lon hon 0")
        self.database_path = database_path.resolve()
        self.busy_timeout_ms = busy_timeout_ms

    def ensure_parent_directory(self) -> None:
        try:
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            raise PersistenceError("Could not create SQLite history directory") from error

    def connect(self) -> sqlite3.Connection:
        self.ensure_parent_directory()
        try:
            connection = sqlite3.connect(
                self.database_path,
                timeout=self.busy_timeout_ms / 1000,
                isolation_level=None,
            )
        except sqlite3.Error as error:
            raise self._translate_error(error) from error

        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute(f"PRAGMA busy_timeout = {self.busy_timeout_ms}")
        except sqlite3.Error as error:
            connection.close()
            raise self._translate_error(error) from error
        return connection

    @contextmanager
    def read_connection(self) -> Iterator[sqlite3.Connection]:
        connection = self.connect()
        try:
            yield connection
        except sqlite3.Error as error:
            raise self._translate_error(error) from error
        finally:
            connection.close()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        connection = self.connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except sqlite3.Error as error:
            connection.rollback()
            raise self._translate_error(error) from error
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _translate_error(error: sqlite3.Error) -> PersistenceError:
        message = str(error).lower()
        if "locked" in message or "busy" in message:
            return DatabaseBusyError("SQLite history database is busy")
        return PersistenceError("SQLite history database operation failed")
