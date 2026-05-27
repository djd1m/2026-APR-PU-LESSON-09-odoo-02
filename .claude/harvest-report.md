# Harvest Report: СтройУправ

**Date:** 2026-05-27
**Mode:** quick
**Source Project:** СтройУправ (Odoo 17 ERP for construction/renovation)

## Extracted Artifacts

### Pattern 1: JWT in httpOnly Cookies (not localStorage)

- **Category:** Security Pattern
- **Maturity:** 🟡 Beta (validated in 2 projects)
- **Provenance:** СтройУправ auth-billing (`custom-addons/su_billing/controllers/auth.py`), outschool-01 Phase 4 finding
- **Decontextualized:** Store JWT access tokens (short TTL, e.g. 15 min) and refresh tokens (longer TTL, e.g. 7 days) exclusively in httpOnly cookies with `Secure=True` and `SameSite=Strict`. Never store tokens in localStorage or sessionStorage. localStorage is accessible to any JavaScript running on the page, meaning a single XSS vulnerability leaks all tokens. httpOnly cookies are invisible to JS; SameSite=Strict prevents CSRF. Mobile apps that cannot use cookies need a separate auth flow (e.g., PKCE).
- **Reuse:** Any web application with JWT-based authentication serving browser clients.

---

### Pattern 2: Webhook HMAC Verification (constant-time)

- **Category:** Security Pattern
- **Maturity:** 🟢 Production (standard practice, validated in Phase 4)
- **Provenance:** СтройУправ ЮKassa webhook handler (`custom-addons/su_billing/controllers/webhook.py`), ADR-007
- **Decontextualized:** Every incoming webhook MUST be verified via HMAC-SHA256 signature before processing. Use a constant-time comparison function (e.g., Python's `hmac.compare_digest()`, Node's `crypto.timingSafeEqual()`) to prevent timing attacks. The webhook secret MUST come from an environment variable, and the application MUST crash on startup if the secret is missing. Additionally, implement idempotent processing (deduplicate by payment/event ID) and replay protection via a timestamp window (e.g., reject events older than 5 minutes). Without HMAC verification, any attacker can forge webhook payloads to fake payments or trigger unauthorized state changes.
- **Reuse:** Any application receiving webhooks from payment providers (Stripe, ЮKassa, PayPal), CI/CD systems, or third-party services.

---

### Pattern 3: AI Provider Switch via env var (no proxy)

- **Category:** Architecture Pattern
- **Maturity:** 🟡 Beta (validated in 1 project, ADR-003)
- **Provenance:** СтройУправ AI service (`services/fastapi-ai/app/services/ai_client.py`), ADR-002, ADR-003
- **Decontextualized:** When multiple AI providers offer OpenAI-compatible APIs, use the official OpenAI SDK directly with `base_url` loaded from an environment variable (e.g., `AI_BASE_URL`). Do NOT add a proxy layer (LiteLLM, custom router) unless you genuinely need 10+ providers with incompatible APIs. A proxy adds latency, memory overhead, and another failure point. Switching providers becomes a one-line env var change with zero code modifications. Tradeoff: no automatic failover — implement retry logic in the client if needed.
- **Reuse:** Any project using 2-3 AI providers that all expose OpenAI-compatible endpoints (OpenAI, Azure OpenAI, Cloud.ru, Groq, Together, etc.).

---

### Pattern 4: Decimal for Money (never Float)

- **Category:** Coding Pattern
- **Maturity:** 🟢 Production (industry standard, validated in Phase 4 of 2 projects)
- **Provenance:** СтройУправ coding-style rules, ADR-006, outschool-01 Phase 4 finding
- **Decontextualized:** All monetary values MUST use fixed-point decimal types, never floating-point. In Python use `Decimal` from the `decimal` module; in databases use `DECIMAL(15,2)` or `NUMERIC(15,2)` (never `REAL` or `DOUBLE PRECISION`); in ORMs use the monetary field type (e.g., Odoo `fields.Monetary`). When converting from other types, always go through string: `Decimal(str(value))`, never `Decimal(float_value)` which preserves the float's imprecision. `Float(0.1 + 0.2) = 0.30000000000000004` — on a 3M currency estimate, this produces errors of thousands of units. Non-money quantities (area, count) may use float with explicit precision (e.g., `digits=(16,4)`).
- **Reuse:** Any application that handles financial calculations, invoices, estimates, billing, or accounting.

---

### Pattern 5: File Upload Validation (MIME + magic bytes)

- **Category:** Security Pattern
- **Maturity:** 🟡 Beta (validated in 1 project)
- **Provenance:** СтройУправ photo upload validator (`custom-addons/su_photo/services/file_validator.py`)
- **Decontextualized:** File upload validation must use a defense-in-depth approach with multiple layers: (1) Check file size against a hard limit before any processing. (2) Detect MIME type from magic bytes (first 2048 bytes via libmagic), NOT from the file extension — extensions are trivially spoofable. (3) Validate detected MIME against an explicit allowlist (not a blocklist). (4) Additionally check filename extension against a blocklist of executable types (.exe, .sh, .bat, .py, .js, .php, etc.). (5) Sanitize filenames to remove path traversal characters (`..`, `/`, `\`) and limit length. If libmagic is unavailable, fall back to extension-based detection but log a warning — this is a degraded security posture. Structure the validator as a standalone function that returns the detected MIME type or raises an error.
- **Reuse:** Any application accepting file uploads from users — photo reports, document management, profile avatars, attachments.

---

### Pattern 6: Registration Role Hardcoding (prevent escalation)

- **Category:** Security Pattern
- **Maturity:** 🟢 Production (proven #1 security finding across multiple projects)
- **Provenance:** СтройУправ auth controller (`custom-addons/su_billing/controllers/auth.py`), ADR-010, outschool-01 Phase 4
- **Decontextualized:** In user registration endpoints, NEVER accept a role or permission level from the request body. Hardcode the default role (typically the lowest-privilege role) directly in the controller. Any `role` field in the request payload must be silently ignored. LLM-generated code is particularly prone to this vulnerability because it copies DTO fields from the specification without adding restrictions, allowing `POST /auth/register` with `role: "admin"` to create admin accounts. Role elevation should only be possible through an admin panel or a dedicated admin-only endpoint. This is consistently the #1 security finding in LLM-assisted projects.
- **Reuse:** Any application with role-based access control and a self-registration endpoint.

---

### Pattern 7: Crash on Missing Secrets (no fallbacks)

- **Category:** Security Pattern / Operations Pattern
- **Maturity:** 🟢 Production (standard practice)
- **Provenance:** СтройУправ auth.py, webhook.py, security rules
- **Decontextualized:** When a secret (JWT signing key, webhook secret, API key, database password) is required at runtime, the application MUST crash immediately on startup if the environment variable is not set. Never provide a hardcoded fallback, a "dev mode" default, or a convenience value. The crash should be loud — log at CRITICAL level and raise a RuntimeError (or equivalent) with a message naming the exact missing variable. LLM-generated code frequently adds "convenience" fallbacks like `os.environ.get('SECRET', 'dev-secret-change-me')` which create production vulnerabilities. Use separate API keys per environment (dev/staging/prod). The `.env` file must never be committed to version control.
- **Reuse:** Every application that uses secrets. Universal pattern.

---

### Pattern 8: Odoo Module Naming Convention (su_ prefix)

- **Category:** Coding Pattern
- **Maturity:** 🟡 Beta (project-specific convention, generalizable)
- **Provenance:** СтройУправ coding-style rules (`custom-addons/su_*`)
- **Decontextualized:** When building custom modules on top of a framework that uses a shared namespace (Odoo, WordPress plugins, Django apps), prefix all custom modules with a short project identifier (2-4 chars). Apply the prefix consistently across all layers: directory name (`prefix_module`), model class (`PrefixModel`), database model name (`prefix.model`), table name (`prefix_table`), view IDs, and security groups. This prevents naming collisions with third-party addons and makes it immediately clear which code is custom vs. framework-provided. The prefix should be short enough to not burden readability but unique enough to avoid collisions. Method naming should follow framework conventions (e.g., `action_<verb>` for button handlers, `_compute_<field>` for computed fields).
- **Reuse:** Any project extending a modular framework (Odoo, Magento, WordPress, Shopify apps).

---

### Pattern 9: Phase 4 Review Enforcement (artifact verification)

- **Category:** Process Pattern
- **Maturity:** 🟡 Beta (validated across 2 projects, documented bug)
- **Provenance:** Feature lifecycle rules (`feature-lifecycle.md`), confirmed skipping in HopperRU and outschool-01
- **Decontextualized:** When using an LLM-driven development pipeline with distinct phases (plan, validate, implement, review), the review phase is consistently skipped in autonomous mode. The LLM optimizes for "done" over "done correctly" and terminates after implementation. Mitigation: define an explicit artifact checklist that must exist before a feature is marked complete. The review artifact (e.g., `review-report.md`) must be the LAST artifact created. After pipeline completion, programmatically verify all expected artifacts exist. If any are missing, re-run only the missing phase(s). Track review completion status in the feature roadmap. Phase 4 review has caught critical findings that Phase 3 implementation always misses: privilege escalation, hardcoded secret fallbacks, tokens in localStorage, float for money, webhook without HMAC, dead code.
- **Reuse:** Any LLM-assisted development workflow with multi-phase pipelines.

---

### Pattern 10: autopush.cjs Last in Stop Hooks

- **Category:** Process Pattern
- **Maturity:** 🟢 Production (proven ordering bug)
- **Provenance:** Git workflow rules (`git-workflow.md`), memory from prior session
- **Decontextualized:** When using a sequential hook system where multiple hooks run on the same trigger (e.g., "on stop" or "post-commit"), any hook that pushes to a remote repository MUST be the last hook in the execution order. If an auto-push hook runs before auto-commit hooks, the auto-committed changes will not be included in the push, requiring a separate manual push. This is a general principle: in any sequential hook chain, the "publish" or "broadcast" step must always be the final step, after all "prepare" or "stage" steps have completed. Verify hook ordering after any configuration change.
- **Reuse:** Any tool or CI/CD system with sequential hook execution (Claude Code, Husky, Git hooks, GitHub Actions job ordering).

---

### Pattern 11: AI Input Sanitization (prompt injection defense)

- **Category:** Security Pattern
- **Maturity:** 🟡 Beta (validated in 1 project)
- **Provenance:** СтройУправ AI client (`services/fastapi-ai/app/services/ai_client.py`)
- **Decontextualized:** When user-provided text is passed to an LLM as part of a prompt, apply input sanitization to strip common prompt injection patterns before sending. Build a regex filter that catches phrases like "ignore previous instructions", "you are now", "system:", "assistant:", "forget everything", and format-specific markers (`[INST]`, `<|im_start|>`). This is defense-in-depth — it will not stop sophisticated attacks, but it catches the most common injection attempts. Apply sanitization as a dedicated function at the boundary between user input and AI client, not inline. Collapse whitespace after stripping. Log sanitization events for monitoring. Combine with output validation (parse expected JSON/structured format, reject free-form responses).
- **Reuse:** Any application that passes user input to LLM APIs — chatbots, AI-assisted tools, content generation.

---

## Summary

- **Total artifacts:** 11
- **Categories:** security (6), coding (2), architecture (1), process (2)
- **Average maturity:** 🟡 Beta
- **Cross-project validated:** Patterns 1, 2, 4, 6, 7, 9 (confirmed in 2+ projects or industry standard)
- **Key theme:** LLM-generated code has predictable security blind spots (localStorage tokens, role escalation via DTO, secret fallbacks, float for money, missing HMAC). These patterns form a reusable security checklist for any LLM-assisted project.
