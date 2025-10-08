import argparse
import json
from pathlib import Path

# ใช้ API ตามตัวอย่างใน README ของโปรเจกต์
from agents.localization_subtitle import (
    LocalizationSubtitleAgent,
    LocalizationSubtitleInput,
    SubtitleSegment,
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", required=True, help="output directory (base path)")
    args = ap.parse_args()

    data = json.loads(Path(args.input).read_text(encoding="utf-8"))

    # คาดหวังฟิลด์: base_start_time (str), approved_script (list of {segment_type, text, est_seconds})
    base_start = data.get("base_start_time", "00:00:05,000")
    segments = [
        SubtitleSegment(
            segment_type=s.get("segment_type", "segment"),
            text=s.get("text", ""),
            est_seconds=int(s.get("est_seconds", 3)),
        )
        for s in data.get("approved_script", [])
    ]

    agent = LocalizationSubtitleAgent()
    input_data = LocalizationSubtitleInput(
        base_start_time=base_start,
        approved_script=segments,
    )
    result = agent.run(input_data)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    # เขียนไฟล์ SRT และสรุป
    (out_dir / "subtitles.srt").write_text(result.srt, encoding="utf-8")
    payload = {
        "english_summary": result.english_summary,
        "quality_meta": getattr(result, "quality_meta", {}),
    }
    (out_dir / "summary.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"เขียนไฟล์ผลลัพธ์ที่ {out_dir}")


if __name__ == "__main__":
    main()
