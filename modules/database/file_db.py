from __future__ import annotations

import json
import sqlite3
from typing import Any, Dict, Optional

from app.config import DB_PATH


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_file_db() -> None:
    conn = _connect()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS indexed_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_unique_id TEXT UNIQUE,
            file_id TEXT,
            storage_message_id INTEGER,
            file_name TEXT,
            file_size INTEGER,
            duration INTEGER,
            user_id INTEGER,
            user_title TEXT,
            caption TEXT,
            extension TEXT,
            file_type TEXT,
            category TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()


def save_indexed_file_db(
    file_unique_id: str,
    file_id: str,
    storage_message_id: int,
    file_name: str,
    file_size: int,
    duration: int,
    user_id: int,
    user_title: str,
    caption: str,
    extension: str,
    file_type: str,
    category: str = "book",
) -> None:
    init_file_db()
    conn = _connect()
    conn.execute(
        """
        INSERT INTO indexed_files (
            file_unique_id, file_id, storage_message_id, file_name, file_size,
            duration, user_id, user_title, caption, extension, file_type, category
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(file_unique_id) DO UPDATE SET
            file_id = excluded.file_id,
            storage_message_id = excluded.storage_message_id,
            file_name = excluded.file_name,
            file_size = excluded.file_size,
            duration = excluded.duration,
            user_id = excluded.user_id,
            user_title = excluded.user_title,
            caption = excluded.caption,
            extension = excluded.extension,
            file_type = excluded.file_type,
            category = excluded.category
        """,
        (
            file_unique_id,
            file_id,
            storage_message_id,
            file_name,
            file_size,
            duration,
            user_id,
            user_title,
            caption,
            extension,
            file_type,
            category,
        ),
    )
    conn.commit()
    conn.close()


def get_file_by_unique_id_db(file_unique_id: str) -> Optional[Dict[str, Any]]:
    init_file_db()
    conn = _connect()
    row = conn.execute(
        "SELECT * FROM indexed_files WHERE file_unique_id=?",
        (file_unique_id,),
    ).fetchone()
    conn.close()
    if row is None:
        return None
    return dict(row)


def get_all_indexed_files() -> list[dict]:
    init_file_db()
    conn = _connect()
    rows = conn.execute("SELECT * FROM indexed_files ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(row) for row in rows]


__all__ = [
    "init_file_db",
    "save_indexed_file_db",
    "get_file_by_unique_id_db",
    "get_all_indexed_files",
]
