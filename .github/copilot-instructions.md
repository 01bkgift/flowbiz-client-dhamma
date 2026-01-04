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

### Scheduler/queue/worker (cron-friendly)
- The real scheduler + worker runner is `scripts/scheduler_runner.py` (not the web UI). It implements a deterministic file queue.
- Schedule plan format: `scripts/schedule_plan.yaml` (schema `v1`). Each entry enqueues a `JobSpec` with `{pipeline_path, run_id, params}`.
- Queue implementation (filesystem): `src/automation_core/queue.py` (`data/queue/{pending,running,done,failed}` by default).
- Scheduler logic: `src/automation_core/scheduler.py` (`schedule_due_jobs`) creates deterministic `job_id` + `run_id` (includes job hash).
- Kill switches and flags:
	- `PIPELINE_ENABLED=false` => scheduler + worker return `None` and must not create `output/` artifacts.
	- `SCHEDULER_ENABLED` / `WORKER_ENABLED` gate actual enqueue/work in non-dry-run mode (see `scripts/scheduler_runner.py`).

### Runtime params injection
- Scheduled params are passed to pipeline execution via env var `PIPELINE_PARAMS_JSON`.
- Injection + restore semantics are handled by `src/automation_core/params.py` (`inject_pipeline_params`), used by `scripts/scheduler_runner.py` when calling the orchestrator.
- New steps that need params should read from `PIPELINE_PARAMS_JSON` (JSON object, deterministic key order) rather than inventing new env vars.

## Output contracts and determinism
- Stable schemas and tone are defined in `docs/BASELINE.md` with reference artifacts in `samples/reference/**`; update these when outputs change intentionally.
- Output paths must be relative (no absolute paths or `..`), especially under `output/<run_id>/artifacts/`.
- Voiceover assets are content-addressed in `data/voiceovers/<run_id>/<slug>_<sha12>.wav/json` via `src/automation_core/voiceover_tts.py`; keep hashing and normalization deterministic.
- Assets policy is strict (`docs/ASSETS_POLICY.md`): no font binaries; `assets/fonts/` must remain README-only.

### Runner outputs (common debugging gotcha)
- Orchestrator (`orchestrator.py`) writes under `output/<run_id>/...`.
- Web cmd-runner (`scripts/run_pipeline.py`) writes under `output/pipelines/<timestamp_run_id>/...` with `run.log` and `summary.json`.

## Web UI wiring
- Agent list for the dashboard is in `app/core/agents_registry.py`.
- Commands run by the UI come from `app/agent_commands.yml`; many entries still point to `scripts/agent_placeholder.py`.
- When you wire a real agent into the UI, update both registry + command and provide example inputs under `examples/`.

### Naming across layers (do not assume 1:1)
- Orchestrator pipeline step uses `uses:` values like `TrendScout`, `voiceover.tts`, `youtube.upload` mapped via `AGENTS` in `orchestrator.py`.
- Web UI uses separate keys like `trend_scout`, `voiceover`, `orchestrator_pipeline` (see `app/core/agents_registry.py` and `app/agent_commands.yml`).
- Web pipeline steps (`pipeline.web.yml`) are plain `cmd:` lists and do not reference orchestrator `AGENTS` at all.

### Canonical pipeline examples
- Orchestrator YAMLs you should copy from first: `pipelines/video.yaml`, `pipelines/voiceover_tts.yaml`, `pipelines/video_render.yaml`, `pipelines/youtube_upload_smoke.yaml`.

## Conventions and workflow
- Identifiers are English; comments/docstrings and docs are Thai.
- Preferred checks: `make preflight` or `scripts/preflight.sh`; quick checks via `make quick` or `scripts/preflight_quick.sh`.
- Use `ruff`, `pytest`, and `mypy` settings from `pyproject.toml`.

## Integrations
- YouTube upload uses OAuth env vars (`YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN`) in `src/automation_core/youtube_upload.py`.
- FlowBiz contract endpoints live in `app/main.py` (`/healthz`, `/v1/meta`); avoid breaking their response shape.
- FlowBiz contract endpoints live in `app/main.py` (`/healthz`, `/v1/meta`); avoid breaking their response shape.
