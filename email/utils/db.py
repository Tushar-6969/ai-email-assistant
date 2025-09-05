# utils/db.py
import sqlite3
from pathlib import Path

DB_NAME = "emails.db"


def _connect():
    Path(DB_NAME).touch(exist_ok=True)
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _connect()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id TEXT UNIQUE,
            sender TEXT,
            subject TEXT,
            body TEXT,
            received_at TEXT,
            priority TEXT,
            sentiment TEXT,
            requirements TEXT,
            contacts TEXT,
            draft_reply TEXT,
            status TEXT DEFAULT 'pending'
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_received ON emails(received_at DESC)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_priority ON emails(priority)")
    conn.commit()
    conn.close()


def upsert_emails(emails):
    """
    Upsert email records by message_id. Expects a list of dicts with keys:
    message_id, sender, subject, body, received_at, priority, sentiment, requirements, contacts, draft_reply, status
    """
    if not emails:
        return

    conn = _connect()
    cur = conn.cursor()

    sql = """
    INSERT INTO emails
      (message_id, sender, subject, body, received_at, priority, sentiment, requirements, contacts, draft_reply, status)
    VALUES
      (:message_id, :sender, :subject, :body, :received_at, :priority, :sentiment, :requirements, :contacts, :draft_reply, :status)
    ON CONFLICT(message_id) DO UPDATE SET
      sender=excluded.sender,
      subject=excluded.subject,
      body=excluded.body,
      received_at=excluded.received_at,
      priority=excluded.priority,
      sentiment=excluded.sentiment,
      requirements=excluded.requirements,
      contacts=excluded.contacts,
      draft_reply=excluded.draft_reply,
      status=excluded.status
    """
    cur.executemany(sql, emails)
    conn.commit()
    conn.close()


def fetch_emails(order_by_priority=True, limit=200):
    """
    Returns list of dicts ordered (urgent first then newest) by default.
    """
    conn = _connect()
    cur = conn.cursor()

    if order_by_priority:
        query = """
            SELECT id, message_id, sender, subject, body, received_at,
                   priority, sentiment, requirements, contacts, draft_reply, status
            FROM emails
            ORDER BY CASE WHEN priority='Urgent' THEN 0 ELSE 1 END,
                     datetime(received_at) DESC
            LIMIT ?
        """
        cur.execute(query, (limit,))
    else:
        cur.execute("""
            SELECT id, message_id, sender, subject, body, received_at,
                   priority, sentiment, requirements, contacts, draft_reply, status
            FROM emails
            ORDER BY datetime(received_at) DESC
            LIMIT ?
        """, (limit,))

    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows
