# Canonical Prompt Pack

## Purpose
This document defines a deterministic, docs-governed prompt standard for opening and executing pull requests. It ensures reviewers and agents follow the smallest possible diff, avoid operational risk, and produce repeatable artifacts.

## Scope rules
- Docs-only PRs must modify documentation files exclusively.
- Runtime PRs may touch code/config, but must state execution impact and testing.
- Each PR must declare its allowed files list and must not edit anything outside it.

## Hard rules
- No secrets in prompts, artifacts, or commits.
- No external calls unless explicitly required by the task.
- Deterministic artifacts first (e.g., snapshot files, inventories) before edits.
- Smallest possible diff; do not reformat unrelated content.
- File lock discipline: only touch files explicitly allowed by the prompt.

## CODEX PROMPT SKELETON

### Repo/Branch/Title
- Repo: <org>/<repo>
- Branch: <branch-name>
- PR Title: <title>

### Persona
- <persona traits>

### Pre-flight snapshot gate
- Create REPO_SNAPSHOT.txt (not committed)
- Include: path, branch, commit, timestamp, file inventory, limited tree, key doc excerpts
- Acknowledge snapshot completion verbatim

### Goal
- <concise goal>

### Allowed files
- <explicit list>

### Forbidden files
- <explicit list>

### Implementation order
1) <step>
2) <step>
3) <step>

### PR body requirements
- Summary:
  - <item>
- Testing:
  - ran/not ran: <reason>
- Security:
  - no secrets
  - no external calls
  - runtime impact: <none/describe>

### Done criteria
- Only allowed files changed
- Snapshot not committed
- Diff minimal and scoped
- PR title matches requirement
