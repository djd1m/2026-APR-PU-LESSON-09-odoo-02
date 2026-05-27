---
description: >
  Replicate pipeline — полный цикл подготовки проекта к Vibe Coding.
  Генерирует SPARC документацию, валидирует, создаёт project-specific toolkit.
  $ARGUMENTS: описание продукта/идеи или название компании для reverse engineering.
---

# /replicate $ARGUMENTS

## Role

Координатор подготовки к Vibe Coding. Генерируешь всё для старта проекта
в Claude Code — прямо в текущем репозитории, без zip-архивов.

## Target Architecture (Constraints)

Все проекты создаются под эту целевую архитектуру:

| Аспект | Решение |
|--------|---------|
| **Архитектура** | Distributed Monolith в Monorepo |
| **Контейнеризация** | Docker + Docker Compose |
| **Инфраструктура** | VPS (AdminVPS/HOSTKEY) |
| **Деплой** | Docker Compose на VPS (direct deploy) |
| **AI Integration** | MCP серверы |

## Skills (loaded from .claude/skills/)

All skills are available locally. Read their SKILL.md when needed:

| Skill | Path | Phase |
|-------|------|-------|
| reverse-engineering-unicorn | `.claude/skills/reverse-engineering-unicorn/SKILL.md` | Phase 0 |
| sparc-prd-mini | `.claude/skills/sparc-prd-mini/SKILL.md` | Phase 1 |
| explore | `.claude/skills/explore/SKILL.md` | Phase 1 (dependency) |
| goap-research-ed25519 | `.claude/skills/goap-research-ed25519/SKILL.md` | Phase 1 (dependency) |
| problem-solver-enhanced | `.claude/skills/problem-solver-enhanced/SKILL.md` | Phase 1 (dependency) |
| requirements-validator | `.claude/skills/requirements-validator/SKILL.md` | Phase 2 |
| cc-toolkit-generator-enhanced | `.claude/skills/cc-toolkit-generator-enhanced/SKILL.md` | Phase 3 |
| brutal-honesty-review | `.claude/skills/brutal-honesty-review/SKILL.md` | Phase 4 (/feature) |

**IMPORTANT (Claude Code adaptation):**
- Skills reference `view("/mnt/skills/user/...")` paths from claude.ai
- In Claude Code, replace ALL such references with `.claude/skills/[name]/SKILL.md`
- When sparc-prd-mini calls `view("/mnt/skills/user/explore/SKILL.md")`, read `.claude/skills/explore/SKILL.md` instead
- When sparc-prd-mini calls `view("/mnt/skills/user/goap-research/SKILL.md")`, read `.claude/skills/goap-research-ed25519/SKILL.md` instead

## Pipeline

```
INPUT → [PRODUCT DISCOVERY] → PLANNING → VALIDATION → TOOLKIT → FINALIZE
         (optional)            sparc-prd   requirements  cc-toolkit  commit
                               -mini       -validator    -generator  & report
```

**Note:** sparc-prd-mini v2 already includes Explore, Research, and Solve phases
internally via skill references. The coordinator does NOT duplicate these phases.

## Alternative entry: starting from existing technical documentation

If the user already has technical documentation for the project (tech spec,
architecture docs, API spec, design docs, etc.), the pipeline supports
**skipping Phase 0 entirely** and feeding the user's existing docs into
Phase 1 as pre-filled context.

### Trigger detection (any of these in user input)

Switch to this alternative flow when the user input contains:
- A path reference: "use my docs in `docs/existing/`", "my tech specs are in `<path>`"
- An explicit skip request: "skip discovery", "skip Phase 0"
- A statement of available docs: "I already have technical documentation"
- The semantic flag: `/replicate --from-docs <path>` (or `--skip-discovery`)

### Recommended setup

The user should place their existing docs in a project-local subfolder
(conventionally `docs/existing/` or `docs/source/`) so they're discoverable
but distinct from generated SPARC outputs.

### Modified pipeline flow when triggered

- **Phase 0** (Product Discovery): SKIPPED entirely (no reverse-engineering-unicorn invocation)
- **Phase 1** (sparc-prd-mini): MODIFIED
  - Run in **AUTO mode** — do NOT ask interactive clarification questions
  - SKIP internal sub-phases Explore / Research / Solve (their job is to
    generate the answers that already exist in user docs)
  - READ all files in user-provided path as pre-filled context
  - Generate the 11 standardized SPARC documents in `docs/`, mapping content
    from existing docs to appropriate slots (PRD, Solution_Strategy,
    Specification, Pseudocode, Architecture, Refinement, Completion,
    Research_Findings, Final_Summary, C4_Diagrams, ADR)
  - For SPARC slots without source content in existing docs, mark with a
    `[GAP: needs <description>]` placeholder rather than asking the user
- **Phase 2** (validation): runs UNCHANGED (validates the generated SPARC docs)
- **Phase 3** (toolkit generation): runs UNCHANGED
- **Phase 4** (finalize): runs UNCHANGED

### Three sub-paths the user may prefer

| Sub-path | When | Skills invoked |
|---|---|---|
| **A. Full /replicate with override directives** | Have tech docs, want full pipeline + toolkit + scaffold | sparc-prd-mini (AUTO) → requirements-validator → cc-toolkit-generator-enhanced |
| **B. Invoke sparc-prd-mini skill directly** | Want only the 11 SPARC docs, no toolkit/scaffold | sparc-prd-mini (AUTO) only |
| **C. Rename existing docs to SPARC slot names + invoke validator only** | Existing docs already SPARC-shaped | requirements-validator only |

### Caveats (always surface to the user)

- Existing docs may not cover all 11 SPARC slots — expect `[GAP: ...]` markers
- Validation may flag user stories as "not negotiable/testable" if existing
  docs aren't INVEST/SMART-shaped — this is a real signal, not a bug
- Architectural constraints (pattern, containers, infra, deploy, AI integration)
  must be passed explicitly if not present in existing docs (use the constraints
  block from "Phase 1: PLANNING" below)

### Verification after completion

```bash
npx @dzhechkov/p-replicator verify
```
Should report pre-shipped contract OK + post-/replicate hints showing the
generated SPARC docs and (if Phase 3+4 ran) the project-specific artifacts.

### See also: existing-project feature workflow (Mode 2)

If the user already has a working project (stack, PRD, CLAUDE.md, etc. all
defined) and just wants to **add new features** with the same SPARC-mini
validation cycle — they should use `/feature` (NOT `/replicate`):

```bash
cd existing-project
npx @dzhechkov/p-replicator init      # idempotent — preserves CLAUDE.md
claude
/feature add-stripe-payments          # 4-phase: PLAN → VALIDATE → IMPLEMENT → REVIEW
```

See `.claude/commands/feature.md` ("Use case: existing project") and
`.claude/rules/feature-lifecycle.md` ("Entry modes" → "Mode 2") for the full
spec. This Mode 2 workflow is parallel to /replicate's "Alternative entry"
above, but applies to ad-hoc feature additions rather than full project bootstrap.

## Execution

### Start

1. Briefly explain the phases (4 main + 1 optional)
2. Mention the target architecture (distributed monolith + Docker на VPS)
3. Determine project type → is Product Discovery needed?
4. Begin with the relevant phase

### Phase 0: PRODUCT DISCOVERY (optional)

**Gate — when to activate:**
- New product / startup / SaaS → **activate**
- Competitors to analyze → **activate**
- Internal tool / experiment → **skip**
- **Existing technical documentation provided** → **skip** (see "Alternative entry" below)

Read the skill: `.claude/skills/reverse-engineering-unicorn/SKILL.md`

**Mode:** QUICK (sufficient for informing PRD)

**Selected modules:**

| Module | When needed | Output for PRD |
|--------|------------|----------------|
| M2: Product & Customers | Always | JTBD, Value Prop, segments |
| M3: Market & Competition | Always | TAM/SAM, competitors, Blue Ocean |
| M4: Business & Finance | If monetization | Unit economics |
| M5: Growth Engine | If B2C/PLG | Channels, integrations |

**Output:** Product Discovery Brief → passed as pre-filled context to Phase 1

**Checkpoint:**
```
═══════════════════════════════════════════════════════════════
✅ PHASE 0: PRODUCT DISCOVERY
[Summary from brief]
⏸️ "ок" — next | "превью discovery" — show brief
═══════════════════════════════════════════════════════════════
```

### Phase 1: PLANNING

Read the skill: `.claude/skills/sparc-prd-mini/SKILL.md`

**sparc-prd-mini v2 runs 8 internal phases:**
- Phase 0: Explore → explore skill (read from `.claude/skills/explore/SKILL.md`)
- Phase 1: Research → goap-research-ed25519 skill (read from `.claude/skills/goap-research-ed25519/SKILL.md`)
- Phase 2: Solve → problem-solver-enhanced skill (read from `.claude/skills/problem-solver-enhanced/SKILL.md`)
- Phases 3-7: Specification, Pseudocode, Architecture, Refinement, Completion

**Pass context to the skill:**

```yaml
Architecture Constraints:
  pattern: "Distributed Monolith (Monorepo)"
  containers: "Docker + Docker Compose"
  infrastructure: "VPS (AdminVPS/HOSTKEY)"
  deploy: "Docker Compose direct deploy (SSH / CI pipeline)"
  ai_integration: "MCP servers"

Product Context: # From Phase 0 (if applicable)
  target_segments: [from JTBD]
  key_competitors: [from competitive matrix]
  differentiation: [from Blue Ocean]
  monetization: [from Unit Economics]

Security Pattern: # If external integrations
  api_keys_input: "UI Settings > Integrations"
  storage: "Encrypted IndexedDB (AES-GCM 256-bit)"
  key_derivation: "PBKDF2 from user password"
  server_side: "No key storage on backend"
```

**Mode:** MANUAL (checkpoint at each phase inside sparc-prd-mini)

**Output location:** `docs/` directory (NOT `/output/` — write directly into the project)

Write all 11 documents to `docs/`:
- `docs/PRD.md`
- `docs/Solution_Strategy.md`
- `docs/Specification.md`
- `docs/Pseudocode.md`
- `docs/Architecture.md`
- `docs/Refinement.md`
- `docs/Completion.md`
- `docs/Research_Findings.md`
- `docs/Final_Summary.md`
- `docs/C4_Diagrams.md` (if applicable)
- `docs/ADR.md` (if applicable)

Git commit: `docs: SPARC documentation for [project-name]`

**Checkpoint:**
```
═══════════════════════════════════════════════════════════════
✅ PHASE 1: PLANNING (SPARC DOCUMENTATION)
Created [N] documents in docs/
⏸️ "ок" — next to validation | "превью [filename]" — show file
═══════════════════════════════════════════════════════════════
```

### Phase 2: VALIDATION

Read the skill: `.claude/skills/requirements-validator/SKILL.md`

**Goal:** Verify all documentation for completeness, testability, and implementation readiness.

**Strategy: Swarm of Validation Agents**

| Agent | Scope | Criteria |
|-------|-------|----------|
| `validator-stories` | PRD → User Stories | INVEST criteria, score ≥70 |
| `validator-acceptance` | Stories → AC | SMART criteria, testability |
| `validator-architecture` | Architecture.md | Target constraints, completeness |
| `validator-pseudocode` | Pseudocode.md | Story coverage, implementability |
| `validator-coherence` | Cross-document | Consistency, no contradictions |

**Process (iterative, max 3 iterations):**

```
1. ANALYZE — parallel validator agents (use Task tool)
2. AGGREGATE — Gap Register + Blocked/Warning items
3. FIX — resolve gaps in documentation
4. RE-VALIDATE — re-check fixes
↻ Until: no BLOCKED (≥50), average ≥70, no contradictions
```

**BDD Scenarios Generation:**
- Happy path (1-2), Error handling (2-3), Edge cases (1-2), Security
- Save as `docs/test-scenarios.md`

**Save validation report:** `docs/validation-report.md`

Git commit: `docs: validation report and BDD scenarios`

**Exit Criteria:**

| Verdict | Conditions | Action |
|---------|-----------|--------|
| 🟢 READY | All scores ≥50, average ≥70, no contradictions | → Phase 3 |
| 🟡 CAVEATS | Warnings exist, no blocked, limitations described | → Phase 3 with notes |
| 🔴 NEEDS WORK | Blocked items exist | → Return to Phase 1 |

**Checkpoint:**
```
═══════════════════════════════════════════════════════════════
✅ PHASE 2: VALIDATION COMPLETE
Verdict: [🟢/🟡/🔴]
Average Score: XX/100
Iterations: N/3
⏸️ "ок" — generate toolkit | "превью validation" — show report
═══════════════════════════════════════════════════════════════
```

### Phase 3: TOOLKIT GENERATION

Read the skill: `.claude/skills/cc-toolkit-generator-enhanced/SKILL.md`

**Goal:** Generate project-specific Claude Code instruments IN-PLACE.

**IMPORTANT (Claude Code adaptation, post v1.4):**
- Scan `docs/` directory for SPARC documents (NOT `/mnt/user-data/uploads/`)
- Generate files IN-PLACE into the project (NOT into output directory)
- **Pre-shipped by `npx p-replicator init` — do NOT overwrite or regenerate:**
  - All 10 skills in `.claude/skills/`
  - All 11 commands: `/replicate`, `/harvest`, `/start`, `/plan`, `/feature`, `/go`, `/run`, `/next`, `/myinsights`, `/docs`, `/deploy`
  - All 5 rules: `replicate-pipeline`, `skill-interface-protocol`, `git-workflow`, `insights-capture`, `feature-lifecycle`
  - All 4 pipeline agents: `replicate-coordinator`, `product-discoverer`, `doc-validator`, `harvest-coordinator`
  - `.claude/settings.json` + cross-platform Node hook scripts in `.claude/hooks/`
- Phase 3 generates ONLY project-specific artifacts derived from SPARC docs (see below).

**Generate these project-specific files:**

**1. Enhance CLAUDE.md** (root) with project-specific content:
- Project overview from PRD.md
- Architecture from Architecture.md
- Tech stack decisions
- Parallel execution strategy
- Available agents/skills/commands list (reference pre-shipped + project-generated)
- Development insights section
- Feature lifecycle section

**2. Project-specific Agents (`.claude/agents/`):**
- `planner.md` — feature planning with algorithm templates from Pseudocode.md
- `code-reviewer.md` — quality review with edge cases from Refinement.md
- `architect.md` — system design from Architecture.md + Solution_Strategy.md
- Additional agents based on project characteristics

**3. Project-specific Rules (`.claude/rules/`):**
- `security.md` — from Specification.md NFRs
- `coding-style.md` — from Architecture.md tech stack
- `secrets-management.md` — IF external APIs detected
- `testing.md` — from Refinement.md test strategy

**4. Project-specific Skills (`.claude/skills/`):**
- `project-context/` — domain knowledge from Research_Findings.md
- `coding-standards/` — tech-specific patterns from Architecture.md
- `security-patterns/` — IF external APIs (encrypted storage pattern)

**5. Project state:**
- `.claude/feature-roadmap.json` — generated from PRD.md MVP scope
- `.mcp.json` — IF external integrations
- `DEVELOPMENT_GUIDE.md` — step-by-step development lifecycle
- `README.md` — enhanced with project info

**6. Conditional command (only if DDD docs present):**
- `.claude/commands/feature-ent.md` — enterprise feature lifecycle with DDD/ADR/C4

**Verify after Phase 3:**
- Run `npx @dzhechkov/p-replicator verify` to confirm both pre-shipped contract AND post-/replicate artifacts are in place.

Git commit: `feat: Claude Code toolkit for [project-name]`

**Checkpoint:**
```
═══════════════════════════════════════════════════════════════
✅ PHASE 3: TOOLKIT GENERATED
- CLAUDE.md enhanced with project context
- [N] agents + [N] commands + [N] rules generated
- DEVELOPMENT_GUIDE.md created
⏸️ "ок" — finalize | "превью toolkit" — show structure
═══════════════════════════════════════════════════════════════
```

### Phase 4: FINALIZE

**Goal:** Generate scaffold files, commit everything, show summary.

**Generate scaffold files:**

1. `docker-compose.yml` — from Architecture.md services
2. `Dockerfile` — from Architecture.md tech stack
3. `.gitignore` — if not exists
4. `docs/features/` — create empty directory for future features

**Git operations:**
```bash
git add .
git commit -m "chore: initial project setup from SPARC documentation"
```

**Show final summary:**
```
═══════════════════════════════════════════════════════════════
✅ REPLICATE COMPLETE: [project-name]

📁 Project structure:
├── CLAUDE.md                     # Project context
├── DEVELOPMENT_GUIDE.md          # Dev lifecycle guide
├── README.md                     # Quick start
├── docs/                         # [N] SPARC documents
│   ├── validation-report.md      # Validation results
│   ├── test-scenarios.md         # BDD scenarios
│   └── features/                 # For future features
├── .claude/
│   ├── commands/                 # /start, /feature, /plan, /test, /deploy, /myinsights
│   ├── agents/                   # planner, code-reviewer, architect
│   ├── skills/                   # 8 shared + project-specific skills
│   ├── rules/                    # git-workflow, security, coding-style, ...
│   └── settings.json             # Hooks (insights auto-commit)
├── docker-compose.yml            # Scaffold
└── Dockerfile                    # Scaffold

🚀 Next steps:
1. Run /start to bootstrap the project
2. First feature: [recommended from PRD MVP]

💡 Available commands:
- /start         — bootstrap project from docs
- /feature [name] — full feature lifecycle
- /plan [feature] — plan implementation
- /test [scope]   — run/generate tests
- /deploy [env]   — deploy to environment
- /myinsights     — capture development insights
═══════════════════════════════════════════════════════════════
```

## Development Practices (embedded in toolkit)

### 1. Swarm of Agents & Parallel Execution

Include in CLAUDE.md:
```markdown
## Parallel Execution Strategy
- Use `Task` tool for independent subtasks
- Run tests, linting, type-checking in parallel
- For complex features: spawn specialized agents
```

### 2. Client-Side Secrets Management (if external APIs)

**Mandatory pattern for apps with external integrations:**

```
PRINCIPLE: User enters keys via UI → stored encrypted in browser → NEVER sent to backend
```

**Security Implementation:**
- Encryption at Rest: AES-GCM 256-bit (Web Crypto API)
- Key derivation: PBKDF2 from user password (100k+ iterations)
- Storage: IndexedDB for encrypted data, master key only in memory
- Auto-lock after inactivity timeout
- Never: transmit to backend, log, store in plaintext

## Checkpoint Commands

| Command | Action |
|---------|--------|
| `ок` | Next phase |
| `превью [filename]` | View generated file |
| `превью discovery` | Show Product Discovery Brief |
| `превью validation` | Show Validation Report |
| `превью toolkit` | Show toolkit structure |

## Critical Rules

### ALWAYS
- Read skill SKILL.md before executing its logic
- Checkpoint after each phase
- Pass Architecture Constraints to sparc-prd-mini
- Write docs to `docs/` directory (not `/output/`)
- Generate toolkit IN-PLACE (not into separate directory)
- Use existing generic commands/rules (don't regenerate /feature, /myinsights, etc.)

### NEVER
- Don't duplicate explore/research phases — sparc-prd-mini does this internally
- Never skip validation — toolkit is built on validated docs
- Never use base cc-toolkit-generator — only enhanced version
- Don't overwrite template files (generic commands, rules, settings.json)

### CONDITIONAL
- If external APIs → include security-patterns/ skill + secrets-management.md rule
- If new product → start with Phase 0 (Product Discovery)
- If B2B/Enterprise → strengthen security patterns in validation
