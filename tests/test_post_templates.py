"""
Tests for post template rendering and summary artifact.
"""

from __future__ import annotations

import json
from pathlib import Path

from automation_core import post_templates


def _write_templates(
    base_dir: Path, *, short_text: str | None = None, long_text: str | None = None
) -> None:
    templates_dir = base_dir / "templates" / "post"
    templates_dir.mkdir(parents=True, exist_ok=True)
    (templates_dir / "short.md").write_text(
        short_text or "{{hook}}\n{{summary}}\n\n{{cta}}\n{{hashtags}}\n",
        encoding="utf-8",
    )
    (templates_dir / "long.md").write_text(
        long_text
        or "{{title}}\n\n{{hook}}\n\n{{summary}}\n\n{{cta}}\n\n{{hashtags}}\n",
        encoding="utf-8",
    )


def _write_metadata(base_dir: Path, run_id: str, payload: dict[str, object]) -> None:
    metadata_path = base_dir / "output" / run_id / "metadata.json"
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _assert_relative(value: str) -> None:
    path = Path(value)
    assert not path.is_absolute()
    assert ".." not in path.parts


def test_post_content_summary_schema(tmp_path, monkeypatch):
    run_id = "run_schema"
    _write_templates(tmp_path)
    _write_metadata(
        tmp_path,
        run_id,
        {
            "title": "Title",
            "description": "Summary",
            "tags": ["#b", "#a"],
            "platform": "youtube",
            "language": "en",
        },
    )

    monkeypatch.setenv(
        "PIPELINE_PARAMS_JSON", json.dumps({"hook": "Hook", "cta": "Go"})
    )
    monkeypatch.setenv("PIPELINE_ENABLED", "true")

    _, summary_path = post_templates.generate_post_content_summary(
        run_id, base_dir=tmp_path
    )
    assert summary_path.exists()

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["schema_version"] == "v1"
    assert summary["engine"] == "post_templates"
    assert summary["run_id"] == run_id
    assert isinstance(summary["checked_at"], str)

    inputs = summary["inputs"]
    outputs = summary["outputs"]

    assert inputs["lang"] == "en"
    assert inputs["platform"] == "youtube"
    assert inputs["template_short"] == "templates/post/short.md"
    assert inputs["template_long"] == "templates/post/long.md"
    assert inputs["sources"] == [
        post_templates.ENV_SOURCE,
        f"output/{run_id}/metadata.json",
    ]

    _assert_relative(inputs["template_short"])
    _assert_relative(inputs["template_long"])
    for source in inputs["sources"]:
        if source == post_templates.ENV_SOURCE:
            continue
        _assert_relative(source)

    assert isinstance(outputs["short"], str)
    assert isinstance(outputs["long"], str)


def test_render_deterministic_outputs(tmp_path, monkeypatch):
    run_id = "run_det"
    _write_templates(tmp_path)

    payload = {
        "title": "Same Title",
        "summary": "Same Summary",
        "hashtags": ["#b", "#a"],
    }
    monkeypatch.setenv("PIPELINE_PARAMS_JSON", json.dumps(payload))

    first = post_templates.render_post_templates(run_id, base_dir=tmp_path)
    second = post_templates.render_post_templates(run_id, base_dir=tmp_path)

    assert first["short"] == second["short"]
    assert first["long"] == second["long"]


def test_hashtag_normalization_list(tmp_path, monkeypatch):
    run_id = "run_tags"
    _write_templates(tmp_path, short_text="{{hashtags}}\n", long_text="{{hashtags}}\n")

    monkeypatch.setenv(
        "PIPELINE_PARAMS_JSON",
        json.dumps({"hashtags": ["#b", " #c ", "#a"]}),
    )

    rendered = post_templates.render_post_templates(run_id, base_dir=tmp_path)
    assert rendered["short"].strip() == "#a #b #c"
    assert rendered["long"].strip() == "#a #b #c"


def test_hashtag_normalization_string(tmp_path, monkeypatch):
    run_id = "run_tags_str"
    _write_templates(tmp_path, short_text="{{hashtags}}\n", long_text="{{hashtags}}\n")

    monkeypatch.setenv(
        "PIPELINE_PARAMS_JSON",
        json.dumps({"hashtags": "  #b   #a  #c  "}),
    )

    rendered = post_templates.render_post_templates(run_id, base_dir=tmp_path)
    assert rendered["short"].strip() == "#b #a #c"
    assert rendered["long"].strip() == "#b #a #c"


def test_kill_switch_prevents_writes(tmp_path, monkeypatch):
    run_id = "run_disabled"
    _write_templates(tmp_path)

    monkeypatch.setattr(post_templates, "REPO_ROOT", tmp_path)
    monkeypatch.setenv("PIPELINE_ENABLED", "false")

    exit_code = post_templates.cli_main(["render", "--run-id", run_id])
    assert exit_code == 0
    assert not (tmp_path / "output").exists()


def test_kill_switch_prevents_direct_call_writes(tmp_path, monkeypatch):
    run_id = "run_disabled_direct"
    _write_templates(tmp_path)

    monkeypatch.setenv("PIPELINE_ENABLED", "false")

    _, summary_path = post_templates.generate_post_content_summary(
        run_id, base_dir=tmp_path
    )
    assert summary_path == (
        tmp_path / "output" / run_id / "artifacts" / "post_content_summary.json"
    )
    assert not (tmp_path / "output").exists()
    assert not summary_path.exists()


def test_unknown_placeholder_fails_without_writes(tmp_path, monkeypatch):
    run_id = "run_unknown"
    _write_templates(tmp_path, short_text="{{unknown}}\n", long_text="{{title}}\n")

    monkeypatch.setattr(post_templates, "REPO_ROOT", tmp_path)
    monkeypatch.setenv("PIPELINE_ENABLED", "true")

    exit_code = post_templates.cli_main(["render", "--run-id", run_id])
    assert exit_code == 1
    assert not (tmp_path / "output").exists()
