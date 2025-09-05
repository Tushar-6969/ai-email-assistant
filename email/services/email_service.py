import imaplib
import email
from email.header import decode_header
import os

IMAP_SERVER = "imap.gmail.com"
IMAP_PORT = 993
EMAIL_USER = os.getenv("EMAIL_USER")  # your Gmail address
EMAIL_PASS = os.getenv("EMAIL_PASS")  # App Password

FILTER_KEYWORDS = ["support", "query", "request", "help"]

def load_emails_from_gmail(limit=20):
    """
    Fetch emails from Gmail via IMAP.
    Returns: list of dicts with sender, subject, body, date
    """
    mails = []
    try:
        conn = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        conn.login(EMAIL_USER, EMAIL_PASS)
        conn.select("inbox")

        # Search all emails
        status, messages = conn.search(None, "ALL")
        email_ids = messages[0].split()[-limit:]  # last N emails

        for eid in reversed(email_ids):
            _, msg_data = conn.fetch(eid, "(RFC822)")
            msg = email.message_from_bytes(msg_data[0][1])

            subject, encoding = decode_header(msg["Subject"])[0]
            if isinstance(subject, bytes):
                subject = subject.decode(encoding or "utf-8", errors="ignore")

            sender = msg.get("From", "")
            date = msg.get("Date", "")

            # Get email body
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                        break
            else:
                body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")

            # Apply keyword filter
            if any(kw.lower() in subject.lower() for kw in FILTER_KEYWORDS):
                mails.append({
                    "sender": sender,
                    "subject": subject,
                    "body": body,
                    "date": date
                })

        conn.logout()
    except Exception as e:
        print("Email fetch error:", e)

    return mails
