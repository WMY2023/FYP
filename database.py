import os
import sqlite3
import uuid
from datetime import datetime, timezone
from contextlib import contextmanager
from pathlib import Path
from typing import Any


DEFAULT_DATABASE_PATH = "data/medical_assistant.db"


@contextmanager
def get_connection():
    database_path = Path(os.getenv("DATABASE_PATH", DEFAULT_DATABASE_PATH))
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_database() -> None:
    with get_connection() as connection:
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS patient_reports (
                id TEXT PRIMARY KEY, patient_id TEXT NOT NULL, title TEXT NOT NULL,
                report_text TEXT NOT NULL, file_name TEXT, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS communication_records (
                id TEXT PRIMARY KEY, patient_id TEXT NOT NULL, report_id TEXT,
                sender_role TEXT NOT NULL, message_text TEXT NOT NULL,
                tone TEXT, complexity TEXT, created_at TEXT NOT NULL,
                FOREIGN KEY(report_id) REFERENCES patient_reports(id)
            );
            CREATE TABLE IF NOT EXISTS reference_chunks (
                id TEXT PRIMARY KEY, document_title TEXT NOT NULL, publisher TEXT,
                source TEXT, chunk_number INTEGER NOT NULL, chunk_text TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
        """)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())


def save_patient_report(patient_id: str, title: str, report_text: str,
                        file_name: str | None = None) -> str:
    report_id = _new_id()
    with get_connection() as connection:
        connection.execute(
            "INSERT INTO patient_reports VALUES (?, ?, ?, ?, ?, ?)",
            (report_id, patient_id.strip(), title.strip(), report_text.strip(),
             file_name, _now()),
        )
    return report_id


def save_communication(patient_id: str, report_id: str | None, sender_role: str,
                       message_text: str, tone: str | None = None,
                       complexity: str | None = None) -> str:
    message_id = _new_id()
    with get_connection() as connection:
        connection.execute(
            "INSERT INTO communication_records VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (message_id, patient_id.strip(), report_id, sender_role,
             message_text.strip(), tone, complexity, _now()),
        )
    return message_id


def save_reference(title: str, publisher: str, source: str, text: str,
                   chunk_size: int = 900, overlap: int = 150) -> int:
    step = max(1, chunk_size - overlap)
    chunks: list[tuple[Any, ...]] = []
    for number, start in enumerate(range(0, len(text), step)):
        chunk = text[start:start + chunk_size].strip()
        if chunk:
            chunks.append((_new_id(), title.strip(), publisher.strip(), source.strip(),
                           number, chunk, _now()))
        if start + chunk_size >= len(text):
            break
    with get_connection() as connection:
        connection.executemany(
            "INSERT INTO reference_chunks VALUES (?, ?, ?, ?, ?, ?, ?)", chunks
        )
    return len(chunks)


def list_reports(patient_id: str | None = None) -> list[dict[str, Any]]:
    query = "SELECT * FROM patient_reports"
    parameters: tuple[str, ...] = ()
    if patient_id:
        query += " WHERE patient_id = ?"
        parameters = (patient_id.strip(),)
    query += " ORDER BY created_at DESC"
    with get_connection() as connection:
        return [dict(row) for row in connection.execute(query, parameters)]


def list_communications(patient_id: str, report_id: str | None = None) -> list[dict[str, Any]]:
    query = "SELECT * FROM communication_records WHERE patient_id = ?"
    parameters: list[str] = [patient_id]
    if report_id:
        query += " AND report_id = ?"
        parameters.append(report_id)
    query += " ORDER BY created_at ASC"
    with get_connection() as connection:
        return [dict(row) for row in connection.execute(query, parameters)]


def list_references() -> list[dict[str, Any]]:
    with get_connection() as connection:
        return [dict(row) for row in connection.execute(
            "SELECT * FROM reference_chunks ORDER BY created_at DESC, chunk_number"
        )]


def delete_reference(title: str, publisher: str, source: str) -> int:
    with get_connection() as connection:
        cursor = connection.execute(
            """DELETE FROM reference_chunks
               WHERE document_title = ? AND publisher = ? AND source = ?""",
            (title.strip(), publisher.strip(), source.strip()),
        )
        return cursor.rowcount


init_database()
