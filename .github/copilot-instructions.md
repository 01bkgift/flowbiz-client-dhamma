# Copilot instructions for dhamma-channel-automation

## Architecture
- Core libs live in `src/automation_core/` (BaseAgent, config, logging, prompt_loader, queue/scheduler, post_templates, voiceover_tts, youtube_upload).
- Agent packages are under `src/agents/<name>/` with Pydantic schemas in `model.py` and logic in `agent.py`, but many pipeline steps are implemented directly in `orchestrator.py`.
- CLI entry point is `cli/main.py` (Typer + Rich), currently exposing `trend-scout`.
- Web UI is FastAPI + Jinja in `app/` and shells out to commands from `app/agent_commands.yml`.

## Pipelines and orchestration
- Orchestrator pipelines live in `pipelines/*.yaml` and use `uses:` keys that must match the `AGENTS` mapping in `orchestrator.py`; run via `python orchestrator.py --pipeline ... --run-id ...`.
- The web pipeline in `pipeline.web.yml` is a different format (`cmd:` steps) executed by `scripts/run_pipeline.py` and used by the UI.
- `PIPELINE_ENABLED` is a global kill switch enforced in `orchestrator.py`, `src/automation_core/post_templates.py`, `src/automation_core/dispatch_v0.py`, and `src/automation_core/voiceover_tts.py`; do not bypass or write outputs when disabled.
- When adding a new pipeline step, update the handler in `orchestrator.py` and the YAML in `pipelines/` together.

## Output contracts and determinism
- Stable schemas and tone are defined in `docs/BASELINE.md` with reference artifacts in `samples/reference/**`; update these when outputs change intentionally.
- Output paths must be relative (no absolute paths or `..`), especially under `output/<run_id>/artifacts/`.
- Voiceover assets are content-addressed in `data/voiceovers/<run_id>/<slug>_<sha12>.wav/json` via `src/automation_core/voiceover_tts.py`; keep hashing and normalization deterministic.
- Assets policy is strict (`docs/ASSETS_POLICY.md`): no font binaries; `assets/fonts/` must remain README-only.

## Web UI wiring
- Agent list for the dashboard is in `app/core/agents_registry.py`.
- Commands run by the UI come from `app/agent_commands.yml`; many entries still point to `scripts/agent_placeholder.py`.
- When you wire a real agent into the UI, update both registry + command and provide example inputs under `examples/`.

## Conventions and workflow
- Identifiers are English; comments/docstrings and docs are Thai.
- Preferred checks: `make preflight` or `scripts/preflight.sh`; quick checks via `make quick` or `scripts/preflight_quick.sh`.
- Use `ruff`, `pytest`, and `mypy` settings from `pyproject.toml`.

## Integrations
- YouTube upload uses OAuth env vars (`YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN`) in `src/automation_core/youtube_upload.py`.
- FlowBiz contract endpoints live in `app/main.py` (`/healthz`, `/v1/meta`); avoid breaking their response shape.
