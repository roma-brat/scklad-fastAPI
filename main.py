"""
Склад Инструментов — FastAPI
"""

import os
import logging
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends, Form
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from config import DATABASE_URL, APP_PORT, TIMEZONE
from database import DatabaseManager
from services.auth_service import AuthService
from utils.user_agent import is_mobile as _is_mobile

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)


# ========== GLOBAL STATE ==========
db_manager: DatabaseManager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_manager
    db_manager = DatabaseManager(DATABASE_URL)
    print("✅ Database initialized")
    logger.info("Application startup complete")
    yield
    logger.info("Shutting down")


app = FastAPI(title="Склад Инструментов", version="2.0.0", lifespan=lifespan)

# Session middleware (signed cookie) — replaces manual cookie handling
app.add_middleware(
    SessionMiddleware, secret_key="sklad-secret-key-change-in-production-2024"
)

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


# ========== HTTP LOGGING MIDDLEWARE ==========

class HTTPLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware для логирования HTTP запросов."""

    async def dispatch(self, request: Request, call_next):
        # Логируем запрос
        logger.info(f"{request.method} {request.url.path}")

        response = await call_next(request)

        # Логируем ответ (только ошибки или важные операции)
        if response.status_code >= 400:
            logger.warning(f"  → {response.status_code} {request.url.path}")
        elif request.method in ["POST", "PUT", "DELETE"]:
            logger.info(f"  → {response.status_code}")

        return response


app.add_middleware(HTTPLoggingMiddleware)


# ========== MOBILE DETECTION MIDDLEWARE ==========


class MobileDetectionMiddleware(BaseHTTPMiddleware):
    """Middleware для автоматического определения мобильного устройства."""

    async def dispatch(self, request: Request, call_next):
        request.state.is_mobile = _is_mobile(request)
        return await call_next(request)


app.add_middleware(MobileDetectionMiddleware)

# Flutter service worker - PWA endpoint
@app.get("/flutter_service_worker.js")
async def flutter_service_worker():
    from fastapi.responses import FileResponse
    sw_path = "static/flutter_service_worker.js"
    if os.path.exists(sw_path):
        return FileResponse(sw_path, media_type="application/javascript")
    return JSONResponse({"error": "Not Found"}, status_code=404)

# Static
app.mount("/static", StaticFiles(directory="static"), name="static")
item_images = os.path.join(os.path.dirname(__file__), "item_images")
if os.path.exists(item_images):
    app.mount("/item_images", StaticFiles(directory=item_images), name="item_images")

templates = Jinja2Templates(directory="templates")

# Добавляем фильтр для парсинга JSON в шаблонах
import json

templates.env.filters["from_json"] = lambda s: json.loads(s) if s else {}


# Фильтр для форматирования даты в часовом поясе
def format_datetime_filter(dt):
    if not dt:
        return "-"
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt.replace("+00:00", ""))
    return dt.strftime("%d.%m.%Y %H:%M")


templates.env.filters["datetime"] = format_datetime_filter
templates.env.globals["timezone"] = TIMEZONE


# ========== HELPERS ==========
def get_db() -> DatabaseManager:
    return db_manager


def is_mobile(request: Request) -> bool:
    """Проверить, зашёл ли пользователь с мобильного устройства."""
    return getattr(request.state, "is_mobile", False) or _is_mobile(request)


def get_user(request: Request) -> dict | None:
    """Get user from session"""
    return request.session.get("user")


def require_login(request: Request):
    """Redirect to login if not authenticated"""
    if not get_user(request):
        return RedirectResponse(url="/login", status_code=303)
    return None


# ========== ROUTES ==========


@app.get("/")
async def root(request: Request):
    user = get_user(request)
    if user:
        return RedirectResponse(url="/dashboard", status_code=303)
    return RedirectResponse(url="/login", status_code=303)


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if get_user(request):
        return RedirectResponse(url="/dashboard", status_code=303)
    return templates.TemplateResponse("mobile/login.html", {"request": request})


@app.post("/login")
async def login_submit(
    request: Request,
    login: str = Form(...),
    password: str = Form(...),
):
    db = get_db()
    auth = AuthService(db)
    session = auth.login(login, password)

    if session:
        # Загружаем screen_permissions из БД
        screen_perms = None
        route_view_mode = "approved_only"
        if hasattr(db_manager, "get_user_screen_permissions"):
            screen_perms = db_manager.get_user_screen_permissions(session.user.id)
        if hasattr(db_manager, "get_user_route_view_mode"):
            route_view_mode = db_manager.get_user_route_view_mode(session.user.id)

        request.session["user"] = {
            "id": session.user.id,
            "username": session.user.username,
            "login": session.user.login,
            "role": str(session.user.role),
            "workstation": session.user.workstation,
            "workstations": session.user.workstations,
            "screen_permissions": screen_perms,
            "route_view_mode": route_view_mode,
        }
        return RedirectResponse(url="/dashboard", status_code=303)

    return templates.TemplateResponse(
        "auth/login.html",
        {
            "request": request,
            "error_message": "Неверный логин или пароль",
            "login": login,
        },
    )


# Совместимость — редирект /api/auth/login → /login
@app.get("/api/auth/login")
async def login_compat_get(request: Request):
    return RedirectResponse(url="/login", status_code=303)


@app.post("/api/auth/logout")
async def logout_compat(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)


@app.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    db = get_db()
    equipment = db.get_all_equipment()
    return templates.TemplateResponse(
        "auth/register.html",
        {
            "request": request,
            "equipment": equipment,
        },
    )


@app.post("/register")
async def register_submit(
    request: Request,
    login: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    workstations: str = Form(None),
):
    if password != confirm_password:
        return templates.TemplateResponse(
            "auth/register.html",
            {
                "request": request,
                "error_message": "Пароли не совпадают",
            },
        )

    db = get_db()
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

    return templates.TemplateResponse(
        "auth/register.html",
        {
            "request": request,
            "error_message": "Пользователь с таким логином уже существует",
        },
    )


# ========== DASHBOARD ==========


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    redirect_resp = require_login(request)
    if redirect_resp:
        return redirect_resp

    user = get_user(request)
    db = get_db()

    try:
        stats = db.get_statistics()
    except Exception:
        stats = {
            "total_items": 0,
            "low_stock_count": 0,
            "today_transactions": 0,
            "total_users": 0,
        }

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "current_user": user,
            "stats": stats,
        },
    )


# ========== HEALTH ==========


@app.get("/health")
async def health_check():
    return {"status": "ok", "database": "connected" if db_manager else "disconnected"}


# ========== IMPORT ALL API ROUTES ==========
from api import items, transactions, users, details, routes, materials
from api import (
    planning,
    equipment,
    reports,
    import_export,
    my_page,
    mobile_api,
    planner,
    otk,
    order_card,
)

app.include_router(items.router)
app.include_router(transactions.router)
app.include_router(users.router)
app.include_router(details.router)
app.include_router(routes.router)
app.include_router(planning.router)
app.include_router(equipment.router)
app.include_router(reports.router)
app.include_router(import_export.router)
app.include_router(my_page.router)
app.include_router(mobile_api.router)
app.include_router(planner.router)
app.include_router(otk.router)
app.include_router(order_card.router)
app.include_router(materials.router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=APP_PORT)
