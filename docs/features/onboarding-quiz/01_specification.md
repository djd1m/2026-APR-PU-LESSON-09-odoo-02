# Specification: Onboarding Quiz (F07)

**Feature:** F07 — Onboarding Quiz
**Module:** `su_onboard`
**Status:** Draft
**Date:** 2026-05-27

---

## 1. Overview

4-question wizard-style onboarding quiz presented after first login.
Collects company profile data, personalizes the dashboard layout,
pre-fills task templates, and recommends a pricing plan. Skippable.

---

## 2. Functional Requirements

| ID | Requirement | Priority | Description |
|----|-------------|:--------:|-------------|
| FR-ONB-01 | Quiz — 4 questions | P0 | Q1: Company type (ремонтная компания / генподрядчик / частный мастер / заказчик). Q2: Number of objects (1-3 / 4-10 / 11-50 / 50+). Q3: Current tools (Excel / 1C / WhatsApp / Other — multi-select). Q4: Biggest pain point (бюджеты / сроки / документы / коммуникация). |
| FR-ONB-02 | Personalization | P0 | Based on answers: configure default dashboard widgets, pre-fill task templates matching company type, recommend pricing plan (free/starter/business/enterprise). |
| FR-ONB-03 | Skip | P0 | User can skip quiz at any step. Defaults applied. Quiz can be re-taken from settings. |
| FR-ONB-04 | One-time per user | P0 | Quiz shown only on first login (or until completed/skipped). `completed` boolean on `su.onboarding` record. |
| FR-ONB-05 | Recommended plan display | P0 | After quiz, show recommended plan with CTA to activate trial. No forced subscription change. |

---

## 3. Data Model

### `su.onboarding` (new model)

| Field | Type | Required | Description |
|-------|------|:--------:|-------------|
| `partner_id` | Many2one(`res.partner`) | Yes | One record per partner |
| `company_type` | Selection | No | `repair` / `contractor` / `private_master` / `client` |
| `object_count` | Selection | No | `1_3` / `4_10` / `11_50` / `50_plus` |
| `current_tools` | Char | No | Comma-separated multi-select values |
| `biggest_pain` | Selection | No | `budget` / `deadlines` / `documents` / `communication` |
| `recommended_plan` | Selection | No | `free` / `starter` / `business` / `enterprise` |
| `completed` | Boolean | No | True when quiz finished or skipped |
| `skipped` | Boolean | No | True if user skipped without answering |
| `completed_at` | Datetime | No | Timestamp of completion/skip |
| `company_id` | Many2one(`res.company`) | Yes | Multi-tenant isolation |

---

## 4. API Endpoints (Odoo Controllers)

| Method | Route | Auth | Description |
|--------|-------|------|-------------|
| GET | `/api/v1/onboarding/status` | JWT | Check if quiz completed for current user |
| POST | `/api/v1/onboarding/submit` | JWT | Submit all 4 answers, compute recommendation |
| POST | `/api/v1/onboarding/skip` | JWT | Mark quiz as skipped, apply defaults |

---

## 5. Plan Recommendation Logic

| Company Type | Object Count | Recommended Plan |
|-------------|-------------|-----------------|
| `client` | any | `free` |
| `private_master` | `1_3` | `free` |
| `private_master` | `4_10` | `starter` |
| `private_master` | `11_50`+ | `business` |
| `repair` | `1_3` | `starter` |
| `repair` | `4_10` | `business` |
| `repair` | `11_50`+ | `enterprise` |
| `contractor` | any `1_3` | `business` |
| `contractor` | `4_10`+ | `enterprise` |

---

## 6. Non-Functional Requirements

| Category | Requirement |
|----------|-------------|
| Performance | Quiz submit < 300 ms (P95) |
| Security | All endpoints require JWT auth. Company_id filter on all queries. |
| Validation | Server-side validation of all selection values. Reject unknown values. |
| Idempotency | Re-submitting quiz overwrites previous answers (upsert by partner_id). |
