# Copilot instructions for dhamma-channel-automation

## Governance rules
- This repo follows deterministic, evidence-driven changes only.
- No publish, no runtime change: do not modify runtime behavior, pipelines, or adapters unless explicitly requested.
- Governance-only edits must stay within `.github/**` and `SECURITY.md`.

## Determinism and contracts
- Treat `docs/BASELINE.md` as the source of truth for output contracts.
- Preserve deterministic artifacts and stable schemas; avoid nondeterministic outputs.
- Keep output paths relative and avoid introducing absolute paths.

## Structure hints
- Core libraries live in `src/automation_core/` and agents in `src/agents/`.
- CLI entry point is `cli/main.py`.
- Web UI lives in `app/` and uses `app/agent_commands.yml`.

## Quality expectations
- Prefer smallest possible diffs with clear intent.
- Do not add external services or network calls in workflows.
- Use `ruff` and `pytest` commands from CI for checks.
