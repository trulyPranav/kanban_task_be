# Task Management API — Reference

**Base URL:** `http://localhost:8000`  
**API Prefix:** `/api/v1`  
**Interactive UI:** `http://localhost:8000/docs` (Swagger) · `http://localhost:8000/redoc`

---

## Table of Contents

1. [Conventions](#1-conventions)
2. [Common Request Headers](#2-common-request-headers)
3. [Common Response Headers](#3-common-response-headers)
4. [Shared Response Structures](#4-shared-response-structures)
   - [Paginated Response](#41-paginated-response)
   - [Error Response](#42-error-response)
   - [Validation Error Response](#43-validation-error-response)
5. [HTTP Status Codes](#5-http-status-codes)
6. [Error Codes Reference](#6-error-codes-reference)
7. [Rate Limiting](#7-rate-limiting)
8. [Enums](#8-enums)
9. [Users](#9-users)
10. [Tasks](#10-tasks)
11. [Comments](#11-comments)
12. [Health](#12-health)

---

## 1. Conventions

| Convention | Detail |
|---|---|
| Content type | All request and response bodies are `application/json` |
| IDs | All resource IDs are UUID v4 strings, e.g. `"3f2504e0-4f89-11d3-9a0c-0305e82c3301"` |
| Timestamps | ISO 8601 with UTC timezone offset, e.g. `"2026-03-10T14:30:00+00:00"` |
| Pagination | 1-based page index; defaults to `page=1`, `page_size=20` |
| Partial update | `PUT` replaces only the fields you send (uses `exclude_unset`); omitted fields are untouched |
| Nullable fields | Fields typed `string \| null` are explicitly `null` in the response when empty, never omitted |
| Boolean absent | Optional filters that are omitted are treated as "no filter" |

---

## 2. Common Request Headers

| Header | Required | Description |
|---|---|---|
| `Content-Type: application/json` | Yes (for POST/PUT/PATCH) | Body encoding |
| `X-Request-ID: <uuid>` | No | Pass your own trace ID; it is echoed back in the response. If absent, the server generates one. |

---

## 3. Common Response Headers

Every response includes the following headers:

| Header | Value | Description |
|---|---|---|
| `X-Request-ID` | UUID v4 string | Echoes the request's `X-Request-ID`, or a server-generated UUID if none was sent. Use for tracing errors across logs. |
| `X-Content-Type-Options` | `nosniff` | Prevents MIME-type sniffing |
| `X-Frame-Options` | `DENY` | Blocks clickjacking |
| `Strict-Transport-Security` | `max-age=63072000; includeSubDomains; preload` | Enforces HTTPS for 2 years |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Restricts referrer leakage |
| `Permissions-Policy` | `geolocation=(), microphone=(), camera=()` | Disables unused browser features |
| `Content-Security-Policy` | `default-src 'none'; frame-ancestors 'none'` | Prevents framing and inline execution |

---

## 4. Shared Response Structures

### 4.1 Paginated Response

All list endpoints return this envelope. The generic `items` array holds the resource-specific objects.

```json
{
  "items": [ /* array of resource objects */ ],
  "total": 10000,
  "page": 1,
  "page_size": 20,
  "total_pages": 500,
  "has_next": true,
  "has_prev": false
}
```

| Field | Type | Description |
|---|---|---|
| `items` | `array` | The records for this page |
| `total` | `integer` | Total number of matching records across all pages |
| `page` | `integer` | Current page number (1-based) |
| `page_size` | `integer` | Number of items requested per page |
| `total_pages` | `integer` | `ceil(total / page_size)`, minimum 1 |
| `has_next` | `boolean` | `true` if there is a next page |
| `has_prev` | `boolean` | `true` if there is a previous page |

### 4.2 Error Response

All `4xx` and `5xx` responses return this shape:

```json
{
  "detail": "Task '3f2504e0-4f89-11d3-9a0c-0305e82c3301' not found."
}
```

| Field | Type | Description |
|---|---|---|
| `detail` | `string` | Human-readable message describing what went wrong |

### 4.3 Validation Error Response (`422`)

Returned when request body or query parameter validation fails (Pydantic):

```json
{
  "detail": [
    {
      "type": "string_too_short",
      "loc": ["body", "title"],
      "msg": "String should have at least 1 character",
      "input": "",
      "ctx": { "min_length": 1 }
    }
  ]
}
```

| Field | Type | Description |
|---|---|---|
| `detail` | `array` | List of validation failure objects |
| `detail[].type` | `string` | Machine-readable error type from Pydantic |
| `detail[].loc` | `array` | Path to the failing field, e.g. `["body", "title"]` or `["query", "page"]` |
| `detail[].msg` | `string` | Human-readable description |
| `detail[].input` | `any` | The value that was rejected |
| `detail[].ctx` | `object` | Extra context such as `min_length`, `max_length`, `pattern` |

---

## 5. HTTP Status Codes

| Code | Meaning | When returned |
|---|---|---|
| `200 OK` | Success | GET, PUT, PATCH |
| `201 Created` | Resource created | POST |
| `204 No Content` | Success, no body | DELETE |
| `400 Bad Request` | Malformed request | Business rule violations (see [§6](#6-error-codes-reference)) |
| `404 Not Found` | Resource does not exist | Any operation on a non-existent ID |
| `409 Conflict` | Duplicate resource | Creating a user with an already-used email or username |
| `422 Unprocessable Entity` | Validation failed | Invalid field types, missing required fields, constraint violations |
| `429 Too Many Requests` | Rate limit exceeded | More requests than allowed in the time window |
| `500 Internal Server Error` | Unexpected server error | Unhandled exceptions (detail is generic for safety) |

---

## 6. Error Codes Reference

These are the distinct `detail` message patterns the backend can produce.

| Scenario | Status | Example `detail` |
|---|---|---|
| User not found | `404` | `"User '…uuid…' not found."` |
| Task not found | `404` | `"Task '…uuid…' not found."` |
| Comment not found | `404` | `"Comment '…uuid…' not found."` |
| Email already registered | `409` | `"Email 'alice@example.com' is already registered."` |
| Username already taken | `409` | `"Username 'alice' is already taken."` |
| Field too short | `422` | Pydantic validation error array (see §4.3) |
| Field too long | `422` | Pydantic validation error array |
| Invalid enum value | `422` | Pydantic validation error array |
| Rate limit exceeded | `429` | `"Rate limit exceeded: 60 per 1 minute"` |
| Unhandled server error | `500` | `"An unexpected error occurred. Please try again later."` |

---

## 7. Rate Limiting

Rate limits are enforced **per IP address** using a sliding-window counter.

When a limit is exceeded the server responds with `429 Too Many Requests` and includes a `Retry-After` header indicating how many seconds to wait.

```
HTTP/1.1 429 Too Many Requests
Retry-After: 14
X-Request-ID: a3f1c2d4-...

{ "error": "Rate limit exceeded: 60 per 1 minute" }
```

### Per-endpoint limits

| Endpoint | Method | Limit |
|---|---|---|
| `POST /users/` | Create user | 20 / minute |
| `GET /users/` | List users | 60 / minute |
| `GET /users/{id}` | Get user | 60 / minute |
| `PUT /users/{id}` | Update user | 20 / minute |
| `DELETE /users/{id}` | Delete user | 10 / minute |
| `POST /tasks/` | Create task | 30 / minute |
| `GET /tasks/` | List tasks | 60 / minute |
| `GET /tasks/{id}` | Get task | 60 / minute |
| `PUT /tasks/{id}` | Update task | 30 / minute |
| `PATCH /tasks/{id}/status` | Update status | 60 / minute |
| `DELETE /tasks/{id}` | Delete task | 20 / minute |
| `POST /tasks/{id}/comments/` | Add comment | 30 / minute |
| `GET /tasks/{id}/comments/` | List comments | 60 / minute |
| `PUT /tasks/{id}/comments/{cid}` | Update comment | 20 / minute |
| `DELETE /tasks/{id}/comments/{cid}` | Delete comment | 20 / minute |

---

## 8. Enums

### Task Status

| Value | Display label | Kanban column |
|---|---|---|
| `"todo"` | To Do | Column 1 |
| `"in_progress"` | In Progress | Column 2 |
| `"done"` | Done | Column 3 |

### Task Priority

| Value | Display label |
|---|---|
| `"low"` | Low |
| `"medium"` | Medium |
| `"high"` | High |

---

## 9. Users

### 9.1 Object Shape

#### `UserResponse`

```json
{
  "id": "3f2504e0-4f89-11d3-9a0c-0305e82c3301",
  "username": "alice_dev",
  "email": "alice@example.com",
  "full_name": "Alice Smith",
  "avatar_url": "https://example.com/avatar/alice.png",
  "created_at": "2026-01-15T09:00:00+00:00",
  "updated_at": "2026-03-10T14:00:00+00:00"
}
```

| Field | Type | Constraints |
|---|---|---|
| `id` | `string (uuid)` | Read-only |
| `username` | `string` | 3–50 chars, pattern `^[a-zA-Z0-9_.\-]+$`, unique |
| `email` | `string (email)` | Valid email format, unique |
| `full_name` | `string` | 1–100 chars |
| `avatar_url` | `string \| null` | Max 500 chars |
| `created_at` | `string (ISO 8601)` | Read-only |
| `updated_at` | `string (ISO 8601)` | Read-only |

#### `UserSummary` (embedded in Task and Comment responses)

```json
{
  "id": "3f2504e0-4f89-11d3-9a0c-0305e82c3301",
  "username": "alice_dev",
  "full_name": "Alice Smith",
  "avatar_url": "https://example.com/avatar/alice.png"
}
```

---

### 9.2 `POST /api/v1/users/`

Creates a new user.

**Rate limit:** 20 / minute

**Request body:**

```json
{
  "username": "alice_dev",
  "email": "alice@example.com",
  "full_name": "Alice Smith",
  "avatar_url": "https://example.com/avatar/alice.png"
}
```

| Field | Required | Type | Constraints |
|---|---|---|---|
| `username` | ✅ | `string` | 3–50 chars, `^[a-zA-Z0-9_.\-]+$` |
| `email` | ✅ | `string` | Valid email |
| `full_name` | ✅ | `string` | 1–100 chars |
| `avatar_url` | ❌ | `string \| null` | Max 500 chars |

**Response:** `201 Created` → `UserResponse`

**Error cases:**

| Status | Condition |
|---|---|
| `409` | `email` or `username` already in use |
| `422` | Validation failure |

---

### 9.3 `GET /api/v1/users/`

Returns a paginated list of users.

**Rate limit:** 60 / minute

**Query parameters:**

| Param | Type | Default | Description |
|---|---|---|---|
| `page` | `integer ≥ 1` | `1` | Page number |
| `page_size` | `integer 1–100` | `20` | Items per page |
| `search` | `string` | — | Case-insensitive match against `username`, `full_name`, `email` |

**Response:** `200 OK` → `PaginatedResponse<UserResponse>`

---

### 9.4 `GET /api/v1/users/{user_id}`

Fetches a single user.

**Rate limit:** 60 / minute

**Path parameter:** `user_id` — UUID of the user

**Response:** `200 OK` → `UserResponse`

**Error cases:**

| Status | Condition |
|---|---|
| `404` | User not found |

---

### 9.5 `PUT /api/v1/users/{user_id}`

Updates a user. Only the fields included in the body are changed.

**Rate limit:** 20 / minute

**Request body** (all fields optional):

```json
{
  "username": "new_username",
  "email": "new@example.com",
  "full_name": "New Name",
  "avatar_url": null
}
```

**Response:** `200 OK` → `UserResponse`

**Error cases:**

| Status | Condition |
|---|---|
| `404` | User not found |
| `409` | New email or username already in use by another user |
| `422` | Validation failure |

---

### 9.6 `DELETE /api/v1/users/{user_id}`

Deletes a user. All tasks they created or were assigned to will have the respective FK set to `null` (cascade `SET NULL`). Their comments are also set to anonymous (`user_id = null`).

**Rate limit:** 10 / minute

**Response:** `204 No Content`

**Error cases:**

| Status | Condition |
|---|---|
| `404` | User not found |

---

## 10. Tasks

### 10.1 Object Shape

#### `TaskResponse`

```json
{
  "id": "7a1b2c3d-0000-0000-0000-000000000001",
  "title": "Implement login page",
  "description": "Build the login form with email and password fields.",
  "status": "in_progress",
  "priority": "high",
  "due_date": "2026-04-01T00:00:00+00:00",
  "assigned_to_id": "3f2504e0-4f89-11d3-9a0c-0305e82c3301",
  "created_by_id": "3f2504e0-4f89-11d3-9a0c-0305e82c3302",
  "created_at": "2026-03-01T10:00:00+00:00",
  "updated_at": "2026-03-10T14:00:00+00:00",
  "assignee": {
    "id": "3f2504e0-4f89-11d3-9a0c-0305e82c3301",
    "username": "alice_dev",
    "full_name": "Alice Smith",
    "avatar_url": "https://example.com/avatar/alice.png"
  },
  "creator": {
    "id": "3f2504e0-4f89-11d3-9a0c-0305e82c3302",
    "username": "bob_pm",
    "full_name": "Bob Jones",
    "avatar_url": null
  },
  "comment_count": 3
}
```

| Field | Type | Description |
|---|---|---|
| `id` | `string (uuid)` | Read-only |
| `title` | `string` | 1–200 chars |
| `description` | `string \| null` | Max 5000 chars |
| `status` | `TaskStatus enum` | One of `"todo"`, `"in_progress"`, `"done"` |
| `priority` | `TaskPriority enum` | One of `"low"`, `"medium"`, `"high"` |
| `due_date` | `string (ISO 8601) \| null` | Optional deadline |
| `assigned_to_id` | `string (uuid) \| null` | ID of the assigned user |
| `created_by_id` | `string (uuid) \| null` | ID of the creator user |
| `created_at` | `string (ISO 8601)` | Read-only |
| `updated_at` | `string (ISO 8601)` | Read-only |
| `assignee` | `UserSummary \| null` | Embedded assignee object (eager-loaded) |
| `creator` | `UserSummary \| null` | Embedded creator object (eager-loaded) |
| `comment_count` | `integer` | Number of comments on this task |

---

### 10.2 `POST /api/v1/tasks/`

Creates a new task.

**Rate limit:** 30 / minute

**Request body:**

```json
{
  "title": "Implement login page",
  "description": "Build the login form with email and password fields.",
  "status": "todo",
  "priority": "high",
  "due_date": "2026-04-01T00:00:00Z",
  "assigned_to_id": "3f2504e0-4f89-11d3-9a0c-0305e82c3301",
  "created_by_id": "3f2504e0-4f89-11d3-9a0c-0305e82c3302"
}
```

| Field | Required | Type | Default | Constraints |
|---|---|---|---|---|
| `title` | ✅ | `string` | — | 1–200 chars |
| `description` | ❌ | `string \| null` | `null` | Max 5000 chars |
| `status` | ❌ | `TaskStatus` | `"todo"` | See §8 |
| `priority` | ❌ | `TaskPriority` | `"medium"` | See §8 |
| `due_date` | ❌ | `string (ISO 8601) \| null` | `null` | — |
| `assigned_to_id` | ❌ | `string (uuid) \| null` | `null` | Must be an existing user ID |
| `created_by_id` | ❌ | `string (uuid) \| null` | `null` | Must be an existing user ID |

**Response:** `201 Created` → `TaskResponse`

**Error cases:**

| Status | Condition |
|---|---|
| `404` | `assigned_to_id` or `created_by_id` does not match an existing user |
| `422` | Validation failure |

---

### 10.3 `GET /api/v1/tasks/`

Returns a paginated, filterable list of tasks. This is the primary endpoint for populating the Kanban board.

**Rate limit:** 60 / minute

**Query parameters:**

| Param | Type | Default | Description |
|---|---|---|---|
| `page` | `integer ≥ 1` | `1` | Page number |
| `page_size` | `integer 1–100` | `20` | Items per page |
| `status` | `TaskStatus` | — | Filter to one status column |
| `priority` | `TaskPriority` | — | Filter by priority |
| `assigned_to_id` | `string (uuid)` | — | Filter by assignee |
| `created_by_id` | `string (uuid)` | — | Filter by creator |
| `search` | `string` | — | Case-insensitive search across `title` and `description` |

> **Kanban tip:** Call this endpoint three times in parallel — once per status value — to populate the three columns simultaneously without an extra grouping step.
>
> ```
> GET /api/v1/tasks/?status=todo&page=1&page_size=50
> GET /api/v1/tasks/?status=in_progress&page=1&page_size=50
> GET /api/v1/tasks/?status=done&page=1&page_size=50
> ```

**Response:** `200 OK` → `PaginatedResponse<TaskResponse>`

---

### 10.4 `GET /api/v1/tasks/{task_id}`

Fetches a single task with full detail including embedded assignee, creator, and comment count.

**Rate limit:** 60 / minute

**Response:** `200 OK` → `TaskResponse`

**Error cases:**

| Status | Condition |
|---|---|
| `404` | Task not found |

---

### 10.5 `PUT /api/v1/tasks/{task_id}`

Updates a task. Only the fields present in the body are changed.

**Rate limit:** 30 / minute

**Request body** (all fields optional):

```json
{
  "title": "Updated title",
  "description": "Updated description.",
  "status": "in_progress",
  "priority": "low",
  "due_date": null,
  "assigned_to_id": "3f2504e0-4f89-11d3-9a0c-0305e82c3301"
}
```

**Response:** `200 OK` → `TaskResponse`

**Error cases:**

| Status | Condition |
|---|---|
| `404` | Task not found, or `assigned_to_id` does not match an existing user |
| `422` | Validation failure |

---

### 10.6 `PATCH /api/v1/tasks/{task_id}/status`

Updates only the status of a task. Designed for Kanban drag-and-drop — minimal payload, high rate limit.

**Rate limit:** 60 / minute

**Request body:**

```json
{
  "status": "done"
}
```

| Field | Required | Type |
|---|---|---|
| `status` | ✅ | `TaskStatus` enum |

**Response:** `200 OK` → `TaskResponse`

**Error cases:**

| Status | Condition |
|---|---|
| `404` | Task not found |
| `422` | Invalid status value |

---

### 10.7 `DELETE /api/v1/tasks/{task_id}`

Deletes a task and all of its comments (cascade delete).

**Rate limit:** 20 / minute

**Response:** `204 No Content`

**Error cases:**

| Status | Condition |
|---|---|
| `404` | Task not found |

---

## 11. Comments

Comments are nested under tasks. All comment endpoints require a valid `task_id` in the path.

### 11.1 Object Shape

#### `CommentResponse`

```json
{
  "id": "c1d2e3f4-0000-0000-0000-000000000001",
  "task_id": "7a1b2c3d-0000-0000-0000-000000000001",
  "user_id": "3f2504e0-4f89-11d3-9a0c-0305e82c3301",
  "content": "I've started working on this — blocked on the design mock.",
  "created_at": "2026-03-10T09:00:00+00:00",
  "updated_at": "2026-03-10T09:00:00+00:00",
  "author": {
    "id": "3f2504e0-4f89-11d3-9a0c-0305e82c3301",
    "username": "alice_dev",
    "full_name": "Alice Smith",
    "avatar_url": "https://example.com/avatar/alice.png"
  }
}
```

| Field | Type | Description |
|---|---|---|
| `id` | `string (uuid)` | Read-only |
| `task_id` | `string (uuid)` | The parent task |
| `user_id` | `string (uuid) \| null` | Author's user ID; `null` if deleted |
| `content` | `string` | 1–2000 chars |
| `created_at` | `string (ISO 8601)` | Read-only |
| `updated_at` | `string (ISO 8601)` | Read-only |
| `author` | `UserSummary \| null` | Embedded author; `null` if user was deleted |

---

### 11.2 `POST /api/v1/tasks/{task_id}/comments/`

Adds a comment to a task.

**Rate limit:** 30 / minute

**Request body:**

```json
{
  "content": "I've started working on this.",
  "user_id": "3f2504e0-4f89-11d3-9a0c-0305e82c3301"
}
```

| Field | Required | Type | Constraints |
|---|---|---|---|
| `content` | ✅ | `string` | 1–2000 chars |
| `user_id` | ❌ | `string (uuid) \| null` | Must be an existing user ID |

**Response:** `201 Created` → `CommentResponse`

**Error cases:**

| Status | Condition |
|---|---|
| `404` | `task_id` not found, or `user_id` does not match an existing user |
| `422` | Validation failure |

---

### 11.3 `GET /api/v1/tasks/{task_id}/comments/`

Returns paginated comments for a task, ordered oldest-first.

**Rate limit:** 60 / minute

**Query parameters:**

| Param | Type | Default | Description |
|---|---|---|---|
| `page` | `integer ≥ 1` | `1` | Page number |
| `page_size` | `integer 1–100` | `20` | Items per page |

**Response:** `200 OK` → `PaginatedResponse<CommentResponse>`

**Error cases:**

| Status | Condition |
|---|---|
| `404` | `task_id` not found |

---

### 11.4 `PUT /api/v1/tasks/{task_id}/comments/{comment_id}`

Replaces the content of a comment.

**Rate limit:** 20 / minute

**Request body:**

```json
{
  "content": "Updated comment text."
}
```

| Field | Required | Type | Constraints |
|---|---|---|---|
| `content` | ✅ | `string` | 1–2000 chars |

**Response:** `200 OK` → `CommentResponse`

**Error cases:**

| Status | Condition |
|---|---|
| `404` | `task_id` or `comment_id` not found, or comment does not belong to the given task |
| `422` | Validation failure |

---

### 11.5 `DELETE /api/v1/tasks/{task_id}/comments/{comment_id}`

Deletes a comment.

**Rate limit:** 20 / minute

**Response:** `204 No Content`

**Error cases:**

| Status | Condition |
|---|---|
| `404` | `task_id` or `comment_id` not found, or comment does not belong to the given task |

---

## 12. Health

### `GET /health`

Lightweight health check. No rate limit.

**Response:** `200 OK`

```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

Use this endpoint for load balancer probes and uptime monitors.
