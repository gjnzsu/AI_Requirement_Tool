# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the App

```bash
# Install dependencies
pip install -r requirements.txt

# Set required env var, then start the server
# Copy .env and fill in ANTHROPIC_API_KEY
python main.py
```

The server runs on port `5000` by default (configurable via `PORT` in `.env`).

## Environment Variables (`.env`)

| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | *(required)* | Anthropic API key |
| `PORT` | `5000` | HTTP port |
| `CLAUDE_MODEL` | `claude-opus-4-5` | Claude model ID used for analysis |
| `DEBUG` | `False` | Flask debug mode |

## Architecture

This is a single-file Flask backend + vanilla JS frontend with no build step.

### Backend (`main.py`)

Flask app with three API endpoints:

- `POST /api/analyze` — accepts `{ text, language }`, sends a structured prompt to the Claude API, returns a JSON object with analysis sections: `actors`, `use_cases`, `functional_requirements`, `non_functional_requirements`, `constraints`, `assumptions`, `risks`.
- `POST /api/export` — accepts `{ data, format }` where format is `json`, `csv`, or `markdown`; returns the requirements data serialized in that format.
- `GET /api/health` — liveness check.

All static files are served from `static/` via Flask's `send_from_directory`.

### Frontend (`static/`)

No framework, no bundler. Bootstrap 5 + custom CSS + vanilla JS.

- `static/index.html` — single HTML page; includes all CSS/JS.
- `static/js/app.js` — all frontend logic: form handling, fetch calls to `/api/analyze` and `/api/export`, and DOM rendering of the structured analysis result.
- `static/css/` — custom styles layered on top of Bootstrap.

### Data Flow

1. User pastes requirements text into the textarea and selects a language (English/Chinese).
2. Frontend POSTs to `/api/analyze`.
3. Backend builds a detailed system prompt instructing Claude to extract structured requirements, calls the Anthropic API, parses the JSON response.
4. Frontend receives the JSON and renders each section (actors, use cases, functional/non-functional requirements, constraints, assumptions, risks) as collapsible cards.
5. User can export the analysis via `/api/export`.
