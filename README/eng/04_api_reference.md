# API Reference

REST API endpoints for StroyUprav. The AI service runs on FastAPI with automatic OpenAPI/Swagger documentation available at `/api/docs`.

---

## Table of Contents

1. [Authentication](#1-authentication)
2. [Projects](#2-projects)
3. [AI Estimator](#3-ai-estimator)
4. [Tasks](#4-tasks)
5. [Photo Reports](#5-photo-reports)
6. [Budget](#6-budget)
7. [Billing](#7-billing)
8. [Webhooks](#8-webhooks)
9. [Rate Limits](#9-rate-limits)

---

## Base URLs

| Service | Base URL | Description |
|---------|----------|-------------|
| Odoo API | `https://stroyuprav.example.com/api/v1` | ERP endpoints (projects, tasks, budget) |
| AI Service | `https://stroyuprav.example.com/api/ai` | AI estimator, drawing parser |
| Health | `https://stroyuprav.example.com/api/health` | Service health check |

---

## 1. Authentication

All endpoints (except registration and login) require a valid JWT token. Tokens are set as httpOnly cookies.

### POST /api/v1/auth/register

Register a new user account.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "securePassword123!",
  "full_name": "Ivan Petrov",
  "company_name": "StroyKom LLC"
}
```

**Response (201):**
```json
{
  "id": "usr_abc123",
  "email": "user@example.com",
  "full_name": "Ivan Petrov",
  "role": "manager",
  "created_at": "2026-05-27T10:00:00Z"
}
```

> **Note:** The `role` field is NOT accepted in the request body. All new users are assigned the default role. Only admins can change roles via the admin panel. This prevents privilege escalation.

### POST /api/v1/auth/login

**Request:**
```json
{
  "email": "user@example.com",
  "password": "securePassword123!"
}
```

**Response (200):**
```json
{
  "access_token": "eyJhbG...",
  "token_type": "bearer",
  "expires_in": 900
}
```

The `access_token` is also set as an httpOnly cookie. The refresh token (7-day lifetime) is set as a separate httpOnly cookie.

### POST /api/v1/auth/refresh

Refresh an expired access token using the refresh token cookie.

**Response (200):**
```json
{
  "access_token": "eyJhbG...",
  "token_type": "bearer",
  "expires_in": 900
}
```

### POST /api/v1/auth/logout

Invalidates the current session and clears cookies.

**Response (204):** No content.

---

## 2. Projects

### GET /api/v1/projects

List all projects for the authenticated user.

**Query parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `status` | string | `all` | Filter: `active`, `completed`, `on_hold`, `all` |
| `health` | string | `all` | Filter: `green`, `yellow`, `red`, `all` |
| `page` | int | 1 | Page number |
| `per_page` | int | 20 | Items per page (max 100) |

**Response (200):**
```json
{
  "items": [
    {
      "id": "prj_001",
      "name": "Apartment renovation, Tverskaya 15",
      "address": "Moscow, Tverskaya 15, apt 42",
      "status": "active",
      "progress_pct": 45.2,
      "budget_planned": 1500000,
      "budget_actual": 720000,
      "health": "green",
      "start_date": "2026-04-01",
      "end_date": "2026-07-15",
      "created_at": "2026-03-20T08:00:00Z"
    }
  ],
  "total": 12,
  "page": 1,
  "per_page": 20
}
```

### POST /api/v1/projects

Create a new project.

**Request:**
```json
{
  "name": "Office renovation, 3rd floor",
  "address": "Moscow, Lenina 5",
  "client_name": "Olga Sidorova",
  "client_phone": "+79001234567",
  "start_date": "2026-06-01",
  "end_date": "2026-09-01",
  "budget_planned": 3000000
}
```

**Response (201):** Project object (same format as GET).

### GET /api/v1/projects/{project_id}

Get detailed project information.

### PUT /api/v1/projects/{project_id}

Update project fields.

### DELETE /api/v1/projects/{project_id}

Archive a project (soft delete).

---

## 3. AI Estimator

### POST /api/ai/estimates/from-text

Generate a cost estimate from a text description.

**Request:**
```json
{
  "project_id": "prj_001",
  "description": "Apartment 65 sq.m. Full renovation: demolition, wall leveling, laminate, wallpaper, bathroom tile 6 sq.m., electrical rewiring, plumbing.",
  "region_code": "77",
  "price_level": "2026-Q2"
}
```

**Response (202 Accepted):**
```json
{
  "estimate_id": "est_abc123",
  "status": "processing",
  "estimated_time_sec": 30,
  "poll_url": "/api/ai/estimates/est_abc123"
}
```

> **Note:** Estimate generation is asynchronous. Poll the `poll_url` or wait for a webhook notification.

### GET /api/ai/estimates/{estimate_id}

Poll estimate status and retrieve results.

**Response (200) -- completed:**
```json
{
  "estimate_id": "est_abc123",
  "status": "completed",
  "project_id": "prj_001",
  "total_cost": 1450000,
  "currency": "RUB",
  "line_items": [
    {
      "line_num": 1,
      "gesn_code": "46-01-001-01",
      "description": "Demolition of plaster coatings",
      "unit": "sq.m.",
      "quantity": 180.0,
      "unit_rate": 245.50,
      "total": 44190.00,
      "ai_note": null
    },
    {
      "line_num": 2,
      "gesn_code": "15-02-016-01",
      "description": "Wall leveling with plaster mix",
      "unit": "sq.m.",
      "quantity": 180.0,
      "unit_rate": 890.00,
      "total": 160200.00,
      "ai_note": "Price is 12% above regional average. Consider code 15-02-016-03 for savings."
    }
  ],
  "metadata": {
    "region": "Moscow",
    "price_index": "Q2-2026",
    "model_used": "qwen3-72b",
    "generation_time_sec": 28
  },
  "created_at": "2026-05-27T10:05:00Z"
}
```

### POST /api/ai/estimates/from-drawing

Generate an estimate from an uploaded drawing/blueprint.

**Request:** `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | file | Yes | PDF or image (JPG/PNG) of the floor plan |
| `project_id` | string | Yes | Associated project |
| `region_code` | string | No | Region code (default: from project address) |

**Response (202):** Same as `from-text` (async processing).

### GET /api/ai/estimates/{estimate_id}/export

Export estimate as PDF or Excel.

**Query parameters:**

| Parameter | Type | Values |
|-----------|------|--------|
| `format` | string | `pdf`, `xlsx` |

**Response:** File download.

---

## 4. Tasks

### GET /api/v1/projects/{project_id}/tasks

List tasks for a project.

**Query parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | string | `new`, `in_progress`, `under_review`, `completed`, `cancelled` |
| `assignee_id` | string | Filter by assigned worker/crew |
| `priority` | string | `low`, `medium`, `high`, `critical` |

**Response (200):**
```json
{
  "items": [
    {
      "id": "tsk_001",
      "name": "Demolish old floor tiles in bathroom",
      "status": "in_progress",
      "priority": "high",
      "assignee": {
        "id": "usr_worker1",
        "name": "Sergey Ivanov"
      },
      "due_date": "2026-06-05",
      "depends_on": [],
      "subtasks_count": 2,
      "photos_count": 3,
      "created_at": "2026-05-20T09:00:00Z"
    }
  ],
  "total": 24
}
```

### POST /api/v1/projects/{project_id}/tasks

Create a new task.

**Request:**
```json
{
  "name": "Install laminate flooring in living room",
  "description": "45 sq.m., oak laminate, diagonal pattern",
  "assignee_id": "usr_worker1",
  "priority": "medium",
  "due_date": "2026-06-20",
  "depends_on": ["tsk_003"]
}
```

### PATCH /api/v1/tasks/{task_id}/status

Change task status.

**Request:**
```json
{
  "status": "in_progress"
}
```

**Allowed transitions:**
- `new` --> `in_progress` (any role)
- `in_progress` --> `under_review` (any role)
- `under_review` --> `completed` (manager/admin only)
- Any --> `cancelled` (manager/admin only, except from `completed`)
- `cancelled` --> `new` (manager/admin only)

**Response (400) on invalid transition:**
```json
{
  "error": "invalid_transition",
  "message": "Cannot transition from 'completed' to 'cancelled'"
}
```

---

## 5. Photo Reports

### POST /api/v1/tasks/{task_id}/photos

Upload a photo for a task.

**Request:** `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | file | Yes | JPEG or PNG (max 20 MB) |
| `latitude` | float | No | GPS latitude (auto-captured on mobile) |
| `longitude` | float | No | GPS longitude |
| `comment` | string | No | Optional description |

**Response (201):**
```json
{
  "id": "pht_001",
  "task_id": "tsk_001",
  "url": "https://s3.stroyuprav.example.com/stroiuprav/photos/pht_001.jpg",
  "thumbnail_url": "https://s3.stroyuprav.example.com/stroiuprav/photos/pht_001_thumb.jpg",
  "latitude": 55.7558,
  "longitude": 37.6173,
  "taken_at": "2026-05-27T14:30:00Z",
  "uploaded_at": "2026-05-27T14:30:05Z"
}
```

> **Validation:** Files are checked for MIME type, magic bytes, and scanned with ClamAV. Maximum file size: 20 MB.

### GET /api/v1/tasks/{task_id}/photos

List all photos for a task.

### GET /api/v1/projects/{project_id}/photos

List all photos across all tasks in a project.

---

## 6. Budget

### GET /api/v1/projects/{project_id}/budget

Get real-time budget summary.

**Response (200):**
```json
{
  "project_id": "prj_001",
  "planned": 1500000,
  "actual": 720000,
  "deviation_abs": -780000,
  "deviation_pct": -52.0,
  "forecast_total": 1620000,
  "health": "yellow",
  "last_updated": "2026-05-27T12:00:00Z",
  "alerts": [
    {
      "type": "line_item_overrun",
      "message": "Electrical materials exceeded budget by 18%",
      "severity": "warning",
      "created_at": "2026-05-26T09:00:00Z"
    }
  ]
}
```

### GET /api/v1/projects/{project_id}/budget/breakdown

Detailed budget breakdown by estimate line items.

---

## 7. Billing

### GET /api/v1/billing/subscription

Get current subscription details.

**Response (200):**
```json
{
  "plan": "professional",
  "status": "active",
  "price_monthly": 9900,
  "currency": "RUB",
  "trial_ends_at": null,
  "current_period_end": "2026-06-27T00:00:00Z",
  "estimates_used": 12,
  "estimates_limit": null,
  "projects_used": 8,
  "projects_limit": 20
}
```

### POST /api/v1/billing/subscribe

Create or change a subscription.

**Request:**
```json
{
  "plan": "professional",
  "payment_method": "bank_card",
  "return_url": "https://stroyuprav.example.com/billing/success"
}
```

**Response (200):**
```json
{
  "confirmation_url": "https://yookassa.ru/payments/...",
  "payment_id": "pay_abc123"
}
```

---

## 8. Webhooks

### YuKassa Webhook (Incoming)

**POST /api/webhooks/yukassa**

Receives payment notifications from YuKassa. All webhooks are verified:
- HMAC-SHA256 signature check using `YUKASSA_WEBHOOK_SECRET`
- Replay protection: events older than 5 minutes are rejected
- Idempotency: duplicate events are safely ignored

### Estimate Completion Webhook (Outgoing)

If configured, the system sends a POST to the client's URL when an estimate is completed:

```json
{
  "event": "estimate.completed",
  "estimate_id": "est_abc123",
  "project_id": "prj_001",
  "total_cost": 1450000,
  "completed_at": "2026-05-27T10:05:30Z"
}
```

---

## 9. Rate Limits

| Category | Limit | Window |
|----------|-------|--------|
| Authenticated requests | 100 | per minute |
| Anonymous requests | 20 | per minute |
| AI endpoints | 10 | per minute |

**Response (429 Too Many Requests):**
```json
{
  "error": "rate_limit_exceeded",
  "retry_after_sec": 32
}
```

Headers included in all responses:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 42
X-RateLimit-Reset: 1716811200
```
