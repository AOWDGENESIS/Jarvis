"""
core/db.py â€” JARVIS OMNI v7.6 OMEGA
I3: Aufgaben & Erinnerungen (tasks Tabelle)
I5: GesprÃ¤chsprotokoll Ã¼ber Sessions hinweg (conversations Tabelle)
Thread-sicher via threading.Lock + WAL-Modus.
"""
import sqlite3
import threading
import logging
import os
from datetime import datetime, timedelta
from typing import Optional

log = logging.getLogger("jarvis.db")

# DB liegt im data/-Ordner neben main.py
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH   = os.path.join(_BASE_DIR, "data", "jarvis.db")

_lock = threading.Lock()


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")   # Thread-sicher
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Erstellt alle Tabellen falls nicht vorhanden."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with _lock:
        conn = _connect()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS conversations (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  TEXT    NOT NULL,
                timestamp   TEXT    NOT NULL,
                role        TEXT    NOT NULL CHECK(role IN ('Felix','Jarvis','system')),
                text        TEXT    NOT NULL,
                mode        TEXT    DEFAULT 'SATELLITE'
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at   TEXT    NOT NULL,
                reminder_dt  TEXT,           -- NULL = keine Erinnerung, ISO-8601
                text         TEXT    NOT NULL,
                done         INTEGER NOT NULL DEFAULT 0,
                notified     INTEGER NOT NULL DEFAULT 0
            );

            CREATE INDEX IF NOT EXISTS idx_conv_session ON conversations(session_id);
            CREATE INDEX IF NOT EXISTS idx_task_reminder ON tasks(reminder_dt, done, notified);
        """)
        conn.commit()
        conn.close()
    log.info(f"[DB] Initialisiert: {DB_PATH}")


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# I5: GESPRÃ„CHSPROTOKOLL
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
def save_message(session_id: str, role: str, text: str, mode: str = "SATELLITE"):
    """Speichert eine Nachricht dauerhaft."""
    with _lock:
        conn = _connect()
        conn.execute(
            "INSERT INTO conversations (session_id, timestamp, role, text, mode) VALUES (?,?,?,?,?)",
            (session_id, datetime.now().isoformat(), role, text, mode)
        )
        conn.commit()
        conn.close()


def load_recent_messages(limit: int = 20) -> list[dict]:
    """LÃ¤dt die letzten N Nachrichten (fÃ¼r Kontext-Wiederherstellung)."""
    with _lock:
        conn = _connect()
        rows = conn.execute(
            "SELECT role, text, mode, timestamp FROM conversations ORDER BY id DESC LIMIT ?",
            (limit,)
        ).fetchall()
        conn.close()
    return [dict(r) for r in reversed(rows)]


def get_conversation_stats() -> dict:
    with _lock:
        conn = _connect()
        total = conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
        days  = conn.execute(
            "SELECT COUNT(DISTINCT DATE(timestamp)) FROM conversations"
        ).fetchone()[0]
        conn.close()
    return {"total_messages": total, "active_days": days}


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# I3: AUFGABEN & ERINNERUNGEN
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
def add_task(text: str, reminder_dt: Optional[datetime] = None) -> int:
    """FÃ¼gt eine neue Aufgabe hinzu. Gibt die neue ID zurÃ¼ck."""
    with _lock:
        conn = _connect()
        cur = conn.execute(
            "INSERT INTO tasks (created_at, reminder_dt, text) VALUES (?,?,?)",
            (
                datetime.now().isoformat(),
                reminder_dt.isoformat() if reminder_dt else None,
                text,
            )
        )
        task_id = cur.lastrowid
        conn.commit()
        conn.close()
    log.info(f"[DB] Aufgabe #{task_id} gespeichert: '{text[:50]}' | Erinnerung: {reminder_dt}")
    return task_id


def get_open_tasks() -> list[dict]:
    """Alle offenen Aufgaben."""
    with _lock:
        conn = _connect()
        rows = conn.execute(
            "SELECT id, text, reminder_dt, created_at FROM tasks WHERE done=0 ORDER BY id DESC"
        ).fetchall()
        conn.close()
    return [dict(r) for r in rows]


def complete_task(task_id: int):
    with _lock:
        conn = _connect()
        conn.execute("UPDATE tasks SET done=1 WHERE id=?", (task_id,))
        conn.commit()
        conn.close()
    log.info(f"[DB] Aufgabe #{task_id} als erledigt markiert.")


def get_due_reminders() -> list[dict]:
    """Erinnerungen die jetzt fÃ¤llig sind (noch nicht benachrichtigt)."""
    now = datetime.now().isoformat()
    with _lock:
        conn = _connect()
        rows = conn.execute(
            """SELECT id, text, reminder_dt FROM tasks
               WHERE done=0 AND notified=0
               AND reminder_dt IS NOT NULL AND reminder_dt <= ?""",
            (now,)
        ).fetchall()
        conn.close()
    return [dict(r) for r in rows]


def mark_notified(task_id: int):
    with _lock:
        conn = _connect()
        conn.execute("UPDATE tasks SET notified=1 WHERE id=?", (task_id,))
        conn.commit()
        conn.close()


def delete_task(task_id: int):
    with _lock:
        conn = _connect()
        conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
        conn.commit()
        conn.close()


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# EINFACHER DATUM-PARSER (Deutsch)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
def parse_reminder_dt(text: str) -> Optional[datetime]:
    """
    Versteht natÃ¼rliche deutsche Zeitangaben:
    'morgen', 'Ã¼bermorgen', 'in X minuten/stunden',
    'heute um HH:MM', 'morgen um HH:MM', 'in X tagen'
    """
    import re
    text = text.lower().strip()
    now  = datetime.now()

    # "in X minuten"
    m = re.search(r'in (\d+)\s*min', text)
    if m: return now + timedelta(minutes=int(m.group(1)))

    # "in X stunden"
    m = re.search(r'in (\d+)\s*stund', text)
    if m: return now + timedelta(hours=int(m.group(1)))

    # "in X tagen"
    m = re.search(r'in (\d+)\s*tag', text)
    if m: return now + timedelta(days=int(m.group(1)))

    # "Ã¼bermorgen um HH:MM" oder "Ã¼bermorgen"
    if 'Ã¼bermorgen' in text or 'uebermorgen' in text:
        base = now + timedelta(days=2)
        m = re.search(r'(\d{1,2})[:\.](\d{2})', text)
        if m: return base.replace(hour=int(m.group(1)), minute=int(m.group(2)), second=0, microsecond=0)
        return base.replace(hour=9, minute=0, second=0, microsecond=0)

    # "morgen um HH:MM" oder "morgen"
    if 'morgen' in text:
        base = now + timedelta(days=1)
        m = re.search(r'(\d{1,2})[:\.](\d{2})', text)
        if m: return base.replace(hour=int(m.group(1)), minute=int(m.group(2)), second=0, microsecond=0)
        return base.replace(hour=9, minute=0, second=0, microsecond=0)

    # "heute um HH:MM"
    if 'heute' in text:
        m = re.search(r'(\d{1,2})[:\.](\d{2})', text)
        if m: return now.replace(hour=int(m.group(1)), minute=int(m.group(2)), second=0, microsecond=0)

    # Nur Uhrzeit z.B. "um 15:30"
    m = re.search(r'um\s+(\d{1,2})[:\.](\d{2})', text)
    if m:
        t = now.replace(hour=int(m.group(1)), minute=int(m.group(2)), second=0, microsecond=0)
        if t <= now: t += timedelta(days=1)  # Falls Zeit schon vorbei â†’ morgen
        return t

    return None  # Keine Zeitangabe erkannt â†’ einfache Aufgabe ohne Erinnerung