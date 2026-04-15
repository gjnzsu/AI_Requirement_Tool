# FastAPI Migration Notes

## Purpose

This document freezes the current Flask API contract before the FastAPI strangler migration begins. It uses `app.py` and `src/webapp/routes/*.py` as the source of truth for endpoint behavior.

## Baseline Verification

Command run:

```bash
python -m pytest tests/integration/api/ -q
```

Result:

- `61 passed`
- `2 failed`

Observed failures:

- `tests/integration/api/test_auth_api.py::TestAuthAPI::test_chat_endpoint_with_valid_token`
  - Expected `200`
  - Observed `500`
- `tests/integration/api/test_model_api.py::TestModelAPI::test_model_switching_persistence`
  - Expected `200`
  - Observed `500`

No application code was changed for this baseline freeze.

## Frozen API Contract

The table below captures the current Flask contract as implemented today.

| Endpoint | Method | Required status codes | Response shape / contract |
| --- | --- | --- | --- |
| `/api/auth/login` | `POST` | `200`, `400`, `401`, `503`, `500` | `200` returns JSON `{ "token": string, "user": { "id": number, "username": string, "email": string } }`. `400` returns `{ "error": string }` when username or password is missing. `401` returns `{ "error": string }` for invalid credentials. `503` returns `{ "error": string }` when auth is not configured. |
| `/api/auth/logout` | `POST` | `200`, `401`, `503` | `200` returns JSON `{ "success": true, "message": "Logged out successfully" }`. Authentication is enforced by `token_required`, so missing or invalid tokens return `401` via the auth layer. `503` returns `{ "error": string }` when auth is not configured. |
| `/api/auth/me` | `GET` | `200`, `401`, `404` | `200` returns JSON `{ "user": object }` for the authenticated user. Missing or invalid tokens return `401` via `token_required`. If a token is valid but no user is resolved, the route returns `{ "error": "User not found" }` with `404`. |
| `/api/chat` | `POST` | `200`, `400`, `401`, `429`, `500` | Request body is JSON and must include `message`. Optional fields: `conversation_id`, `model`, `agent_mode`. `200` returns JSON `{ "response": string, "conversation_id": string, "agent_mode": string, "ui_actions": array, "workflow_progress": array|object, "timestamp": string }`. `400` is returned for missing/invalid JSON, missing message, invalid model, or invalid agent mode. `401` comes from `token_required`. `429` is used for rate-limit failures. Other exceptions return `500` with `{ "error": string }`. |
| `/api/current-model` | `GET` | `200`, `401`, `500` | `200` returns JSON `{ "model": string, "available_models": ["openai", "gemini", "deepseek"] }`. Missing or invalid tokens return `401` via `token_required`. Other exceptions return `{ "error": string }` with `500`. |
| `/api/conversations` | `GET` | `200`, `401`, `500` | `200` returns JSON `{ "conversations": array }`. Each conversation item includes `id`, `title`, `created_at`, `updated_at`, and `message_count` when available. |
| `/api/conversations/<conversation_id>` | `GET` | `200`, `401`, `404`, `500` | `200` returns JSON `{ "conversation": object }`. Missing conversations return `{ "error": "Conversation not found" }` with `404`. |
| `/api/conversations/<conversation_id>` | `DELETE` | `200`, `401`, `404`, `500` | `200` returns JSON `{ "success": true }`. Missing conversations return `{ "error": "Conversation not found" }` with `404`. |
| `/api/conversations` | `DELETE` | `200`, `401`, `500` | `200` returns JSON `{ "success": true }` after clearing all conversations. |
| `/api/conversations/<conversation_id>/title` | `PUT` | `200`, `400`, `401`, `404`, `500` | Body must be JSON with `title`. `200` returns JSON `{ "success": true, "title": string }`. Missing title returns `{ "error": "Title is required" }` with `400`. Missing conversations return `404`. |
| `/api/new-chat` | `POST` | `200`, `401`, `500` | `200` returns JSON `{ "conversation_id": string, "success": true }`. |
| `/api/search` | `GET` | `200`, `400`, `401`, `500` | Requires query string parameter `q`. `200` returns JSON `{ "conversations": array }`. Missing `q` returns `{ "error": "Search query is required" }` with `400`. Invalid `limit` returns `{ "error": string }` with `400`. |
| `/api/health` | `GET` | `200` | Returns JSON `{ "status": "ok" }`. |
| `/metrics` | `GET` | `200` | Returns Prometheus exposition text (`Content-Type: text/plain; version=0.0.4`) when Prometheus support is installed. |

## Notes For Migration

- `/api/auth/*`, `/api/chat`, `/api/current-model`, `/api/conversations*`, `/api/new-chat`, and `/api/search` are all protected by the current Flask auth decorator where applicable.
- The two baseline failures above are part of the current snapshot and should be treated as pre-migration defects unless fixed in a separate change.
- Any FastAPI replacement should preserve these statuses and JSON field names unless a dedicated contract change is planned and tested separately.
