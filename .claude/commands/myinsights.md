---
description: Capture and recall development insights. Append a new insight to `.claude/insights/index.md` with structured fields (problem, solution, tags). Auto-injected into context on SessionStart for relevant tasks.
argument-hint: '[recall <query> | <free-form insight>]'
---

# /myinsights $ARGUMENTS

## Purpose

Build a project-local knowledge base of "грабли" (rakes) — errors, workarounds,
discoveries — so they don't have to be re-learned. Insights are auto-loaded
into Claude Code context on each session start (via `SessionStart` hook in
`.claude/settings.json`) when their tags match the current task.

## Modes

### Capture (default)

Run `/myinsights` with a free-form description, or no arguments to be prompted.

Process:
1. Ask 3 short questions (or extract from `$ARGUMENTS`):
   - **Problem** — what went wrong / surprised you
   - **Solution** — what fixed it
   - **Tags** — keywords for future recall
2. Append entry to `.claude/insights/index.md`:

```markdown
## <ISO date> — <short title>

**Tags:** <comma-separated>

**Problem:**
<1-3 sentences>

**Solution:**
<1-5 sentences with code if relevant>

**References:** <file:line | commit hash>

---
```

3. Auto-commit (Stop hook handles this if `.claude/settings.json` is in place).

### Recall

`/myinsights recall <query>`:

1. Read `.claude/insights/index.md`
2. Filter entries whose tags or text match `<query>` (case-insensitive)
3. Print top 5 matches with relevance score

## Storage

`.claude/insights/index.md` — chronological log, Markdown format. One file per
project to keep recall trivial.

## Auto-injection on SessionStart

The default `.claude/settings.json` configures `node .claude/hooks/session-insights.cjs`
which: (1) reads recent insights, (2) prints them to stdout, (3) Claude Code
captures stdout and injects into the initial context.

This is what makes insights compounding: every session benefits from past
mistakes without manual recall.

## Related

- `.claude/rules/insights-capture.md` — when/how to capture
- `.claude/hooks/session-insights.cjs` — session injection
- `/harvest` — extracts reusable patterns from insights at project end
