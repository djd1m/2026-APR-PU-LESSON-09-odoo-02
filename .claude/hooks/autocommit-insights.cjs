#!/usr/bin/env node
'use strict';

/**
 * Stop hook — auto-commits .claude/insights/ if anything changed.
 * Cross-platform: pure Node + execFileSync, no shell.
 */

const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');

const TARGET_DIR = path.resolve(process.cwd(), '.claude', 'insights');
const RELATIVE = path.relative(process.cwd(), TARGET_DIR);
const SILENT = { stdio: 'ignore' };

function git(args) {
  return execFileSync('git', args, SILENT);
}

try {
  if (!fs.existsSync(TARGET_DIR)) process.exit(0);
  try { git(['rev-parse', '--git-dir']); } catch { process.exit(0); }

  git(['add', '--', RELATIVE]);

  let hasDiff = false;
  try {
    git(['diff', '--cached', '--quiet', '--', RELATIVE]);
  } catch {
    hasDiff = true;
  }

  if (hasDiff) {
    git(['commit', '--only', '--', RELATIVE, '-m', 'docs(insights): auto-capture']);
  }
} catch (_err) {
  process.exit(0);
}
