#!/usr/bin/env node
'use strict';

/**
 * Stop hook — auto-commits .claude/feature-roadmap.json if it changed.
 * Cross-platform: uses execFileSync('git', [...]) so no shell quoting/redirect issues.
 */

const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');

const TARGET = path.resolve(process.cwd(), '.claude', 'feature-roadmap.json');
const RELATIVE = path.relative(process.cwd(), TARGET);
const SILENT = { stdio: 'ignore' };

function git(args) {
  return execFileSync('git', args, SILENT);
}

try {
  // Skip if file doesn't exist or we're not in a git repo.
  if (!fs.existsSync(TARGET)) process.exit(0);
  try { git(['rev-parse', '--git-dir']); } catch { process.exit(0); }

  // Stage only the target file.
  git(['add', '--', RELATIVE]);

  // Check whether anything is staged for THIS path.
  // `git diff --cached --quiet -- <path>` exits 0 = no diff, 1 = diff exists.
  let hasDiff = false;
  try {
    git(['diff', '--cached', '--quiet', '--', RELATIVE]);
  } catch {
    hasDiff = true;
  }

  if (hasDiff) {
    git(['commit', '--only', '--', RELATIVE, '-m', 'docs(roadmap): auto-update']);
  }
} catch (_err) {
  // Best-effort — never break Claude session on commit failures.
  process.exit(0);
}
