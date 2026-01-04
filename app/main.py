import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app import config
from app.auth import (
    check_credentials,
    current_user,
    login_user,
    logout_user,
    require_login,
)
from app.core.agents_registry import AGENTS
from app.core.jobs import JOB_MANAGER

app = FastAPI(title=config.APP_NAME)
app.add_middleware(
    SessionMiddleware,
    secret_key=config.SECRET_KEY,
    session_cookie=config.SESSION_COOKIE,
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


def _redirect(path: str):
    return RedirectResponse(url=path, status_code=302)


# FlowBiz Contract Endpoints
@app.get("/healthz")
async def healthz():
    """FlowBiz health check endpoint"""
    return {
        "status": "ok",
        "service": config.APP_SERVICE_NAME,
        "version": config.FLOWBIZ_VERSION,
    }


@app.get("/v1/meta")
async def meta():
    """FlowBiz metadata endpoint"""
    return {
        "service": config.APP_SERVICE_NAME,
        "environment": config.APP_ENV,
        "version": config.FLOWBIZ_VERSION,
        "build_sha": config.FLOWBIZ_BUILD_SHA,
    }


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    if current_user(request):
        return _redirect("/dashboard")
    hint = "ตั้งค่า ADMIN_USERNAME/ADMIN_PASSWORD ในไฟล์ .env"
    return templates.TemplateResponse(
        request,
        "login.html",
        {"request": request, "app_name": config.APP_NAME, "admin_hint": hint},
    )


@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if check_credentials(username, password):
        login_user(request, username)
        return _redirect("/dashboard")
    hint = "ตั้งค่า ADMIN_USERNAME/ADMIN_PASSWORD ในไฟล์ .env"
    return templates.TemplateResponse(
        request,
        "login.html",
        {
            "request": request,
            "app_name": config.APP_NAME,
            "error": "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง",
            "admin_hint": hint,
        },
        status_code=401,
    )


@app.get("/logout")
async def logout(request: Request):
    logout_user(request)
    return _redirect("/")


@app.get("/forgot", response_class=HTMLResponse)
async def forgot(request: Request):
    return templates.TemplateResponse(
        request,
        "forgot.html",
        {"request": request, "admin_user": config.ADMIN_USERNAME},
    )


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    require_login(request)
    job_states = []
    for a in AGENTS:
        j = JOB_MANAGER.get(a["key"])
        job_states.append(
            {
                "key": a["key"],
                "name": a["name"],
                "status": j.status,
                "progress": j.progress,
            }
        )
    # Warnings for security hygiene
    warnings = []
    if config.SECRET_KEY in ("dev-secret-key-change-me", "change-me"):
        warnings.append("โปรดเปลี่ยน SECRET_KEY ในไฟล์ .env")
    if config.ADMIN_USERNAME == "admin" and config.ADMIN_PASSWORD == "admin123":
        warnings.append(
            "โปรดเปลี่ยนชื่อผู้ใช้/รหัสผ่านเริ่มต้น (ADMIN_USERNAME/ADMIN_PASSWORD) ใน .env"
        )
    # Optional success banner after restart
    restart_ok = request.query_params.get("restarted") in {"1", "true", "yes"}
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "request": request,
            "agents": job_states,
            "warnings": warnings,
            "cfg": config,
            "restart_ok": restart_ok,
        },
    )


@app.get("/agents", response_class=HTMLResponse)
async def agents_list(request: Request):
    require_login(request)
    job_map = {a["key"]: JOB_MANAGER.get(a["key"]) for a in AGENTS}
    return templates.TemplateResponse(
        request,
        "agents.html",
        {"request": request, "agents": AGENTS, "job_map": job_map},
    )


@app.get("/agents/{agent_key}", response_class=HTMLResponse)
async def agent_detail(request: Request, agent_key: str):
    require_login(request)
    agent = next((a for a in AGENTS if a["key"] == agent_key), None)
    if not agent:
        return _redirect("/agents")
    job = JOB_MANAGER.get(agent_key)
    return templates.TemplateResponse(
        request,
        "agent_detail.html",
        {"request": request, "agent": agent, "job": job},
    )


@app.post("/agents/{agent_key}/action")
async def agent_action(request: Request, agent_key: str, action: str = Form(...)):
    require_login(request)
    if action == "start":
        await JOB_MANAGER.start(agent_key)
    elif action == "pause":
        JOB_MANAGER.pause(agent_key)
    elif action == "resume":
        JOB_MANAGER.resume(agent_key)
    elif action == "stop":
        JOB_MANAGER.stop(agent_key)
    elif action == "reset":
        JOB_MANAGER.reset(agent_key)
    elif action == "restart":
        # หยุด -> รีเซ็ต -> เริ่มใหม่
        JOB_MANAGER.stop(agent_key)
        JOB_MANAGER.reset(agent_key)
        await JOB_MANAGER.start(agent_key)
    return _redirect(f"/agents/{agent_key}")


@app.get("/agents/{agent_key}/logs/stream")
async def agent_logs_stream(request: Request, agent_key: str):
    """SSE stream ของสถานะและ log แบบเรียลไทม์สำหรับเอเจนต์ที่เลือก"""
    require_login(request)

    job = JOB_MANAGER.get(agent_key)

    async def event_gen():
        last_idx = 0
        # ส่งสถานะเริ่มต้นทันที
        initial = {"status": job.status, "progress": job.progress}
        yield f"event: status\ndata: {json.dumps(initial, ensure_ascii=False)}\n\n"
        try:
            while True:
                # ส่ง log ใหม่ตั้งแต่ last_idx
                if last_idx < len(job.log):
                    for line in job.log[last_idx:]:
                        # ส่งทีละบรรทัดเป็น event: log
                        payload = json.dumps(line, ensure_ascii=False)
                        yield f"event: log\ndata: {payload}\n\n"
                    last_idx = len(job.log)

                # อัปเดตสถานะ/ความคืบหน้าเป็นระยะ
                status_payload = json.dumps(
                    {"status": job.status, "progress": job.progress},
                    ensure_ascii=False,
                )
                yield f"event: status\ndata: {status_payload}\n\n"

                # หากงานสิ้นสุดหรือผิดพลาดแล้ว ให้ส่งสรุปแล้วจบการสตรีม
                if job.status in ("completed", "error", "stopped"):
                    break

                await asyncio.sleep(0.5)
        except asyncio.CancelledError:  # pragma: no cover
            # ไคลเอนต์ยกเลิกการเชื่อมต่อ
            return

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )


@app.post("/server/restart", response_class=HTMLResponse)
async def server_restart(request: Request, background_tasks: BackgroundTasks):
    """รีสตาร์ทเว็บเซิร์ฟเวอร์: สร้างโปรเซสใหม่ แล้วปิดตัวเดิม"""
    require_login(request)

    def _do_restart():
        try:
            py = os.getenv("PYTHON_BIN") or sys.executable  # type: ignore[name-defined]
        except Exception:  # pragma: no cover
            py = sys.executable  # type: ignore[name-defined]
        # Launch a helper that waits for this process to release the port,
        # then starts uvicorn with the same interpreter.
        cmd = [
            py,
            "-m",
            "app.utils.server_restart",
            "--host",
            config.WEB_HOST,
            "--port",
            str(config.WEB_PORT),
            "--py",
            py,
        ]
        try:
            creationflags = 0
            if os.name == "nt":
                creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            subprocess.Popen(
                cmd,
                cwd=str(Path.cwd()),
                creationflags=creationflags,
            )
        except Exception:
            pass
        # เว้นเวลาเล็กน้อยให้ helper เริ่มทำงาน แล้วปิดโปรเซสปัจจุบัน
        time.sleep(0.2)
        os._exit(0)

    background_tasks.add_task(_do_restart)
    # แจ้งผู้ใช้ให้รอ แล้วเบราว์เซอร์จะเชื่อมต่อใหม่ที่เดิม
    html = (
        "<html><head>\n"
        '  <meta http-equiv="refresh" content="2;url=/dashboard?restarted=1" />\n'
        "</head><body>\n"
        "  <p>กำลังรีสตาร์ทเซิร์ฟเวอร์ โปรดรอสักครู่...</p>\n"
        '  <p>หากไม่ถูกเปลี่ยนหน้าอัตโนมัติ <a href="/dashboard">คลิกที่นี่</a></p>\n'
        "</body></html>"
    )
    return HTMLResponse(content=html, status_code=202)


@app.get("/server/restart", response_class=HTMLResponse)
async def server_restart_get(request: Request):
    """รองรับกรณีผู้ใช้เปิดด้วย GET โดยเผลอคลิกลิงก์/บุ๊กมาร์ก: แสดงปุ่มยืนยัน"""
    require_login(request)
    return HTMLResponse(
        content=(
            "<html><body>\n"
            "<p>ต้องการรีสตาร์ทเซิร์ฟเวอร์หรือไม่?</p>\n"
            '<form method="post" action="/server/restart">\n'
            '<button type="submit">ยืนยัน Restart Server</button>\n'
            "</form>\n"
            '<p><a href="/dashboard">กลับแดชบอร์ด</a></p>\n'
            "</body></html>"
        ),
        status_code=200,
    )


@app.get("/settings", response_class=HTMLResponse)
async def settings_view(request: Request):
    require_login(request)
    return templates.TemplateResponse(
        request,
        "settings.html",
        {"request": request, "cfg": config},
    )


@app.get("/wizard", response_class=HTMLResponse)
async def wizard_view(request: Request):
    require_login(request)
    # Surface minimal config warnings here too
    warnings = []
    if config.SECRET_KEY in ("dev-secret-key-change-me", "change-me"):
        warnings.append("โปรดเปลี่ยน SECRET_KEY ในไฟล์ .env")
    if config.ADMIN_USERNAME == "admin" and config.ADMIN_PASSWORD == "admin123":
        warnings.append(
            "โปรดเปลี่ยนชื่อผู้ใช้/รหัสผ่านเริ่มต้น (ADMIN_USERNAME/ADMIN_PASSWORD) ใน .env"
        )
    return templates.TemplateResponse(
        request,
        "wizard.html",
        {"request": request, "warnings": warnings},
    )


@app.post("/wizard/run")
async def wizard_run(request: Request):
    require_login(request)
    # เรียก Orchestrator Pipeline
    await JOB_MANAGER.start("orchestrator_pipeline")
    return _redirect("/agents/orchestrator_pipeline")
