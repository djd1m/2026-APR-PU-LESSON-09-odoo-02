#!/usr/bin/env node
'use strict';

/**
 * Stop hook — pushes to origin after all autocommit hooks have run.
 * MUST be the LAST entry in the Stop hooks array in settings.json.
 * Cross-platform: uses execFileSync('git', [...]).
 */

const { execFileSync } = require('node:child_process');

function git(args) {
  return execFileSync('git', args, { stdio: 'pipe' }).toString().trim();
}

try {
  // Skip if not in a git repo.
  try { git(['rev-parse', '--git-dir']); } catch { process.exit(0); }

  // Check if we have a remote named 'origin'.
  let remotes;
  try { remotes = git(['remote']); } catch { process.exit(0); }
  if (!remotes.split('\n').includes('origin')) process.exit(0);

  // Check if current branch tracks a remote.
  let branch;
  try { branch = git(['rev-parse', '--abbrev-ref', 'HEAD']); } catch { process.exit(0); }

  // Push current branch to origin (best-effort).
  execFileSync('git', ['push', 'origin', branch], { stdio: 'inherit' });
} catch (_err) {
  // Best-effort — never break Claude session on push failures.
  process.exit(0);
}
