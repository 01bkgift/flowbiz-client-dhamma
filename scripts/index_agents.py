import argparse
import json
from datetime import datetime
from pathlib import Path

import yaml


def scan_files():
    root = Path(".")
    prompts_dir = root / "prompts"
    agents_dir = root / "src" / "agents"
    commands_file = root / "app" / "agent_commands.yml"

    data = {
        "scanned_at": datetime.utcnow().isoformat() + "Z",
        "prompts": [],
        "agents": [],
        "commands": {},
        "summary": {},
    }

    # collect prompts
    if prompts_dir.exists():
        for p in sorted(prompts_dir.glob("**/*.txt")):
            data["prompts"].append(
                {
                    "path": str(p.as_posix()),
                    "name": p.name,
                    "size": p.stat().st_size,
                    "mtime": datetime.utcfromtimestamp(p.stat().st_mtime).isoformat()
                    + "Z",
                }
            )

    # collect agents tree
    if agents_dir.exists():
        for d in sorted(agents_dir.glob("*")):
            if d.is_dir():
                entry = {
                    "agent_dir": str(d.as_posix()),
                    "files": [],
                }
                for f in sorted(d.glob("**/*")):
                    if f.is_file():
                        entry["files"].append(
                            {
                                "path": str(f.as_posix()),
                                "name": f.name,
                                "size": f.stat().st_size,
                            }
                        )
                data["agents"].append(entry)

    # commands mapping
    if commands_file.exists():
        try:
            data["commands"] = (
                yaml.safe_load(commands_file.read_text(encoding="utf-8")) or {}
            )
        except Exception as e:
            data["commands_error"] = repr(e)

    # summary
    data["summary"] = {
        "prompt_count": len(data["prompts"]),
        "agent_dir_count": len(data["agents"]),
        "has_commands": bool(data.get("commands")),
    }
    return data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, help="output json path")
    args = parser.parse_args()

    print("progress=5%")
    data = scan_files()
    print("progress=80%")
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Wrote index to {out_path}")
    print("progress=100%")


if __name__ == "__main__":
    main()
