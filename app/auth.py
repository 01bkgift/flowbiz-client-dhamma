from fastapi import HTTPException, Request

from app import config

SESSION_USER_KEY = "user"


def login_user(request: Request, username: str):
    request.session[SESSION_USER_KEY] = {"username": username}


def logout_user(request: Request):
    request.session.pop(SESSION_USER_KEY, None)


def current_user(request: Request):
    return request.session.get(SESSION_USER_KEY)


def require_login(request: Request):
    if not current_user(request):
        raise HTTPException(status_code=401)


def check_credentials(username: str, password: str) -> bool:
    return username == config.ADMIN_USERNAME and password == config.ADMIN_PASSWORD
