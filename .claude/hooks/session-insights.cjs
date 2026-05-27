#!/usr/bin/env node
'use strict';

/**
 * SessionStart hook — injects up to 3 most recent insights from
 * .claude/insights/index.md into Claude's initial session context (via stdout).
 *
 * Cross-platform: pure Node, no shell pipes. Silent on missing index.
 */

const fs = require('node:fs');
const path = require('node:path');

const INDEX = path.resolve(process.cwd(), '.claude', 'insights', 'index.md');

try {
  if (!fs.existsSync(INDEX)) process.exit(0);
  const text = fs.readFileSync(INDEX, 'utf8');
  // Each insight starts with "## " heading (per insights-capture.md convention).
  const sections = text.split(/^## /m).filter(Boolean);
  const recent = sections.slice(-3).map((s) => '## ' + s.trim()).join('\n\n');
  if (recent.length > 0) {
    process.stdout.write('## Recent project insights\n\n' + recent + '\n');
  }
} catch (_err) {
  // Hook is advisory — never block the session on errors here.
  process.exit(0);
}
