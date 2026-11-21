"""
db.py - Local SQLite storage for Doctor AI.

Stores:
  * conversations  (one chat = one conversation)
  * messages       (every user / assistant message, plus attached file info)
  * profile        (one patient profile: age, allergies, conditions ...)

The database file is created automatically at data/doctor_ai.db.
It is ignored by git (see .gitignore: *.db), so patient data is never uploaded.
"""

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("DOCTOR_AI_DB") or os.path.join(BASE_DIR, "data", "doctor_ai.db")

MAX_ATTACHMENT_TEXT = 6000  # characters of a report kept for later questions


@contextmanager
def _connect():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def init_db():
    """Create the tables if they do not exist yet."""
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT NOT NULL,
                kind        TEXT NOT NULL DEFAULT 'chat',
                created_at  TEXT NOT NULL,
                updated_at  TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS messages (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id  INTEGER NOT NULL
                                 REFERENCES conversations(id) ON DELETE CASCADE,
                role             TEXT NOT NULL,
                content          TEXT NOT NULL,
                attachment_name  TEXT,
                attachment_text  TEXT,
                created_at       TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_messages_conv
                ON messages(conversation_id, id);
            CREATE TABLE IF NOT EXISTS profile (
                id           INTEGER PRIMARY KEY CHECK (id = 1),
                name         TEXT, age TEXT, sex TEXT,
                conditions   TEXT, allergies TEXT, medications TEXT, notes TEXT
            );
            """
        )


# ---------------- conversations ----------------

def create_conversation(title="New chat", kind="chat"):
    now = _now()
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO conversations (title, kind, created_at, updated_at) "
            "VALUES (?, ?, ?, ?)",
            (title[:80], kind, now, now),
        )
        return cur.lastrowid


def list_conversations(limit=100):
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM conversations ORDER BY updated_at DESC, id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_conversation(conv_id):
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM conversations WHERE id = ?", (conv_id,)
        ).fetchone()
    return dict(row) if row else None


def rename_conversation(conv_id, title):
    with _connect() as conn:
        conn.execute(
            "UPDATE conversations SET title = ? WHERE id = ?", (title[:80], conv_id)
        )


def delete_conversation(conv_id):
    with _connect() as conn:
        conn.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))


def delete_all():
    with _connect() as conn:
        conn.execute("DELETE FROM conversations")


# ---------------- messages ----------------

def add_message(conv_id, role, content, attachment_name=None, attachment_text=None):
    if attachment_text:
        attachment_text = attachment_text[:MAX_ATTACHMENT_TEXT]
    now = _now()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO messages (conversation_id, role, content, attachment_name, "
            "attachment_text, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (conv_id, role, content, attachment_name, attachment_text, now),
        )
        conn.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?", (now, conv_id)
        )


def get_messages(conv_id):
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM messages WHERE conversation_id = ? ORDER BY id", (conv_id,)
        ).fetchall()
    return [dict(r) for r in rows]


def search_messages(query, limit=30):
    """Simple keyword search across all saved chats."""
    like = f"%{query.strip()}%"
    with _connect() as conn:
        rows = conn.execute(
            "SELECT m.conversation_id, c.title, m.role, m.content, m.created_at "
            "FROM messages m JOIN conversations c ON c.id = m.conversation_id "
            "WHERE m.content LIKE ? ORDER BY m.id DESC LIMIT ?",
            (like, limit),
        ).fetchall()
    return [dict(r) for r in rows]


# ---------------- patient profile ----------------

PROFILE_FIELDS = ["name", "age", "sex", "conditions", "allergies", "medications", "notes"]


def get_profile():
    with _connect() as conn:
        row = conn.execute("SELECT * FROM profile WHERE id = 1").fetchone()
    data = dict(row) if row else {}
    return {f: (data.get(f) or "") for f in PROFILE_FIELDS}


def save_profile(values):
    clean = {f: str(values.get(f, "")).strip() for f in PROFILE_FIELDS}
    with _connect() as conn:
        conn.execute(
            "INSERT INTO profile (id, name, age, sex, conditions, allergies, "
            "medications, notes) VALUES (1, :name, :age, :sex, :conditions, "
            ":allergies, :medications, :notes) "
            "ON CONFLICT(id) DO UPDATE SET name=:name, age=:age, sex=:sex, "
            "conditions=:conditions, allergies=:allergies, "
            "medications=:medications, notes=:notes",
            clean,
        )
