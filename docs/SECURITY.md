# Security Implementation Guide

This document details every security control implemented in the Task Management API. Pass this to your security reviewer or frontend team to understand the full threat-model coverage.

---

## Table of Contents

1. [Security Response Headers](#1-security-response-headers)
2. [CORS Policy](#2-cors-policy)
3. [Rate Limiting](#3-rate-limiting)
4. [Request Tracing](#4-request-tracing)
5. [Input Validation](#5-input-validation)
6. [Database Layer](#6-database-layer)
7. [Error Handling](#7-error-handling)
8. [OWASP Top 10 Coverage](#8-owasp-top-10-coverage)
9. [Recommendations Before Production](#9-recommendations-before-production)

---

## 1. Security Response Headers

The `SecurityHeadersMiddleware` injects the following headers on **every** HTTP response before it is sent to the client.

| Header | Value | Threat mitigated |
|---|---|---|
| `X-Content-Type-Options` | `nosniff` | MIME-type confusion / drive-by download attacks |
| `X-Frame-Options` | `DENY` | Clickjacking — prevents this API being embedded in an `<iframe>` |
| `Strict-Transport-Security` | `max-age=63072000; includeSubDomains; preload` | SSL-stripping / MITM — forces HTTPS for 2 years including all subdomains |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Referrer leakage — cross-origin requests receive only the origin, not the full URL |
| `Permissions-Policy` | `geolocation=(), microphone=(), camera=()` | Fingerprinting / feature abuse — disables browser APIs not used by this service |
| `Content-Security-Policy` | `default-src 'none'; frame-ancestors 'none'` | XSS fallback, prevents framing; tighten further when serving the Swagger UI |
| `Server` *(removed)* | — | Technology fingerprinting — strips the `uvicorn` version string from all responses |

### Notes for the frontend

- The `Strict-Transport-Security` header is only enforced by browsers once the first HTTPS response has been received. Ensure your deployment terminates TLS at the load balancer or reverse proxy and proxies to uvicorn over HTTP internally.
- If you host the Swagger UI or any HTML on the same origin, adjust `Content-Security-Policy` to allow `script-src 'self'` and `style-src 'self'`.

---

## 2. CORS Policy

Cross-Origin Resource Sharing is managed by FastAPI's `CORSMiddleware`.

| Setting | Value |
|---|---|
| `allow_origins` | Configured via `CORS_ORIGINS` in `.env` — defaults to `["http://localhost:3000", "http://localhost:5173"]` |
| `allow_credentials` | `true` — cookies and `Authorization` headers are allowed |
| `allow_methods` | `["*"]` — all HTTP methods |
| `allow_headers` | `["*"]` — all headers including `X-Request-ID` |

**To add your production frontend origin**, update `CORS_ORIGINS` in `.env`:

```env
CORS_ORIGINS=["https://app.yourdomain.com"]
```

> Do **not** use a wildcard `*` origin in production, especially when `allow_credentials` is `true`. Browsers reject `*` with credentials anyway — always enumerate your exact frontend origins.

---

## 3. Rate Limiting

Rate limiting is implemented with [slowapi](https://github.com/laurents/slowapi) (a Python port of Flask-Limiter) backed by an in-memory counter keyed on **the client's remote IP address**.

### How it works

1. Each request increments a sliding-window counter for that IP + endpoint combo.
2. When the counter exceeds the limit, `429 Too Many Requests` is returned immediately.
3. The `Retry-After` response header tells the client how many seconds to wait.

### Limits summary

| Resource action | Limit |
|---|---|
| Create user | 20 / minute |
| Read user(s) | 60 / minute |
| Update user | 20 / minute |
| Delete user | 10 / minute |
| Create task | 30 / minute |
| Read task(s) | 60 / minute |
| Update task | 30 / minute |
| Update task status (Kanban) | 60 / minute |
| Delete task | 20 / minute |
| Add comment | 30 / minute |
| Read comments | 60 / minute |
| Update comment | 20 / minute |
| Delete comment | 20 / minute |

### Frontend guidance

- Check for `429` responses and surface a user-friendly message.
- Read the `Retry-After` header and implement exponential back-off or a countdown before retrying.
- For Kanban drag-and-drop, use the dedicated `PATCH /tasks/{id}/status` endpoint (60/min) rather than the full `PUT` (30/min) to get double the throughput.

---

## 4. Request Tracing

The `RequestIDMiddleware` provides end-to-end trace correlation.

### How it works

- If the client sends `X-Request-ID: <your-uuid>` in the request, the server echoes it back on the response.
- If the header is absent, the server generates a fresh UUID v4 and returns it.

### Usage

```
Request  →  X-Request-ID: 550e8400-e29b-41d4-a716-446655440000
Response ←  X-Request-ID: 550e8400-e29b-41d4-a716-446655440000
```

- The server logs every unhandled error with the URL and method. If you pass `X-Request-ID`, include it in your bug reports to allow log correlation.
- Generate a fresh UUID per user action on the frontend, not per HTTP request, so you can tie a multi-request flow (e.g., create task + fetch board) to a single trace ID.

---

## 5. Input Validation

All input is validated by **Pydantic v2** before it reaches the service layer. No raw user input ever reaches a database query directly.

### String constraints

| Field | Min | Max | Pattern |
|---|---|---|---|
| `username` | 3 | 50 chars | `^[a-zA-Z0-9_.\-]+$` |
| `full_name` | 1 | 100 chars | — |
| `email` | — | — | RFC 5322 (via `pydantic[email]`) |
| `avatar_url` | — | 500 chars | — |
| `task.title` | 1 | 200 chars | — |
| `task.description` | — | 5000 chars | — |
| `comment.content` | 1 | 2000 chars | — |
| `search` query param | — | 100 chars | — |

### Enum validation

`status` and `priority` fields only accept the exact string values defined in the enum (see `API_REFERENCE.md §8`). Any other string returns `422`.

### Pagination bounds

| Param | Min | Max |
|---|---|---|
| `page` | 1 | — |
| `page_size` | 1 | 100 |

### Injection prevention

- All database queries use **SQLAlchemy ORM with parameterised statements** — user-supplied values are never interpolated into raw SQL strings, preventing SQL injection.
- No shell commands, template rendering, or `eval`-style execution is used anywhere in the codebase, preventing command injection and SSTI.
- Pydantic rejects unexpected fields by default — extra keys in request bodies are silently ignored (Pydantic v2 default), not executed.

---

## 6. Database Layer

### Async ORM

All database access goes through SQLAlchemy 2.0 async ORM with parameterised queries. The repository pattern keeps raw query logic isolated from business logic and routers.

### FK integrity

| Relationship | On delete behaviour |
|---|---|
| `Task.assigned_to_id → users.id` | `SET NULL` — task persists, assignee field cleared |
| `Task.created_by_id → users.id` | `SET NULL` — task persists, creator field cleared |
| `Comment.task_id → tasks.id` | `CASCADE` — comments are deleted with their parent task |
| `Comment.user_id → users.id` | `SET NULL` — comment persists, author becomes anonymous |

### Index strategy

Composite and single-column indexes are pre-defined on the most common query patterns:

- `(status, priority)` — Kanban column + priority filter
- `created_at` — default sort order
- `(assigned_to_id, created_by_id)` — filter by user
- `task_id` on comments — list comments for a task

---

## 7. Error Handling

### Principle: never leak internals

The global exception handler catches any unhandled `Exception` and returns a **generic** `500` message. Stack traces and internal details are only written to the **server log**, never to the API response.

```python
# What the client receives:
{ "detail": "An unexpected error occurred. Please try again later." }

# What the server logs (include X-Request-ID in bug reports):
ERROR | Unhandled exception on GET /api/v1/tasks/...
Traceback (most recent call last): ...
```

### Predictable error shapes

All `4xx` errors return `{ "detail": "..." }` — a single string. `422` validation errors return `{ "detail": [...] }` — an array. See `API_REFERENCE.md §4.2` and `§4.3` for the exact shapes.

---

## 8. OWASP Top 10 Coverage

| # | Vulnerability | Status | Implementation |
|---|---|---|---|
| A01 | Broken Access Control | ⚠️ Partial | No auth layer yet — see §9. FK-level isolation prevents cross-task comment operations. |
| A02 | Cryptographic Failures | ✅ Addressed | No secrets stored; HSTS header enforces TLS in transit; `.env` is git-ignored |
| A03 | Injection | ✅ Addressed | SQLAlchemy ORM parameterised queries; Pydantic input validation on all fields |
| A04 | Insecure Design | ✅ Addressed | Layered architecture (router → service → repository); rate limiting; input constraints |
| A05 | Security Misconfiguration | ✅ Addressed | Security headers middleware; `Server` header stripped; CORS origin allowlist |
| A06 | Vulnerable Components | ✅ Addressed | All dependencies pinned with minimum versions in `requirements.txt`; run `pip audit` regularly |
| A07 | Auth & Session Failures | ⚠️ Not implemented | See §9 |
| A08 | Software & Data Integrity | ✅ Addressed | No deserialization of untrusted objects; Pydantic enforces schema integrity |
| A09 | Security Logging & Monitoring | ✅ Addressed | Structured logging on all errors with method + URL; `X-Request-ID` enables trace correlation |
| A10 | SSRF | ✅ Addressed | No outbound HTTP calls from this service; `avatar_url` is stored as a string, never fetched |

---

## 9. Recommendations Before Production

The following items are **not implemented** and must be addressed before deploying to a production environment.

### 9.1 Authentication & Authorisation (A01 / A07)

The API currently has no authentication layer. Any caller can read, modify, or delete any resource.

**Recommended approach:**
- Add JWT Bearer token authentication using [`python-jose`](https://github.com/mpdavis/python-jose) or [`authlib`](https://docs.authlib.org/).
- Protect all mutating endpoints with a `get_current_user` dependency.
- Add ownership checks (e.g., only the task creator or assignee can update a task).
- Consider OAuth 2.0 / OIDC with a provider (Supabase Auth, Auth0, Clerk) if you want social login.

### 9.2 HTTPS / TLS Termination

The `Strict-Transport-Security` header is included but only meaningful once TLS is active. In production:

- Terminate TLS at a reverse proxy (nginx, Caddy) or load balancer (AWS ALB).
- Never expose uvicorn directly on port 80 or 443 in production.

### 9.3 Persistent Rate Limit Store

The current in-memory rate limiter resets on every server restart and does not work across multiple instances. In production use a Redis backend:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="redis://localhost:6379",
)
```

Add `redis` to `requirements.txt`.

### 9.4 Secrets Management

- Rotate `DATABASE_URL` credentials regularly.
- Use a secrets manager (AWS Secrets Manager, HashiCorp Vault, Doppler) rather than a `.env` file on production servers.
- Never commit `.env` — it is already in `.gitignore`.

### 9.5 Database

- Switch `DATABASE_URL` to PostgreSQL (`postgresql+asyncpg://...`) for production workloads.
- Enable connection pooling (PgBouncer or SQLAlchemy pool settings).
- Take regular automated backups.

### 9.6 Dependency Auditing

Run regularly to catch known CVEs in dependencies:

```bash
pip install pip-audit
pip-audit
```

### 9.7 Content-Security-Policy Tightening

The current CSP (`default-src 'none'`) is correct for a pure JSON API. If you add Swagger UI endpoints, adjust:

```
Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; frame-ancestors 'none'
```
