# app.py
from datetime import datetime, timedelta
from flask import Flask, render_template, redirect, url_for
from services.email_service import fetch_support_emails    # step 1: IMAP fetch function
from services.nlp_service import analyze_email
from services.response_service import generate_response
from utils.db import init_db, upsert_emails, fetch_emails

app = Flask(__name__)
init_db()


def ingest_latest():
    """
    Fetch recent support emails via IMAP (or dataset fallback), analyze, generate reply,
    sort by priority (urgent first) and upsert into DB.
    """
    raw_emails = fetch_support_emails(max_count=100)  # returns list of dicts with message_id/sender/subject/body/received_at
    processed = []

    for e in raw_emails:
        # ensure required keys exist
        message_id = e.get("message_id") or f"{e.get('sender')}_{e.get('subject')}_{hash(e.get('body',''))}"
        e_norm = {
            "message_id": message_id,
            "sender": e.get("sender", ""),
            "subject": e.get("subject", "") or "",
            "body": e.get("body", "") or "",
            "received_at": e.get("received_at") or datetime.utcnow().isoformat()
        }

        analysis = analyze_email(e_norm)
        draft = generate_response(e_norm, analysis)

        rec = {
            "message_id": e_norm["message_id"],
            "sender": e_norm["sender"],
            "subject": e_norm["subject"],
            "body": e_norm["body"],
            "received_at": e_norm["received_at"],
            "priority": analysis.get("priority", "Not urgent"),
            "sentiment": analysis.get("sentiment", "Neutral"),
            "requirements": analysis.get("requirements", ""),
            "contacts": analysis.get("contacts", ""),
            "draft_reply": draft,
            "status": "pending"
        }
        processed.append(rec)

    # Priority queue: urgent first, then by newest received_at
    def sort_key(r):
        pri = 0 if r.get("priority") == "Urgent" else 1
        # received_at might be ISO string — attempt to parse, fallback to 0
        try:
            ts = datetime.fromisoformat(r.get("received_at"))
            ts_key = -ts.timestamp()
        except Exception:
            ts_key = 0
        return (pri, ts_key)

    processed.sort(key=sort_key)

    if processed:
        upsert_emails(processed)


@app.route("/")
def dashboard():
    # Ingest before showing (idempotent due to DB upsert by message_id)
    ingest_latest()

    emails = fetch_emails(order_by_priority=True)

    # Stats
    now = datetime.utcnow()
    last_24h_cutoff = now - timedelta(hours=24)

    def parse_iso(s):
        try:
            return datetime.fromisoformat(s)
        except Exception:
            return None

    total = len(emails)
    urgent = sum(1 for e in emails if e.get("priority") == "Urgent")
    positive = sum(1 for e in emails if e.get("sentiment") == "Positive")
    negative = sum(1 for e in emails if e.get("sentiment") == "Negative")
    neutral = sum(1 for e in emails if e.get("sentiment") == "Neutral")
    last_24 = sum(1 for e in emails if (parse_iso(e.get("received_at")) or now) >= last_24h_cutoff)
    resolved = sum(1 for e in emails if e.get("status") == "resolved")
    pending = total - resolved

    stats = {
        "total": total,
        "urgent": urgent,
        "positive": positive,
        "negative": negative,
        "neutral": neutral,
        "last_24h": last_24,
        "resolved": resolved,
        "pending": pending,
    }

    return render_template("dashboard.html", emails=emails, stats=stats)


if __name__ == "__main__":
    app.run(debug=True)
