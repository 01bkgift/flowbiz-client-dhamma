import os
import subprocess
import time
from pathlib import Path

import httpx

BASE_URL = "http://127.0.0.1:8001"


def wait_ready(timeout=20):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            r = httpx.get(BASE_URL + "/")
            if r.status_code in (200, 302):
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def main():
    cmd = [
        os.getenv("PYTHON_BIN") or "python",
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8001",
        "--log-level",
        "warning",
    ]
    server = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )

    try:
        if not wait_ready():
            raise RuntimeError("Web server not ready on 8001")

        with httpx.Client(base_url=BASE_URL, follow_redirects=True) as c:
            c.get("/")
            r = c.post(
                "/login",
                data={
                    "username": os.getenv("ADMIN_USERNAME", "admin"),
                    "password": os.getenv("ADMIN_PASSWORD", "admin123"),
                },
            )
            assert r.status_code == 200, f"Login failed: {r.status_code}"

            r = c.get("/agents")
            assert r.status_code == 200
            r = c.post("/agents/trend_scout/action", data={"action": "start"})
            assert r.status_code in (200, 302)
            time.sleep(3)
            r = c.get("/agents/trend_scout")
            assert r.status_code == 200

            r = c.post("/wizard/run")
            assert r.status_code in (200, 302)
            time.sleep(5)

        ok = True
        if not Path("output/web_trend_topics.json").exists():
            print("Missing output/web_trend_topics.json")
            ok = False

        pipelines_dir = Path("output/pipelines")
        has_summary = any(
            (p / "summary.json").exists() for p in pipelines_dir.glob("*")
        )
        if not has_summary:
            print("Missing pipeline summary under output/pipelines/*/summary.json")
            ok = False

        if not ok:
            raise SystemExit(1)
        print("Web flow test OK")

    finally:
        try:
            server.terminate()
        except Exception:
            pass


if __name__ == "__main__":
    main()
