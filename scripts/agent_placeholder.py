import argparse
import json
from datetime import datetime
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", required=True)
    ap.add_argument("--input", required=False)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    payload = {}
    if args.input and Path(args.input).exists():
        try:
            payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
        except Exception:
            pass

    result = {
        "agent": args.agent,
        "started_at": datetime.utcnow().isoformat() + "Z",
        "status": "placeholder",
        "message": f"เอเจนต์ {args.agent} ยังไม่ได้เชื่อม CLI จริง — โปรดอัปเดต app/agent_commands.yml",
        "input_preview": payload,
        "ended_at": datetime.utcnow().isoformat() + "Z",
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Wrote placeholder output for {args.agent} to {out_path}")


if __name__ == "__main__":
    main()
