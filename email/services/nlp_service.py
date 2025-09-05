# services/nlp_service.py
import os
import re
import json

# ------- Heuristic wordlists -------
POS_WORDS = {"great", "thanks", "thank you", "appreciate", "love", "awesome", "good"}
NEG_WORDS = {"issue", "problem", "angry", "frustrated", "not working", "cannot", "error", "fail"}
URGENT_WORDS = {"urgent", "immediately", "asap", "critical", "cannot access", "down", "outage", "blocked"}

EMAIL_REGEX = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
PHONE_REGEX = r"(?:\+?\d[\s-]?)?(?:\(?\d{3}\)?[\s-]?)?\d{3}[\s-]?\d{4}"


# ------- Optional Gemini wrapper (robust to different client versions) -------
def _call_gemini(prompt: str, max_tokens: int = 512) -> str | None:
    """
    Attempt to call Gemini (google-generativeai). Returns text or None on failure.
    """
    try:
        import google.generativeai as genai
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

        # try a couple of likely client APIs (best-effort)
        if hasattr(genai, "generate_text"):
            resp = genai.generate_text(model="gemini-2.0-flash", prompt=prompt, max_output_tokens=max_tokens)
            # handle common shapes
            if isinstance(resp, dict):
                if "candidates" in resp and resp["candidates"]:
                    return resp["candidates"][0].get("content") or resp["candidates"][0].get("text")
                return str(resp)
            return getattr(resp, "text", str(resp))

        if hasattr(genai, "GenerativeModel"):
            model = genai.GenerativeModel("gemini-2.0-flash")
            out = model.generate_content(prompt)
            return getattr(out, "text", None) or str(out)

    except Exception as e:
        # print only in debug; fallback to heuristics
        print("Gemini call failed:", str(e))
        return None

    return None


# ------- Heuristic functions -------
def _sentiment(text: str) -> str:
    tl = (text or "").lower()
    pos = any(w in tl for w in POS_WORDS)
    neg = any(w in tl for w in NEG_WORDS)
    if pos and not neg:
        return "Positive"
    if neg and not pos:
        return "Negative"
    return "Neutral"


def _priority(text: str) -> str:
    tl = (text or "").lower()
    return "Urgent" if any(w in tl for w in URGENT_WORDS) else "Not urgent"


def _extract_contacts(text: str) -> str:
    emails = re.findall(EMAIL_REGEX, text or "")
    phones = re.findall(PHONE_REGEX, text or "")
    parts = []
    if emails:
        parts.append("Emails: " + ", ".join(sorted(set(emails))[:3]))
    if phones:
        parts.append("Phones: " + ", ".join(sorted(set(phones))[:3]))
    return " | ".join(parts)


def _extract_requirements(text: str) -> str:
    if not text:
        return ""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    keys = ("need", "require", "want", "request", "help", "cannot", "unable", "fix", "access", "please")
    reqs = [s for s in sentences if any(k in s.lower() for k in keys)]
    return " ".join(reqs[:3])


# ------- Public API -------
def analyze_email(email_obj: dict) -> dict:
    """
    Analyze an email and return:
    { "sentiment":..., "priority":..., "requirements":..., "contacts":... }
    This uses lightweight heuristics; if GEMINI_API_KEY is present, it will try to refine using the LLM.
    """
    subject = email_obj.get("subject", "") or ""
    body = email_obj.get("body", "") or ""
    combined = (subject + "\n" + body).strip()

    # heuristic baseline
    result = {
        "sentiment": _sentiment(combined),
        "priority": _priority(combined),
        "requirements": _extract_requirements(body),
        "contacts": _extract_contacts(body),
    }

    # If user configured Gemini, try to get a refined JSON from the model
    if os.getenv("GEMINI_API_KEY"):
        prompt = f"""
You are an assistant that extracts metadata from a support email.
Analyze the email below and return a valid JSON object with exactly these keys:
- "priority": one of ["Urgent", "Not urgent"]
- "sentiment": one of ["Positive", "Negative", "Neutral"]
- "requirements": short text summarizing the customer's request (1-2 sentences)
- "contacts": comma-separated contact info (emails, phones) if present

Email:
Subject: {subject}
Body: {body}

Return *only* a JSON object.
"""
        raw = _call_gemini(prompt, max_tokens=250)
        if raw:
            # try to extract JSON substring
            try:
                m = re.search(r"\{.*\}", raw, re.S)
                jtxt = m.group(0) if m else raw
                parsed = json.loads(jtxt)
                # validate parsed keys and normalize
                out = {}
                out["priority"] = parsed.get("priority") or result["priority"]
                out["sentiment"] = parsed.get("sentiment") or result["sentiment"]
                out["requirements"] = parsed.get("requirements") or result["requirements"]
                out["contacts"] = parsed.get("contacts") or result["contacts"]
                return out
            except Exception:
                # fall back to heuristic
                pass

    return result
