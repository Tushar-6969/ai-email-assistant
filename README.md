# AI Email Assistant

**A compact AI-powered email triage & response prototype**

---

## Overview

This repository contains a lightweight Flask-based prototype that demonstrates how to build an AI email assistant. The assistant ingests email text, applies simple NLP to classify and extract intent, and generates suggested responses. The implementation is intentionally small and easy to run locally so you can extend it for production use (connect real mailboxes, replace the LLM, add auth, deploy, etc.).

## Features

* Simple web dashboard to view sample emails and suggested replies.
* Modular service layout: `email_service`, `nlp_service`, `response_service` for clear separation of concerns.
* Local CSV dataset for example email content and testing (`dataset.csv`).
* Lightweight SQLite helper in `utils/db.py` for persistence (can be replaced by any DB).
* Configurable using `.env`.

## Tech stack

* Python 3.11+ (the code was developed with Python 3.13 in mind)
* Flask (web server & templating)
* Pandas (data loading)
* Any LLM or local model can be plugged into `response_service.py` for real responses

## Quick start (local)

1. Clone the repo (or copy files into a project folder).

2. Create a virtual environment and activate it:

```bash
python -m venv venv
source venv/bin/activate   # macOS / Linux
venv\Scripts\activate     # Windows
```

3. Install requirements (example):

```bash
pip install flask pandas python-dotenv
```

4. Create a `.env` file (the repo contains an example `.env`). Example variables:

```
FLASK_ENV=development
SECRET_KEY=your_secret_here
DB_PATH=./email.db
LLM_API_KEY=your_llm_api_key   # optional — used by response_service
```

5. Run the app:

```bash
python app.py
```

6. Open `http://127.0.0.1:5000` in your browser to view the dashboard.

## File / Module descriptions

```
email/
├── .env                   # environment variables (sensitive values should not be committed)
├── app.py                 # Flask entrypoint; routes + wiring of services
├── dataset.csv            # example emails used for demo/testing
├── services/
│   ├── email_service.py   # handles "email" ingestion and retrieval (CSV-based demo)
│   ├── nlp_service.py     # preprocessing, intent classification, basic NER or keywords
│   └── response_service.py# builds/generates suggested replies (plug-in LLM here)
├── static/
│   └── style.css          # basic CSS for dashboard
├── templates/
│   └── dashboard.html     # dashboard UI to list emails and suggested replies
└── utils/
    └── db.py              # minimal DB helper (SQLite wrapper)
```

### `app.py`

`app.py` is the Flask application that wires the services and exposes routes. Typical flow:

1. Load dataset (CSV) or DB entries via `email_service`.
2. For each email, call `nlp_service` to extract intent/keywords.
3. Call `response_service` to generate a suggested reply.
4. Render results in `templates/dashboard.html`.

### `services/email_service.py`

* Demo-oriented: reads `dataset.csv` and returns email records.
* In production this module would connect to an IMAP/POP/Exchange API or mail provider.

### `services/nlp_service.py`

* Lightweight preprocessing: cleaning, tokenization, keyword extraction and basic intent heuristics.
* Replace or extend with spaCy, transformers, or custom classifiers for stronger intent detection.

### `services/response_service.py`

* The place to integrate an LLM (OpenAI, Google Gemini, Anthropic, local LLM) or rule-based template responses.
* Keep prompts strict and minimal to avoid extra output in the generated replies.

## Running tests

* The repository contains a minimal smoke test (if included) or you can manually test by running the app and trying multiple emails in the dashboard.
* Add `pytest` and create test files (e.g. `tests/test_services.py`) to automate behavior checks.

## Environment variables

Store API keys and secrets in `.env` or your secret manager. Example keys to include:

* `FLASK_ENV` — development/production
* `SECRET_KEY` — Flask session secret
* `DB_PATH` — SQLite file path
* `LLM_API_KEY` — key for any external LLM that `response_service` will call

## Folder structure (concise)

```
email/
  app.py
  dataset.csv
  .env
  services/
```
