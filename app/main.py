from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
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


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    if current_user(request):
        return _redirect("/dashboard")
    hint = f"{config.ADMIN_USERNAME}/{config.ADMIN_PASSWORD}"
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "app_name": config.APP_NAME, "admin_hint": hint},
    )


@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if check_credentials(username, password):
        login_user(request, username)
        return _redirect("/dashboard")
    hint = f"{config.ADMIN_USERNAME}/{config.ADMIN_PASSWORD}"
    return templates.TemplateResponse(
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
        "forgot.html",
        {
            "request": request,
            "admin_user": config.ADMIN_USERNAME,
            "admin_pass": config.ADMIN_PASSWORD,
        },
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
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "agents": job_states, "warnings": warnings},
    )


@app.get("/agents", response_class=HTMLResponse)
async def agents_list(request: Request):
    require_login(request)
    job_map = {a["key"]: JOB_MANAGER.get(a["key"]) for a in AGENTS}
    return templates.TemplateResponse(
        "agents.html", {"request": request, "agents": AGENTS, "job_map": job_map}
    )


@app.get("/agents/{agent_key}", response_class=HTMLResponse)
async def agent_detail(request: Request, agent_key: str):
    require_login(request)
    agent = next((a for a in AGENTS if a["key"] == agent_key), None)
    if not agent:
        return _redirect("/agents")
    job = JOB_MANAGER.get(agent_key)
    return templates.TemplateResponse(
        "agent_detail.html", {"request": request, "agent": agent, "job": job}
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
    return _redirect(f"/agents/{agent_key}")


@app.get("/settings", response_class=HTMLResponse)
async def settings_view(request: Request):
    require_login(request)
    return templates.TemplateResponse(
        "settings.html", {"request": request, "cfg": config}
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
        "wizard.html", {"request": request, "warnings": warnings}
    )


@app.post("/wizard/run")
async def wizard_run(request: Request):
    require_login(request)
    # เรียก Orchestrator Pipeline
    await JOB_MANAGER.start("orchestrator_pipeline")
    return _redirect("/agents/orchestrator_pipeline")
