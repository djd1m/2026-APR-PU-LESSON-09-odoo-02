# Pseudocode: Onboarding Quiz (F07)

**Feature:** F07 — Onboarding Quiz
**Date:** 2026-05-27

---

## 1. Model: SuOnboarding

```pseudo
CLASS SuOnboarding EXTENDS Model:
    _name = "su.onboarding"
    _description = "Onboarding quiz answers"
    _rec_name = "partner_id"
    _sql_constraints = [
        ("partner_company_uniq",
         "UNIQUE(partner_id, company_id)",
         "One onboarding record per partner per company")
    ]

    FIELDS:
        partner_id:      Many2one("res.partner", required=True)
        company_type:    Selection([repair, contractor, private_master, client])
        object_count:    Selection([1_3, 4_10, 11_50, 50_plus])
        current_tools:   Char          # comma-separated
        biggest_pain:    Selection([budget, deadlines, documents, communication])
        recommended_plan: Selection([free, starter, business, enterprise])
        completed:       Boolean(default=False)
        skipped:         Boolean(default=False)
        completed_at:    Datetime
        company_id:      Many2one("res.company", default=current_company)

    METHOD _compute_recommended_plan(company_type, object_count) -> plan:
        IF company_type == "client":
            RETURN "free"
        IF company_type == "private_master":
            IF object_count IN ("1_3"):
                RETURN "free"
            ELIF object_count == "4_10":
                RETURN "starter"
            ELSE:
                RETURN "business"
        IF company_type == "repair":
            IF object_count == "1_3":
                RETURN "starter"
            ELIF object_count == "4_10":
                RETURN "business"
            ELSE:
                RETURN "enterprise"
        IF company_type == "contractor":
            IF object_count IN ("1_3"):
                RETURN "business"
            ELSE:
                RETURN "enterprise"
        RETURN "starter"  # fallback

    METHOD action_submit(answers_dict):
        VALIDATE all selection values against allowed lists
        WRITE answers to record
        plan = _compute_recommended_plan(company_type, object_count)
        WRITE recommended_plan = plan
        WRITE completed = True, completed_at = now()
        RETURN {plan, dashboard_config}

    METHOD action_skip():
        WRITE skipped = True, completed = True, completed_at = now()
        WRITE recommended_plan = "starter"  # safe default
```

---

## 2. Controller: OnboardingController

```pseudo
CLASS OnboardingController EXTENDS http.Controller:

    ROUTE GET /api/v1/onboarding/status (auth=jwt):
        partner = current_user.partner_id
        record = search su.onboarding WHERE partner_id = partner
                                        AND company_id = current_company
        IF NOT record:
            RETURN {completed: false, needs_quiz: true}
        RETURN {
            completed: record.completed,
            skipped: record.skipped,
            recommended_plan: record.recommended_plan,
            needs_quiz: NOT record.completed
        }

    ROUTE POST /api/v1/onboarding/submit (auth=jwt):
        VALIDATE request body:
            company_type:  MUST be in allowed selections
            object_count:  MUST be in allowed selections
            current_tools: MUST be string, max 500 chars
            biggest_pain:  MUST be in allowed selections
        partner = current_user.partner_id
        record = search_or_create su.onboarding
                 WHERE partner_id = partner AND company_id = current_company
        result = record.action_submit(validated_data)
        RETURN {status: "ok", recommended_plan: result.plan}

    ROUTE POST /api/v1/onboarding/skip (auth=jwt):
        partner = current_user.partner_id
        record = search_or_create su.onboarding
                 WHERE partner_id = partner AND company_id = current_company
        record.action_skip()
        RETURN {status: "ok", skipped: true}
```

---

## 3. View: Wizard-Style Form

```pseudo
FORM "su_onboarding_form":
    HEADER: statusbar showing steps 1-4 + result
    SHEET:
        GROUP "Step 1 — Company Type":
            field company_type (radio buttons, required)
            button "Next" -> step 2
            button "Skip" -> action_skip

        GROUP "Step 2 — Number of Objects":
            field object_count (radio buttons, required)
            button "Back" -> step 1
            button "Next" -> step 3
            button "Skip" -> action_skip

        GROUP "Step 3 — Current Tools":
            field current_tools (checkboxes: Excel, 1C, WhatsApp, Other)
            button "Back" -> step 2
            button "Next" -> step 4
            button "Skip" -> action_skip

        GROUP "Step 4 — Biggest Pain":
            field biggest_pain (radio buttons, required)
            button "Back" -> step 3
            button "Submit" -> action_submit
            button "Skip" -> action_skip

        GROUP "Result" (visible only when completed AND NOT skipped):
            field recommended_plan (readonly, highlighted)
            button "Activate Trial" -> redirect to billing
            button "Continue to Dashboard" -> redirect to home
```

---

## 4. Security Rules

```pseudo
ACCESS RULES for su.onboarding:
    su_foreman:  read own records (partner_id = current_user.partner_id)
    su_manager:  read/write own company records
    su_admin:    full CRUD
    su_client:   read own records
```
