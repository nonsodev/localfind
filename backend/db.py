"""
db.py — SQLite metadata store for tracking indexed files.
Stores file path, content hash, and last indexed time so we only
re-index files whose content has actually changed.
"""
import sqlite3
import hashlib
from pathlib import Path
from config import DB_PATH

SQLITE_TIMEOUT_SECONDS = 30.0
SQLITE_BUSY_TIMEOUT_MS = 30_000


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=SQLITE_TIMEOUT_SECONDS)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute(f"PRAGMA busy_timeout = {SQLITE_BUSY_TIMEOUT_MS}")
    return conn


def init_db():
    """Create tables if they don't exist."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS folders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT UNIQUE NOT NULL,
                added_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS indexed_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                folder_id INTEGER NOT NULL,
                file_path TEXT UNIQUE NOT NULL,
                content_hash TEXT NOT NULL,
                indexed_at TEXT DEFAULT (datetime('now')),
                file_type TEXT NOT NULL,
                chunk_count INTEGER DEFAULT 0,
                FOREIGN KEY (folder_id) REFERENCES folders(id) ON DELETE CASCADE
            )
        """)
        conn.commit()


def clear_all_metadata():
    """Clear tracked folders and indexed file metadata without deleting the DB file."""
    with get_connection() as conn:
        conn.execute("DELETE FROM indexed_files")
        conn.execute("DELETE FROM folders")
        conn.commit()


# ── Folders ────────────────────────────────────────────────────────────────

def add_folder(path: str) -> dict:
    with get_connection() as conn:
        try:
            conn.execute("INSERT INTO folders (path) VALUES (?)", (path,))
            conn.commit()
            row = conn.execute("SELECT * FROM folders WHERE path = ?", (path,)).fetchone()
            return dict(row)
        except sqlite3.IntegrityError:
            row = conn.execute("SELECT * FROM folders WHERE path = ?", (path,)).fetchone()
            return dict(row)


def remove_folder(folder_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM folders WHERE id = ?", (folder_id,))
        conn.commit()


def get_folders() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM folders ORDER BY added_at DESC").fetchall()
        return [dict(r) for r in rows]


def get_folder_by_id(folder_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM folders WHERE id = ?", (folder_id,)).fetchone()
        return dict(row) if row else None


# ── Indexed files ──────────────────────────────────────────────────────────

def get_file_hash(file_path: str) -> str:
    """SHA256 of file content."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def upsert_indexed_file(folder_id: int, file_path: str, content_hash: str,
                         file_type: str, chunk_count: int):
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO indexed_files (folder_id, file_path, content_hash, file_type, chunk_count)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(file_path) DO UPDATE SET
                content_hash = excluded.content_hash,
                indexed_at = datetime('now'),
                chunk_count = excluded.chunk_count
        """, (folder_id, file_path, content_hash, file_type, chunk_count))
        conn.commit()


def get_indexed_file(file_path: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM indexed_files WHERE file_path = ?", (file_path,)
        ).fetchone()
        return dict(row) if row else None


def get_folder_files(folder_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM indexed_files WHERE folder_id = ?", (folder_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def delete_indexed_file(file_path: str):
    with get_connection() as conn:
        conn.execute("DELETE FROM indexed_files WHERE file_path = ?", (file_path,))
        conn.commit()


def get_stats() -> dict:
    with get_connection() as conn:
        total_folders = conn.execute("SELECT COUNT(*) FROM folders").fetchone()[0]
        total_files = conn.execute("SELECT COUNT(*) FROM indexed_files").fetchone()[0]
        total_chunks = conn.execute("SELECT SUM(chunk_count) FROM indexed_files").fetchone()[0] or 0
        last_sync = conn.execute(
            "SELECT MAX(indexed_at) FROM indexed_files"
        ).fetchone()[0]
        return {
            "total_folders": total_folders,
            "total_files": total_files,
            "total_chunks": total_chunks,
            "last_sync": last_sync,
        }
