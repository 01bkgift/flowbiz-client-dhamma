import json
from pathlib import Path

from steps.decision_support.model import DecisionEnum
from steps.decision_support.step import run_decision_support


def test_decision_support_r1_quality_fail(tmp_path: Path):
    """R1: If quality gate is present AND decision == 'fail' -> recommend_hold"""
    # Setup artifacts
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()

    quality_gate = {
        "decision": "fail",
        "run_id": "test_run",
        "generated_at": "2025-01-01T00:00:00Z",
    }
    (artifacts_dir / "quality_gate_summary.json").write_text(json.dumps(quality_gate))

    # Run step
    step_config = {"output": "decision_support.json", "run_id": "test_run"}
    output_path = run_decision_support(step_config, artifacts_dir)

    # Verify
    assert output_path.exists()
    data = json.loads(output_path.read_text())

    assert data["decision"] == DecisionEnum.RECOMMEND_HOLD
    assert data["confidence"] == 0.95
    assert "QUALITY_FAIL" in data["reasons"]


def test_decision_support_r2_quality_missing(tmp_path: Path):
    """R2: If quality gate is missing -> recommend_hold"""
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()

    # No quality gate file

    step_config = {"output": "decision_support.json", "run_id": "test_run"}
    output_path = run_decision_support(step_config, artifacts_dir)

    data = json.loads(output_path.read_text())
    assert data["decision"] == DecisionEnum.RECOMMEND_HOLD
    assert data["confidence"] == 0.70
    assert "MISSING_QUALITY_GATE" in data["reasons"]


def test_decision_support_r3_kpi_missing(tmp_path: Path):
    """R3: Quality pass but KPI missing -> recommend_publish (low confidence)"""
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()

    quality_gate = {"decision": "pass"}
    (artifacts_dir / "quality_gate_summary.json").write_text(json.dumps(quality_gate))

    output_path = run_decision_support({}, artifacts_dir)

    data = json.loads(output_path.read_text())
    assert data["decision"] == DecisionEnum.RECOMMEND_PUBLISH
    assert data["confidence"] == 0.60
    assert "MISSING_KPI_BASELINE" in data["reasons"]


def test_decision_support_r4_kpi_low(tmp_path: Path):
    """R4: Quality pass + KPI low -> recommend_edit"""
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()

    (artifacts_dir / "quality_gate_summary.json").write_text(
        json.dumps({"decision": "pass"})
    )
    kpi = {
        "total_views": 500,  # < 1000
        "total_watch_time_minutes": 2000,  # < 5000
        "total_subscribers_gained": 5,  # < 10
    }
    (artifacts_dir / "kpi_summary.json").write_text(json.dumps(kpi))

    output_path = run_decision_support({}, artifacts_dir)

    data = json.loads(output_path.read_text())
    assert data["decision"] == DecisionEnum.RECOMMEND_EDIT
    assert data["confidence"] == 0.75
    assert "KPI_LOW" in data["reasons"]


def test_decision_support_r4_kpi_high(tmp_path: Path):
    """R4: Quality pass + KPI high -> recommend_publish"""
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()

    (artifacts_dir / "quality_gate_summary.json").write_text(
        json.dumps({"decision": "pass"})
    )
    kpi = {
        "total_views": 1500,  # >= 1000
        "total_watch_time_minutes": 100,
        "total_subscribers_gained": 0,
    }
    (artifacts_dir / "kpi_summary.json").write_text(json.dumps(kpi))

    output_path = run_decision_support({}, artifacts_dir)

    data = json.loads(output_path.read_text())
    assert data["decision"] == DecisionEnum.RECOMMEND_PUBLISH
    assert data["confidence"] == 0.80
    assert "KPI_UP" in data["reasons"]
    assert "inputs_used" in data
    assert "quality_gate" in data["inputs_used"]
    assert "kpi_summary" in data["inputs_used"]
