# services/response_service.py
import os
import glob
import re
import json
from pathlib import Path

KB_DIR = Path("knowledge_base")  # folder containing .txt files to be used for RAG


def _call_gemini(prompt: str, max_tokens: int = 512) -> str | None:
    """
    Best-effort Gemini wrapper. Returns generated text or None.
    (Same strategy used in nlp_service; duplicated so this file can be used standalone)
    """
    try:
        import google.generativeai as genai
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

        if hasattr(genai, "generate_text"):
            resp = genai.generate_text(model="gemini-2.0-flash", prompt=prompt, max_output_tokens=max_tokens)
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
        print("Gemini call failed:", e)
        return None

    return None


def _tokenize(text: str):
    return re.findall(r"\w+", (text or "").lower())


def retrieve_relevant_kb(email_body: str, top_k: int = 3):
    """
    Naive retrieval: load all .txt files in knowledge_base, score them by word overlap, return top_k texts.
    """
    email_tokens = set(_tokenize(email_body))
    if not email_tokens or not KB_DIR.exists():
        return []

    candidates = []
    for path in KB_DIR.glob("*.txt"):
        try:
            txt = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        doc_tokens = set(_tokenize(txt))
        # score = overlap ratio
        overlap = email_tokens.intersection(doc_tokens)
        score = len(overlap)
        if score > 0:
            candidates.append((score, txt, path.name))
    # sort by score desc
    candidates.sort(key=lambda x: x[0], reverse=True)
    return [{"score": c[0], "text": c[1], "source": c[2]} for c in candidates[:top_k]]


def generate_response(email_obj: dict, analysis: dict) -> str:
    """
    Generate a context-aware draft reply using retrieved KB + Gemini.
    Falls back to a heuristic reply if Gemini is not available.
    """
    sender = email_obj.get("sender", "Customer")
    subject = email_obj.get("subject", "")
    body = email_obj.get("body", "")

    # 1) Retrieve KB excerpts
    contexts = retrieve_relevant_kb(body, top_k=3)
    kb_text = "\n\n---\n\n".join([f"[{c['source']}]\n{c['text']}" for c in contexts]) if contexts else ""

    # 2) Build prompt
    prompt_parts = [
        "You are a professional customer support agent. Write a concise, polite, empathetic reply.",
        f"Customer message (subject): {subject}",
        f"Customer message (body): {body}",
        "",
    ]
    if kb_text:
        prompt_parts.append("Use the following knowledge-base excerpts to answer and reference them where appropriate:")
        prompt_parts.append(kb_text)
        prompt_parts.append("")

    prompt_parts.append("Constraints:")
    prompt_parts.append("- Maintain a friendly professional tone.")
    prompt_parts.append("- Acknowledge frustration if sentiment is Negative.")
    prompt_parts.append("- If the message mentions a product/feature, reference it.")
    prompt_parts.append("- Keep it short (4-8 sentences).")
    prompt_parts.append("- Do NOT include any internal notes or JSON, only the reply text.")
    prompt = "\n".join(prompt_parts)

    # 3) If Gemini available, call it
    if os.getenv("GEMINI_API_KEY"):
        out = _call_gemini(prompt, max_tokens=400)
        if out:
            # best-effort cleanup
            return out.strip()

    # 4) Fallback heuristic draft
    tone_open = "Thanks for reaching out." if analysis.get("sentiment") != "Negative" \
        else "I'm really sorry for the trouble you're facing — thank you for reporting this."

    priority_line = "I've marked this as urgent and escalated it to our team." \
        if analysis.get("priority") == "Urgent" else "I've logged this request and our team will follow up."

    requirements = analysis.get("requirements") or "the details you shared"
    closing = "If you can share screenshots or any additional details, please reply to this message."

    draft = (
        f"Hi {sender.split('<')[0].strip()},\n\n"
        f"{tone_open} Based on your message, I understand: {requirements}.\n\n"
        f"{priority_line} {closing}\n\n"
        f"Best regards,\nSupport Team"
    )
    return draft
