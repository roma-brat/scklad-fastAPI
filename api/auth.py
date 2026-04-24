"""
API роуты для аутентификации
"""

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from database import DatabaseManager
from main import get_db, get_user, require_login
from services.auth_service import AuthService

router = APIRouter(prefix="/api/auth", tags=["auth"])
templates = Jinja2Templates(directory="templates")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Страница входа"""
    # Если уже залогинен - редирект на дашборд
    if get_user(request):
        return RedirectResponse(url="/dashboard", status_code=303)
    return templates.TemplateResponse("auth/login.html", {"request": request})


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Страница регистрации"""
    db = get_db()
    equipment = db.get_all_equipment()
    return templates.TemplateResponse(
        "auth/register.html", {"request": request, "equipment": equipment}
    )


@router.post("/login")
async def login(
    request: Request,
    login: str = Form(...),
    password: str = Form(...),
):
    """Обработка входа"""
    db = get_db()

    # Сначала пробуем через AuthService (с сессиями)
    auth_service = AuthService(db)
    session = auth_service.login(login, password)

    if session:
        # Определяем URL для редиректа по роли
        user_role = session.user.role
        if user_role == "otk":
            redirect_url = "/otk"
        else:
            redirect_url = "/dashboard"

        response = RedirectResponse(url=redirect_url, status_code=303)
        response.set_cookie(
            key="session_id", value=str(session.user.id), path="/", samesite="lax"
        )
        return response
    else:
        return templates.TemplateResponse(
            "auth/login.html",
            {
                "request": request,
                "error_message": "Неверный логин или пароль",
                "login": login,
            },
        )


@router.post("/register")
async def register(
    request: Request,
    login: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    workstations: str = Form(None),
):
    """Обработка регистрации"""
    db = get_db()

    # Валидация паролей
    if password != confirm_password:
        return templates.TemplateResponse(
            "auth/register.html",
            {"request": request, "error_message": "Пароли не совпадают"},
        )

    # Создание пользователя
    user = db.create_user(
        login=login,
        username=username,
        password=password,
        role="user",
        workstations=workstations,
    )

    if user:
        return templates.TemplateResponse(
            "auth/login.html",
            {
                "request": request,
                "success_message": "Регистрация успешна! Теперь войдите.",
            },
        )
    else:
        return templates.TemplateResponse(
            "auth/register.html",
            {
                "request": request,
                "error_message": "Пользователь с таким логином уже существует",
            },
        )


@router.post("/logout")
async def logout(request: Request):
    """Выход из системы"""
    response = RedirectResponse(url="/api/auth/login")
    response.delete_cookie(key="session_id", path="/")
    return response
