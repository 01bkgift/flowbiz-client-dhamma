import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import yaml


def run_cmd(cmd, cwd=None, env=None, log_file=None):
    start = time.time()
    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        env=env or os.environ.copy(),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    lines = []
    for line in proc.stdout:
        line = line.rstrip("\n")
        print(line)
        lines.append(line)
        if log_file:
            log_file.write(line + "\n")
            log_file.flush()
    rc = proc.wait()
    dur = time.time() - start
    return rc, dur, lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pipeline", required=True, help="path to pipeline yaml")
    args = ap.parse_args()

    with open(args.pipeline, encoding="utf-8") as f:
        pipeline = yaml.safe_load(f)

    steps = pipeline.get("steps", [])
    run_id = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    out_dir = Path("output") / "pipelines" / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = out_dir / "run.log"

    summary = {
        "pipeline_file": args.pipeline,
        "run_id": run_id,
        "started_at": datetime.utcnow().isoformat() + "Z",
        "steps": [],
    }

    with open(log_path, "w", encoding="utf-8") as lf:
        for i, step in enumerate(steps, 1):
            name = step.get("id") or f"step{i}"
            cmd = step.get("cmd")
            cwd = step.get("cwd")
            env = os.environ.copy()
            for k, v in (step.get("env") or {}).items():
                env[k] = v
            # Resolve python if set
            if cmd and cmd[0].lower() == "python":
                py = os.getenv("PYTHON_BIN") or sys.executable
                cmd = [py] + cmd[1:]

            lf.write(f"==> [{name}] CMD: {' '.join(cmd)}\n")
            lf.flush()
            print(f"==> RUN [{name}]")
            rc, dur, _ = run_cmd(cmd, cwd=cwd, env=env, log_file=lf)
            status = "success" if rc == 0 else "error"
            summary["steps"].append(
                {
                    "id": name,
                    "cmd": cmd,
                    "rc": rc,
                    "status": status,
                    "duration_sec": round(dur, 2),
                    "log_file": str(log_path),
                }
            )
            if rc != 0 and step.get("continue_on_error") is not True:
                print(f"[STOP] step {name} failed rc={rc}")
                break

    summary["ended_at"] = datetime.utcnow().isoformat() + "Z"
    (out_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[DONE] run_id={run_id} summary={out_dir / 'summary.json'}")


if __name__ == "__main__":
    main()
