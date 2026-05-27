#!/usr/bin/env node
'use strict';

/**
 * P-Replicator statusline (v1.5.0)
 *
 * Invoked by Claude Code via settings.json `statusLine` config. Output to
 * stdout becomes the status bar above the prompt. Multi-line + ANSI colors.
 *
 * Sources: filesystem heuristics + optional state-file (.claude/.p-replicator-state.json)
 * written by /run, /feature, /replicate via .claude/hooks/state-update.cjs.
 *
 * Defensive: every section is wrapped in try/catch with sensible fallback,
 * so a parse error in any single source never breaks the whole status bar.
 */

const fs = require('node:fs');
const path = require('node:path');

const CWD = process.cwd();
const NOW = Date.now();

// ─── ANSI helpers ─────────────────────────────────────────────────────────
const C = {
  reset:  '\x1b[0m',
  bold:   '\x1b[1m',
  dim:    '\x1b[2m',
  red:    '\x1b[31m',
  green:  '\x1b[32m',
  yellow: '\x1b[33m',
  blue:   '\x1b[34m',
  magenta:'\x1b[35m',
  cyan:   '\x1b[36m',
  gray:   '\x1b[90m',
};
function color(c, s) { return c + s + C.reset; }
function bold(s)  { return C.bold + s + C.reset; }
function dim(s)   { return C.dim + s + C.reset; }
function green(s) { return C.green + s + C.reset; }
function yellow(s){ return C.yellow + s + C.reset; }
function red(s)   { return C.red + s + C.reset; }
function cyan(s)  { return C.cyan + s + C.reset; }
function gray(s)  { return C.gray + s + C.reset; }

// ─── safe wrappers ────────────────────────────────────────────────────────
function safeRun(fn, fallback) {
  try { return fn(); } catch { return fallback; }
}
function safeReadJson(p) {
  try { return JSON.parse(fs.readFileSync(p, 'utf8')); } catch { return null; }
}
function safeReadText(p) {
  try { return fs.readFileSync(p, 'utf8'); } catch { return null; }
}
function safeListDir(p) {
  try { return fs.readdirSync(p); } catch { return []; }
}
function exists(p) {
  try { fs.accessSync(p); return true; } catch { return false; }
}

// ─── parsers (heuristic) ──────────────────────────────────────────────────

function parseManifest() {
  return safeReadJson(path.join(CWD, '.p-replicator.json'));
}

function parseState() {
  const p = path.join(CWD, '.claude', '.p-replicator-state.json');
  const state = safeReadJson(p);
  if (!state) return null;
  // Stale check: state older than 30 min — treat as not-running
  if (state.updatedAt) {
    const age = NOW - new Date(state.updatedAt).getTime();
    if (age > 30 * 60 * 1000) return null;
  }
  return state;
}

function parseRoadmap() {
  const r = safeReadJson(path.join(CWD, '.claude', 'feature-roadmap.json'));
  if (!r || !Array.isArray(r.features)) return null;
  const features = r.features;
  const total = features.length;
  const done = features.filter((f) => f.status === 'done').length;
  const inProgress = features.find((f) => f.status === 'in_progress');
  const blocked = features.filter((f) => f.status === 'blocked').length;
  const mvp = features.filter((f) => f.priority === 'mvp');
  const mvpDone = mvp.filter((f) => f.status === 'done').length;
  return { total, done, inProgress, blocked, mvpTotal: mvp.length, mvpDone };
}

function parseSparcDocs() {
  const docsDir = path.join(CWD, 'docs');
  const expectedSparc = [
    'PRD.md', 'Solution_Strategy.md', 'Specification.md', 'Pseudocode.md',
    'Architecture.md', 'Refinement.md', 'Completion.md',
    'Research_Findings.md', 'Final_Summary.md', 'C4_Diagrams.md', 'ADR.md',
  ];
  const present = expectedSparc.filter((f) => exists(path.join(docsDir, f)));
  return { present: present.length, total: expectedSparc.length };
}

function parseValidationScore() {
  const p = path.join(CWD, 'docs', 'validation-report.md');
  const text = safeReadText(p);
  if (!text) return null;
  // Look for "Average Score: XX/100" or "Score: XX" patterns
  const m = text.match(/(?:average\s+)?score[:\s]+(\d{1,3})(?:\s*\/\s*100)?/i);
  if (!m) return null;
  const score = parseInt(m[1], 10);
  let verdict;
  if (score >= 70) verdict = 'READY';
  else if (score >= 50) verdict = 'CAVEATS';
  else verdict = 'NEEDS_WORK';
  return { score, verdict };
}

function parseAdrs() {
  // Prefer docs/ADR.md (single file with ## ADR-N headings)
  const single = path.join(CWD, 'docs', 'ADR.md');
  if (exists(single)) {
    const text = safeReadText(single) || '';
    const headings = text.match(/^#{2,3}\s+ADR/gm) || [];
    if (headings.length > 0) return headings.length;
  }
  // Or docs/adr/*.md (per-ADR files)
  const dir = path.join(CWD, 'docs', 'adr');
  const files = safeListDir(dir).filter((f) => f.endsWith('.md'));
  if (files.length > 0) return files.length;
  // Or docs/ddd/adr/*.md (DDD pipeline)
  const dddDir = path.join(CWD, 'docs', 'ddd', 'adr');
  const dddFiles = safeListDir(dddDir).filter((f) => f.endsWith('.md'));
  return dddFiles.length;
}

function parsePlans() {
  const dir = path.join(CWD, 'docs', 'plans');
  return safeListDir(dir).filter((f) => f.endsWith('.md')).length;
}

function parseInsights() {
  const p = path.join(CWD, '.claude', 'insights', 'index.md');
  const text = safeReadText(p);
  if (!text) return { count: 0, lastDate: null };
  const headings = text.match(/^##\s+\d{4}-\d{2}-\d{2}/gm) || [];
  // Last date: extract from last heading
  let lastDate = null;
  if (headings.length > 0) {
    const last = headings[headings.length - 1];
    const m = last.match(/\d{4}-\d{2}-\d{2}/);
    if (m) lastDate = m[0];
  }
  return { count: headings.length, lastDate };
}

function parseToolkit() {
  const dir = path.join(CWD, '.claude');
  const skills = safeListDir(path.join(dir, 'skills')).filter((d) => {
    return safeRun(() => fs.statSync(path.join(dir, 'skills', d)).isDirectory(), false);
  }).length;
  const commands = safeListDir(path.join(dir, 'commands'))
    .filter((f) => f.endsWith('.md')).length;
  const agents = safeListDir(path.join(dir, 'agents'))
    .filter((f) => f.endsWith('.md')).length;
  const rules = safeListDir(path.join(dir, 'rules'))
    .filter((f) => f.endsWith('.md')).length;
  const hooks = safeListDir(path.join(dir, 'hooks'))
    .filter((f) => f.endsWith('.cjs')).length;
  return { skills, commands, agents, rules, hooks };
}

function parseExpectedToolkit() {
  // From manifest's components if shippedDefaults available; otherwise fall back to baseline
  return {
    skillsExpected: 10,
    commandsExpected: 11,
    agentsExpected: 4,    // pre-shipped only (project agents are extra)
    rulesExpected: 5,     // pre-shipped only (project rules are extra)
    hooksExpected: 6,     // 4 v1.4.1 hooks + statusline + state-update (v1.5.0)
  };
}

function parseSettingsStatus(manifest) {
  const settingsPath = path.join(CWD, '.claude', 'settings.json');
  if (!exists(settingsPath)) return 'missing';
  const cur = safeReadJson(settingsPath);
  if (!cur) return 'corrupt';
  const shipped = manifest && manifest.shippedDefaults && manifest.shippedDefaults['settings.json'];
  if (!shipped) return 'unknown';
  // If exact match: defaults; else: merged (user customized)
  try {
    const sortKeys = (o) => JSON.stringify(o, Object.keys(o).sort());
    return sortKeys(cur) === sortKeys(shipped) ? 'defaults' : 'merged';
  } catch {
    return 'unknown';
  }
}

function parseMcpServers() {
  const mcpJson = safeReadJson(path.join(CWD, '.mcp.json'));
  if (!mcpJson) return null;
  const servers = mcpJson.mcpServers || mcpJson.servers || {};
  return Object.keys(servers).length;
}

function parseKeysarium() {
  return exists(path.join(CWD, '.keysarium.json'));
}

function parseDomain() {
  const claudeMd = safeReadText(path.join(CWD, 'CLAUDE.md'));
  if (!claudeMd) return null;
  // Heuristic keyword search
  const banking = /банк|bank|финт|fintech|gigachat|yandexgpt|ФЗ-152|ЦБ|ФСТЭК/i;
  const retail = /retail|e-commerce|ecommerce|ритейл|рекоменд|conversion/i;
  const enterprise = /enterprise|b2b|legacy|sla|change\s*management/i;
  const healthcare = /health|medical|клиник|hipaa|ФЗ-323/i;
  if (banking.test(claudeMd)) return 'banking';
  if (retail.test(claudeMd)) return 'retail';
  if (enterprise.test(claudeMd)) return 'enterprise';
  if (healthcare.test(claudeMd)) return 'healthcare';
  return null;
}

function parseLastHarvest() {
  // Heuristic: TOOLKIT_HARVEST.md mtime
  const p = path.join(CWD, 'TOOLKIT_HARVEST.md');
  try {
    const stat = fs.statSync(p);
    return stat.mtime.toISOString().slice(0, 10);
  } catch { return null; }
}

function parseLastTest() {
  // Optional cache file written by users
  const p = path.join(CWD, '.claude', '.last-test.json');
  return safeReadJson(p);
}

// ─── progress bar ─────────────────────────────────────────────────────────
function bar(progress, width = 8) {
  const fill = Math.round(progress * width);
  const empty = width - fill;
  return '▓'.repeat(fill) + '░'.repeat(empty);
}
function dotBar(done, total, width = 8) {
  const w = Math.min(width, Math.max(total, 1));
  const fill = Math.round((done / Math.max(total, 1)) * w);
  return '['+ '●'.repeat(fill) + '○'.repeat(w - fill) + ']';
}

// ─── line builders ───────────────────────────────────────────────────────
function buildHeader(manifest) {
  const ver = (manifest && manifest.version) || '?';
  const user = process.env.USER || process.env.USERNAME || 'user';
  const model = process.env.CLAUDE_MODEL || process.env.MODEL || 'Claude';
  return `${cyan(bold('P-Replicator'))} ${dim('V' + ver)} ${green('●')} ${user}  ${dim('│')}  ${model}`;
}

function buildPipeline(state) {
  const parts = ['🚀 ' + bold('Pipeline')];
  if (state && state.currentCommand) {
    const cmd = state.currentCommand;
    const phase = state.currentPhase;
    if (phase) {
      const progress = typeof phase.progress === 'number' ? phase.progress : 0;
      const idx = phase.index ?? '?';
      const total = phase.total ?? '?';
      parts.push(`${cyan(cmd)} ${bar(progress)} ${Math.round(progress*100)}%`);
      parts.push(`${dim('Phase:')} ${phase.name || ''} (${idx}/${total})`);
    } else {
      parts.push(cyan(cmd));
    }
    if (state.lastCommand && state.lastCommand !== cmd) {
      parts.push(`${dim('Last:')} ${state.lastCommand}`);
    }
  } else {
    parts.push(dim('idle'));
  }
  return parts.join('  ' + dim('│') + '  ');
}

function buildRoadmap(roadmap, domain) {
  if (!roadmap) {
    return `🎯 ${bold('Roadmap')}  ${dim('— no roadmap yet (run /next or /replicate)')}`;
  }
  const { total, done, inProgress, blocked, mvpTotal, mvpDone } = roadmap;
  const dotbar = dotBar(done, total, 8);
  const parts = [
    `🎯 ${bold('Roadmap')}`,
    `${dotbar} mvp ${green(mvpDone + '/' + mvpTotal)}`,
    `${dim('Done')} ${green(done + '/' + total)}`,
  ];
  if (inProgress) {
    parts.push(`${dim('▶')} ${cyan(inProgress.id)}`);
  }
  if (blocked > 0) {
    parts.push(`${red('Blocked')} ${blocked}`);
  }
  if (domain) {
    parts.push(`${dim('Domain:')} ${cyan(domain)}`);
  }
  return parts.join('  ' + dim('│') + '  ');
}

function buildDocs(sparc, validation, plans, adrs, lastHarvest) {
  const parts = [`📊 ${bold('SPARC')} ${green('●' + sparc.present + '/' + sparc.total)}`];
  if (validation) {
    const verdictIcon = validation.verdict === 'READY' ? '🟢'
      : validation.verdict === 'CAVEATS' ? '🟡' : '🔴';
    parts.push(`${verdictIcon} ${validation.score}/100`);
  }
  parts.push(`${dim('Plans')} ${plans > 0 ? green('●' + plans) : '0'}`);
  parts.push(`${dim('ADRs')} ${adrs > 0 ? green('●' + adrs) : '0'}`);
  if (lastHarvest) {
    parts.push(`${dim('Harvest')} ${lastHarvest}`);
  }
  return parts.join('  ' + dim('│') + '  ');
}

function buildToolkit(toolkit, expected) {
  const dotIf = (v, e) => v >= e ? green('●' + v + '/' + e) : yellow('●' + v + '/' + e);
  const extraAgents = Math.max(0, toolkit.agents - expected.agentsExpected);
  const extraRules  = Math.max(0, toolkit.rules - expected.rulesExpected);
  const agentsLbl = toolkit.agents >= expected.agentsExpected
    ? green('●' + expected.agentsExpected + (extraAgents > 0 ? '+' + extraAgents : ''))
    : yellow('●' + toolkit.agents + '/' + expected.agentsExpected);
  const rulesLbl = toolkit.rules >= expected.rulesExpected
    ? green('●' + expected.rulesExpected + (extraRules > 0 ? '+' + extraRules : ''))
    : yellow('●' + toolkit.rules + '/' + expected.rulesExpected);
  return [
    `🛠️  ${bold('Toolkit')}`,
    `Skills ${dotIf(toolkit.skills, expected.skillsExpected)}`,
    `Cmds ${dotIf(toolkit.commands, expected.commandsExpected)}`,
    `Agents ${agentsLbl}`,
    `Rules ${rulesLbl}`,
    `Hooks ${dotIf(toolkit.hooks, expected.hooksExpected)}`,
  ].join('  ' + dim('│') + '  ');
}

function buildStatus(insights, lastTest, mcpServers, settingsStatus, keysarium) {
  const parts = [];
  parts.push(`💡 ${bold('Insights')} ${insights.count > 0 ? green('●' + insights.count) : '0'}` +
    (insights.lastDate ? ` ${dim('(' + insights.lastDate + ')')}` : ''));

  if (lastTest && typeof lastTest.passed === 'number') {
    const total = lastTest.total ?? lastTest.passed;
    const ok = lastTest.passed === total;
    parts.push(`${ok ? '✅' : '❌'} ${dim('Tests')} ${ok ? green(lastTest.passed + '/' + total) : red(lastTest.passed + '/' + total)}`);
  }
  if (mcpServers !== null && mcpServers !== undefined) {
    parts.push(`🔌 ${dim('MCP')} ${mcpServers > 0 ? green('●' + mcpServers) : '0'}`);
  }
  if (settingsStatus) {
    const map = { defaults: '✓ defaults', merged: '⚠️ merged', corrupt: red('🔴 corrupt'), missing: red('missing'), unknown: '?' };
    parts.push(`⚙️  ${dim('Settings')} ${map[settingsStatus] || settingsStatus}`);
  }
  if (keysarium) {
    parts.push(`🧬 ${green('Keysarium ✓')}`);
  }
  return parts.join('  ' + dim('│') + '  ');
}

// ─── main ─────────────────────────────────────────────────────────────────
function main() {
  const manifest = safeRun(() => parseManifest(), null);
  const state = safeRun(() => parseState(), null);
  const roadmap = safeRun(() => parseRoadmap(), null);
  const sparc = safeRun(() => parseSparcDocs(), { present: 0, total: 11 });
  const validation = safeRun(() => parseValidationScore(), null);
  const adrs = safeRun(() => parseAdrs(), 0);
  const plans = safeRun(() => parsePlans(), 0);
  const insights = safeRun(() => parseInsights(), { count: 0, lastDate: null });
  const toolkit = safeRun(() => parseToolkit(), { skills: 0, commands: 0, agents: 0, rules: 0, hooks: 0 });
  const expected = parseExpectedToolkit();
  const settingsStatus = safeRun(() => parseSettingsStatus(manifest), null);
  const mcpServers = safeRun(() => parseMcpServers(), null);
  const keysarium = safeRun(() => parseKeysarium(), false);
  const domain = safeRun(() => parseDomain(), null);
  const lastHarvest = safeRun(() => parseLastHarvest(), null);
  const lastTest = safeRun(() => parseLastTest(), null);

  const lines = [
    buildHeader(manifest),
    buildPipeline(state),
    buildRoadmap(roadmap, domain),
    buildDocs(sparc, validation, plans, adrs, lastHarvest),
    buildToolkit(toolkit, expected),
    buildStatus(insights, lastTest, mcpServers, settingsStatus, keysarium),
  ];

  // Write to stdout, never throw
  try {
    process.stdout.write(lines.join('\n') + '\n');
  } catch { /* ignore */ }
}

main();
