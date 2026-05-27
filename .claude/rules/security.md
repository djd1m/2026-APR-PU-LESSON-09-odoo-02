# Security Rules — СтройУправ

## Authentication

### ALWAYS
- Store JWT in **httpOnly cookies** with `Secure`, `SameSite=Strict`
- Use RS256 for JWT signing with key rotation every 90 days
- Crash on startup if `JWT_SECRET_KEY` env var is missing — never use hardcoded fallbacks
- Hash passwords with bcrypt (cost factor >= 12)
- Implement refresh token rotation (one-time use)

### NEVER
- Store tokens in localStorage or sessionStorage (XSS vulnerability)
- Include role/permissions in registration endpoint — role escalation via `POST /auth/register` with `role: "admin"` is the #1 security finding
- Return password hashes in API responses

## Authorization (RBAC)

| Role | Capabilities |
|------|-------------|
| `admin` | Full access, user management, billing |
| `manager` | Projects CRUD, estimates, budgets, brigades |
| `foreman` | Tasks, photos, own brigade's projects only |
| `client` | View-only portal for assigned projects |

### ALWAYS
- Check tenant isolation on every query: `WHERE tenant_id = current_tenant`
- Verify object ownership before update/delete (prevent IDOR)

### NEVER
- Allow cross-tenant data access
- Trust client-side role claims

## Input Validation

### ALWAYS
- Validate and sanitize ALL user inputs server-side
- Use parameterized queries (Odoo ORM, no raw SQL with f-strings)
- Escape HTML in project names, task descriptions (prevent stored XSS)
- Validate file uploads: MIME type, size (20MB photos, 50MB drawings), no executables
- Validate AI prompt inputs — strip injection attempts from estimate descriptions

## Webhooks (ЮKassa)

### ALWAYS
- Verify HMAC signature on every incoming webhook
- Use constant-time comparison for signature verification
- Process webhooks idempotently (deduplicate by `idempotency_key`)

### NEVER
- Process webhook without signature verification

## Data Protection (152-ФЗ)

### ALWAYS
- Keep personal data in Russia (Cloud.ru for AI, VPS in RU datacenter)
- Encrypt at rest (AES-256) and in transit (TLS 1.3)
- Implement data deletion on user request (152-ФЗ right to be forgotten)

### NEVER
- Send personal data to AI providers outside Russia without anonymization
- Log PII in application logs (mask phone numbers, emails)
- Commit `.env` files to git

## Secrets Management

### ALWAYS
- All secrets via environment variables
- Crash on startup if required secrets are missing
- Use separate API keys per environment (dev/staging/prod)

### NEVER
- Hardcode API keys, database passwords, or JWT secrets
- Add "convenience" fallback values for missing secrets

## API Security

### ALWAYS
- Rate limit auth endpoints (5 attempts / 15 min per IP)
- Rate limit AI endpoint (15 RPS per API key)
- Set CORS to specific origins (not `*`)
- Include security headers: `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Strict-Transport-Security`
