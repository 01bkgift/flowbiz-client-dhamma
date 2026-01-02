"""
ชุดทดสอบสำหรับโมดูล post_templates

ทดสอบพฤติกรรมหลัก ๆ ดังนี้:
- การเรนเดอร์เทมเพลตโพสต์แบบสั้น (short) และแบบยาว (long) จากไฟล์ในโฟลเดอร์
  templates/post โดยใช้ตัวแปร placeholder ต่าง ๆ เช่น title, hook, summary,
  cta และ hashtags
- การสร้างและบันทึก summary artifact และตรวจสอบว่าเส้นทางไฟล์ที่ได้เป็น
  path แบบ relative ภายในโฟลเดอร์ output ของ run_id ที่กำหนด
- การอ่านค่า PIPELINE_PARAMS_JSON จาก environment variable แล้วนำมาใช้แทนค่า
  ในเทมเพลต รวมถึงโครงสร้างข้อมูลของ summary artifact ที่สร้างขึ้น
- การ normalize แฮชแท็กทั้งในกรณีรับค่าเป็นลิสต์และเป็นสตริงให้กลายเป็น
  สตริงเดียวที่จัดเรียงและตัดช่องว่างส่วนเกินเรียบร้อย
- การรับประกันว่าผลลัพธ์การเรนเดอร์เทมเพลตมีความเป็น deterministic
  คือเรียกเรนเดอร์ด้วยข้อมูลชุดเดิมจะได้เนื้อหาเท่ากันทุกครั้ง
- กลไก kill switch ผ่านตัวแปร PIPELINE_ENABLED ที่ต้องป้องกันไม่ให้มีการ
  สร้างหรือเขียนไฟล์ในโฟลเดอร์ output ทั้งกรณีเรียกผ่านฟังก์ชัน cli_main
  และกรณีเรียกฟังก์ชันเรนเดอร์โดยตรง
- กรณีที่มี placeholder ที่ไม่รู้จักในเทมเพลตต้องล้มเหลวอย่างถูกต้องและไม่ควร
  มีไฟล์ผลลัพธ์ใด ๆ ถูกเขียนลงดิสก์
"""

from __future__ import annotations

import json
from pathlib import Path

from automation_core import post_templates


def _write_templates(
    base_dir: Path, *, short_text: str | None = None, long_text: str | None = None
) -> None:
    """
    เขียนไฟล์เทมเพลต short.md และ long.md ลงในโฟลเดอร์ templates/post

    Args:
        base_dir: directory ฐานสำหรับการทดสอบ
        short_text: เนื้อหาเทมเพลต short (ถ้าไม่ระบุจะใช้เทมเพลตเริ่มต้น)
        long_text: เนื้อหาเทมเพลต long (ถ้าไม่ระบุจะใช้เทมเพลตเริ่มต้น)
    """
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
    """
    เขียนไฟล์ metadata.json ลงในโฟลเดอร์ output/{run_id}

    Args:
        base_dir: directory ฐานสำหรับการทดสอบ
        run_id: run identifier
        payload: dictionary ที่จะเขียนเป็น JSON
    """
    metadata_path = base_dir / "output" / run_id / "metadata.json"
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _assert_relative(value: str) -> None:
    """
    ตรวจสอบว่า path เป็น relative path ที่ปลอดภัย (ไม่ absolute และไม่มี ..)

    Args:
        value: path ที่ต้องการตรวจสอบ

    Raises:
        AssertionError: ถ้า path เป็น absolute หรือมี '..'
    """
    path = Path(value)
    assert not path.is_absolute()
    assert ".." not in path.parts


def test_post_content_summary_schema(tmp_path, monkeypatch):
    """
    ทดสอบโครงสร้าง schema ของ post_content_summary.json

    ตรวจสอบว่า summary artifact มีฟิลด์ที่จำเป็นครบถ้วน และ path ต่าง ๆ
    เป็น relative path ที่ปลอดภัย
    """
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
    """
    ทดสอบว่าการเรนเดอร์เทมเพลตให้ผลลัพธ์แบบ deterministic

    เรียกเรนเดอร์ด้วยข้อมูลชุดเดิมสองครั้งจะต้องได้เนื้อหาเท่ากันทุกครั้ง
    """
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
    """
    ทดสอบการ normalize แฮชแท็กที่รับค่าเป็น list

    ตรวจสอบว่าแฮชแท็กถูกจัดเรียง trim ช่องว่าง และรวมเป็นสตริงเดียวอย่างถูกต้อง
    """
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
    """
    ทดสอบการ normalize แฮชแท็กที่รับค่าเป็น string

    ตรวจสอบว่าแฮชแท็กที่เป็นสตริงถูกแยกคำ จัดเรียง และตัดช่องว่างส่วนเกินอย่างถูกต้อง
    """
    run_id = "run_tags_str"
    _write_templates(tmp_path, short_text="{{hashtags}}\n", long_text="{{hashtags}}\n")

    monkeypatch.setenv(
        "PIPELINE_PARAMS_JSON",
        json.dumps({"hashtags": "  #b   #a  #c  "}),
    )

    rendered = post_templates.render_post_templates(run_id, base_dir=tmp_path)
    assert rendered["short"].strip() == "#a #b #c"
    assert rendered["long"].strip() == "#a #b #c"


def test_kill_switch_prevents_writes(tmp_path, monkeypatch):
    """
    ทดสอบกลไก kill-switch ผ่าน CLI ว่าป้องกันการเขียนไฟล์เมื่อ PIPELINE_ENABLED=false

    เรียก cli_main ด้วย PIPELINE_ENABLED=false ต้องไม่มีไฟล์ใด ๆ ถูกสร้างในโฟลเดอร์ output
    """
    run_id = "run_disabled"
    _write_templates(tmp_path)

    monkeypatch.setattr(post_templates, "REPO_ROOT", tmp_path)
    monkeypatch.setenv("PIPELINE_ENABLED", "false")

    exit_code = post_templates.cli_main(["render", "--run-id", run_id])
    assert exit_code == 0
    assert not (tmp_path / "output").exists()


def test_kill_switch_prevents_direct_call_writes(tmp_path, monkeypatch):
    """
    ทดสอบกลไก kill-switch ผ่านการเรียกฟังก์ชันโดยตรง

    เรียก generate_post_content_summary ด้วย PIPELINE_ENABLED=false
    ต้องไม่มีไฟล์ใด ๆ ถูกสร้างในโฟลเดอร์ output
    """
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
    """
    ทดสอบว่าเทมเพลตที่มี placeholder ไม่รู้จักจะล้มเหลวโดยไม่เขียนไฟล์

    เรียก cli_main ด้วยเทมเพลตที่มี {{unknown}} ต้อง return exit code 1
    และไม่มีไฟล์ใด ๆ ถูกสร้างในโฟลเดอร์ output
    """
    run_id = "run_unknown"
    _write_templates(tmp_path, short_text="{{unknown}}\n", long_text="{{title}}\n")

    monkeypatch.setattr(post_templates, "REPO_ROOT", tmp_path)
    monkeypatch.setenv("PIPELINE_ENABLED", "true")

    exit_code = post_templates.cli_main(["render", "--run-id", run_id])
    assert exit_code == 1
    assert not (tmp_path / "output").exists()
