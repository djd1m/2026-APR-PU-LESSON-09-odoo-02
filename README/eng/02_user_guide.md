# User Guide

End-user workflows for StroyUprav. This guide covers the six core modules available in the MVP.

---

## Table of Contents

1. [Onboarding](#1-onboarding)
2. [Projects and the Dashboard](#2-projects-and-the-dashboard)
3. [AI Cost Estimator](#3-ai-cost-estimator)
4. [Task Management](#4-task-management)
5. [Photo Reports](#5-photo-reports)
6. [Real-Time Budget](#6-real-time-budget)
7. [Billing and Subscriptions](#7-billing-and-subscriptions)
8. [Roles and Permissions](#8-roles-and-permissions)

---

## 1. Onboarding

After registration, a 4-question onboarding quiz personalizes the interface:

1. **Your role** -- company manager, site foreman (prorab), or client
2. **Company size** -- solo, 5-15 people, 15-50, 50+
3. **Number of active sites** -- 1-3, 3-10, 10+
4. **Primary need** -- cost estimation, project tracking, both

The quiz takes under 3 minutes. Based on answers, the dashboard layout and default views are adjusted for the user's role.

---

## 2. Projects and the Dashboard

### Creating a Project

1. Click **"New Project"** (or the `+` button on mobile)
2. Fill in:
   - Project name (e.g., "Apartment renovation, Tverskaya 15")
   - Address (used for geotagging photos)
   - Client name and contact
   - Planned start/end dates
   - Budget (optional -- can be set after the AI estimate)
3. Save

### Dashboard Overview

The main dashboard shows all projects on one screen:

| Column | Description |
|--------|-------------|
| **Project** | Name and address |
| **Progress** | Percentage complete (weighted by planned labor effort) |
| **Budget** | Actual / Planned spending with color indicator |
| **Deadline** | End date with overdue warning |
| **Health** | GREEN / YELLOW / RED based on budget deviation, overdue tasks, and progress lag |

- **GREEN** -- on track (budget deviation < 5%, no overdue tasks)
- **YELLOW** -- attention needed (deviation 5-10% or minor delays)
- **RED** -- at risk (deviation > 10% or critical delays)

### Filtering and Sorting

Filter projects by:
- Status (active, completed, on hold)
- Work type (renovation, new construction, repairs)
- Assigned crew
- Health score

---

## 3. AI Cost Estimator

The AI Estimator generates cost estimates based on Russian federal norms (GESN/FER). It replaces manual estimation that typically takes 2-5 days with a 5-minute AI-assisted process.

### From Text Description

1. Navigate to **Estimates > New Estimate**
2. Enter a text description of the work:
   ```
   Apartment 65 sq.m., 2 rooms. Full renovation:
   demolition of old finishes, leveling walls and ceiling,
   laminate flooring, wallpaper, suspended ceiling in bathroom,
   tile in bathroom 6 sq.m., replacement of electrical wiring,
   plumbing installation.
   ```
3. Click **"Generate Estimate"**
4. The AI:
   - Classifies the description into standard work categories
   - Looks up matching GESN/FER unit rates via semantic search
   - Applies current Minstroy quarterly price indices
   - Calculates: `base_rate * quantity * index + overhead + profit`
   - Flags items priced >10% above market average

### From a Drawing/Blueprint

1. Navigate to **Estimates > New Estimate > Upload Drawing**
2. Upload a PDF or photo of the floor plan
3. The AI (OCR via Qwen3-VL / GPT-4o fallback):
   - Recognizes rooms and calculates areas
   - Identifies work types
   - Matches to GESN/FER rates
   - Target accuracy: 85%+ on area recognition
4. Review and manually adjust if needed

### Estimate Output

The generated estimate includes:

| Column | Description |
|--------|-------------|
| # | Line item number |
| GESN/FER Code | Reference to the normative database |
| Work Description | Standardized work name |
| Unit | sq.m., linear m., pcs, etc. |
| Quantity | Calculated volume |
| Unit Rate | Price per unit (with current indices) |
| Total | Quantity * Unit Rate |
| AI Note | Optimization suggestions (if price > market average) |

### Export

- **PDF** -- branded estimate with company logo ("Created in StroyUprav" watermark on free plan)
- **Excel** -- full data for further editing
- **Share link** -- read-only link for the client

---

## 4. Task Management

### Creating Tasks

1. Open a project, go to the **Tasks** tab
2. Click **"New Task"**
3. Fill in:
   - Task name
   - Description
   - Assigned crew / worker
   - Priority (low / medium / high / critical)
   - Due date
   - Dependencies (optional -- "start after Task X is done")

### Task Statuses

Tasks follow a fixed state machine:

```
New --> In Progress --> Under Review --> Completed
 |                                         ^
 |         (any status except Completed)   |
 +----------> Cancelled -----> New ---------+
                (reactivation)
```

- Only **managers and admins** can mark tasks as "Completed" or "Cancelled"
- Workers can move tasks to "In Progress" and "Under Review"
- Push notifications are sent on status changes

### Subtasks and Dependencies

- Tasks can have subtasks (one level deep)
- Dependencies: Task B cannot start until Task A is "Completed"
- Gantt chart visualization is available in the P1 (Should Have) release

---

## 5. Photo Reports

### Taking Photos

1. Open a task on your mobile device
2. Tap the camera icon
3. Take a photo -- the app automatically captures:
   - **Geotag** (GPS coordinates)
   - **Timestamp** (date and time)
   - **Task/phase association**

### Photo Storage

- Photos are uploaded to MinIO (S3-compatible storage)
- Automatic sync when the device comes online (offline-first)
- Each photo is linked to its task and project

### Progress Updates

When photos are attached to a task:
- The project's overall progress is automatically recalculated
- Photos are visible in the Client Portal (P1 release)

---

## 6. Real-Time Budget

### Budget Dashboard

Each project has a budget view showing:

| Metric | Description |
|--------|-------------|
| **Planned Budget** | Total from the approved estimate |
| **Actual Spending** | Sum of recorded expenses |
| **Deviation** | Actual - Planned (absolute and percentage) |
| **Forecast** | AI-projected final cost based on current burn rate |

### AI Alerts

The system generates alerts when:
- Actual spending exceeds planned by > 10%
- A specific line item exceeds its budget by > 15%
- Projected final cost exceeds the approved estimate
- Tasks are overdue and accumulating labor costs

Alerts are delivered as:
- In-app notifications
- Push notifications (P1 release)
- Morning digest email (P1 release)

### Budget Data

- Aggregated via PostgreSQL materialized views + Redis cache (TTL 300 seconds)
- Dashboard loads in < 2 seconds (P95)

---

## 7. Billing and Subscriptions

### Plans

| Plan | Price/Month | Included |
|------|------------|----------|
| **Free** | 0 | 1 project, 3 AI estimates/month |
| **Starter** | 2,990 RUB | 5 projects, 30 AI estimates/month |
| **Professional** | 9,900 RUB | 20 projects, unlimited estimates, client portal |
| **Enterprise** | 49,900 RUB | Unlimited projects, API access, priority support |

- 14-day free trial on all paid plans
- Additional AI estimates beyond the plan limit: 490 RUB per estimate

### Payment Methods (via YuKassa)

- Bank cards (Visa, Mastercard, Mir)
- SBP (Instant Payment System)
- YuMoney wallet
- Recurring (auto-renewal)

### Authentication

- Registration with email + password
- JWT tokens in httpOnly cookies (RS256)
- Access token: 15-minute lifetime
- Refresh token: 7-day lifetime

---

## 8. Roles and Permissions

| Role | Dashboard | Create Tasks | Complete Tasks | Manage Budget | AI Estimates | Billing |
|------|:---------:|:------------:|:--------------:|:-------------:|:------------:|:-------:|
| **Admin** | Full | Yes | Yes | Yes | Yes | Yes |
| **Manager** | Full | Yes | Yes | View | Yes | No |
| **Foreman (Prorab)** | Own projects | Yes | No (review only) | View | Yes | No |
| **Worker** | Own tasks | No | No | No | No | No |
| **Client** | Portal only | No | No | View | No | No |

- Roles are assigned by admins only (not selectable during registration -- prevents privilege escalation)
- Row-level security in PostgreSQL ensures tenant isolation
