# Validation Report: Mobile App (PWA) — F06

**Date:** 2026-05-27
**Validator:** requirements-validator (automated)
**Verdict:** READY

---

## 1. Scoring Summary

| Dimension | Score | Weight | Weighted |
|-----------|:-----:|:------:|:--------:|
| Completeness | 85 | 25% | 21.25 |
| Consistency | 90 | 20% | 18.00 |
| Testability | 80 | 15% | 12.00 |
| Security | 85 | 20% | 17.00 |
| Feasibility | 80 | 20% | 16.00 |
| **AVERAGE** | | | **84.25** |

**Verdict: READY** (average >= 70, no blockers)

---

## 2. Dimension Analysis

### 2.1 Completeness (85/100)

**Strengths:**
- All 5 SPARC documents present and non-empty
- FR-MOB-01 through FR-MOB-06 map directly to PRD F06 requirements
- Offline sync strategy clearly defined (server wins for data, append for photos)
- Service Worker caching strategies specified per resource type
- Push notification events and priorities listed

**Gaps (non-blocking):**
- [ ] No explicit mention of `beforeinstallprompt` handling for install banner UX
- [ ] Photo compression algorithm (Canvas API quality settings) could be more specific about target dimensions
- [ ] No mention of Background Sync API registration (Chrome-specific optimization)

### 2.2 Consistency (90/100)

**Strengths:**
- Conflict resolution consistently documented as "server wins" across all docs
- IndexedDB schema consistent between pseudocode and architecture
- API endpoints referenced match existing Task/Photo API contracts from Specification.md
- Security requirements (no localStorage tokens) consistent with NFR-SEC-01 and Architecture.md

**Gaps (non-blocking):**
- [ ] Pseudocode references `/api/v1/projects/*/tasks` but Odoo routes use `/web/dataset/` — need to clarify which API surface the PWA targets (REST vs Odoo RPC)

### 2.3 Testability (80/100)

**Strengths:**
- Clear acceptance criteria with GIVEN/WHEN/THEN format
- Testing strategy covers unit, integration, and server-side
- Specific tools mentioned (Jest, Playwright, pytest)
- Edge cases well-documented with expected behaviors

**Gaps (non-blocking):**
- [ ] No Lighthouse CI integration specified for PWA score tracking
- [ ] Manual tests listed but no automated PWA-specific CI pipeline

### 2.4 Security (85/100)

**Strengths:**
- Explicit prohibition of tokens in IndexedDB/localStorage
- Cache purge on logout documented
- VAPID keys from env vars (not hardcoded)
- CSP header updates mentioned
- Service Worker scope restricted to same-origin

**Gaps (non-blocking):**
- [ ] No mention of IndexedDB data sensitivity classification (what data is cached and is it PII?)
- [ ] No explicit mention of clearing SW caches on user switch (multi-user device scenario)

### 2.5 Feasibility (80/100)

**Strengths:**
- PWA is well-supported on target platforms (Android Chrome, iOS Safari 16.4+)
- Technology choices are standard (Service Worker, IndexedDB, Web Push)
- No custom crypto or complex algorithms
- Integrates with existing Odoo/Nginx infrastructure

**Gaps (non-blocking):**
- [ ] iOS Safari PWA limitations acknowledged but push notification fallback for older iOS not specified
- [ ] IndexedDB storage limits vary by browser/device — no explicit quota management strategy beyond error handling

---

## 3. Blockers

**None identified.**

---

## 4. Recommendations

| Priority | Recommendation | Impact |
|----------|---------------|--------|
| Medium | Clarify API surface: REST (`/api/v1/`) vs Odoo RPC (`/web/dataset/`) for offline sync | Affects SW fetch interception patterns |
| Low | Add `beforeinstallprompt` event handling for A2HS banner | Better install UX |
| Low | Define IndexedDB quota management (eviction strategy when quota low) | Prevents data loss on storage-constrained devices |
| Low | Add Lighthouse CI check to CI/CD pipeline | Track PWA score regression |

---

## 5. BDD Scenarios

```gherkin
Feature: PWA Offline Task Management

  Scenario: Create task while offline
    Given the PWA is installed and user is authenticated
    And the device is offline
    When the user creates a task "Штукатурка стен"
    Then the task is saved to IndexedDB sync_queue
    And a toast shows "Сохранено офлайн. Будет отправлено при подключении."

  Scenario: Sync tasks when back online
    Given the user has 3 pending tasks in sync_queue
    And the device comes online
    Then all 3 tasks are sent to the server within 60 seconds
    And a notification shows "Данные синхронизированы (3 элементов)"

  Scenario: Server wins on conflict
    Given the user edited task "Демонтаж" offline
    And another user updated the same task on server
    When the device comes online and sync runs
    Then the server version is applied locally
    And user sees "Задача обновлена на сервере"

  Scenario: Photo queued offline and uploaded on reconnect
    Given the device is offline
    When the user takes a photo for task "Электрика"
    Then the photo is compressed and stored in photos_queue
    And an indicator shows "Ожидает загрузки"
    When the device comes online
    Then the photo is uploaded to the server
    And the indicator is removed

  Scenario: Push notification opens relevant task
    Given the PWA is installed with push permissions
    When a push notification arrives for task assignment
    And the user clicks the notification
    Then the PWA opens to the assigned task view
```

---

## 6. Conclusion

The mobile-pwa feature specification is **READY for implementation**. All core
requirements from PRD F06 are addressed. The identified gaps are non-blocking
and can be resolved during implementation. The security posture is strong
with explicit token storage prohibitions aligned with the project's security
architecture.
