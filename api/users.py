"""API роуты для пользователей"""

from fastapi import APIRouter, Request, Query, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from main import get_db, get_user
from typing import Optional
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["users"])
templates = Jinja2Templates(directory="templates")

# Роли как в Flet версии
ROLE_OPTIONS = [
    ("user", "Пользователь"),
    ("technologist", "Технолог"),
    ("master", "Мастер цеха"),
    ("foreman", "Начальник цеха"),
    ("admin", "Администратор"),
    ("storekeeper", "Кладовщик"),
    ("chief_designer", "Главный конструктор"),
    ("chief_engineer", "Главный инженер проекта"),
    ("technologist_designer", "Технолог-конструктор"),
    ("otk", "ОТК"),
]


@router.get("/", response_class=HTMLResponse)
async def users_list(request: Request, search: Optional[str] = Query(None)):
    user = get_user(request)
    if not user or user.get("role") != "admin":
        return RedirectResponse(url="/dashboard", status_code=303)

    db = get_db()
    try:
        users = db.get_all_users()
        equipment = db.get_all_equipment()
    except Exception as e:
        logger.error(f"Users load error: {e}")
        users = []
        equipment = []

    # Сериализация пользователей
    serialized_users = []
    for u in users:
        serialized_users.append(
            {
                "id": u.get("id"),
                "username": u.get("username", ""),
                "login": u.get("login", ""),
                "role": u.get("role", "user"),
                "workstations": u.get("workstations", ""),
                "is_active": u.get("is_active", True),
                "created_at": str(u.get("created_at", "")),
            }
        )

    # JSON для клиентского поиска
    all_users_json = json.dumps(serialized_users, ensure_ascii=False)

    # Список станков
    equipment_list = []
    for eq in equipment:
        equipment_list.append(
            {
                "id": eq.get("id"),
                "name": eq.get("name", ""),
            }
        )

    return templates.TemplateResponse(
        "users/list.html",
        {
            "request": request,
            "current_user": user,
            "users": serialized_users,
            "all_users_json": all_users_json,
            "equipment": equipment_list,
            "search": search,
            "role_options": ROLE_OPTIONS,
        },
    )


@router.post("/update")
async def update_user(
    request: Request,
    user_id: int = Form(...),
    role: str = Form("user"),
    workstation: list[str] = Form([]),
    route_view_mode: str = Form("approved_only"),
    screen: list[str] = Form([]),
):
    user = get_user(request)
    if not user or user.get("role") != "admin":
        return RedirectResponse(url="/dashboard", status_code=303)

    db = get_db()
    try:
        # Обновить роль
        db.update_user_role(user_id, role)

        # Обновить станки (собрать из checkbox)
        workstations_json = json.dumps(workstation)
        db.update_user_workstations(user_id, workstations_json)

        # Обновить режим просмотра маршрутов
        if hasattr(db, "update_user_route_view_mode"):
            db.update_user_route_view_mode(user_id, route_view_mode)

        # Обновить права экранов
        if hasattr(db, "update_user_screen_permissions"):
            db.update_user_screen_permissions(user_id, screen)

        # Если админ редактирует себя — обновить сессию
        if user.get("id") == user_id:
            request.session["user"]["screen_permissions"] = screen
            request.session["user"]["role"] = role

        logger.info(
            f"User {user_id} updated: role={role}, workstations={workstation}, screens={screen}"
        )
    except Exception as e:
        logger.error(f"User update error: {e}")

    return RedirectResponse(url="/users", status_code=303)


@router.post("/toggle_active")
async def toggle_user_active(request: Request, user_id: int = Form(...)):
    user = get_user(request)
    if not user or user.get("role") != "admin":
        return RedirectResponse(url="/dashboard", status_code=303)

    db = get_db()
    try:
        db.toggle_user_active(user_id)
        logger.info(f"User {user_id} toggled active")
    except Exception as e:
        logger.error(f"Toggle active error: {e}")

    return RedirectResponse(url="/users", status_code=303)


@router.post("/delete")
async def delete_user(request: Request, user_id: int = Form(...)):
    user = get_user(request)
    if not user or user.get("role") != "admin":
        return RedirectResponse(url="/dashboard", status_code=303)

    db = get_db()
    try:
        db.delete_user(user_id)
        logger.info(f"User {user_id} deleted")
    except Exception as e:
        logger.error(f"Delete user error: {e}")

    return RedirectResponse(url="/users", status_code=303)


@router.get("/api/{user_id}")
async def get_user_details(request: Request, user_id: int):
    """Получить детали пользователя для модального окна"""
    user = get_user(request)
    if not user or user.get("role") != "admin":
        return JSONResponse({"error": "Unauthorized"}, status_code=403)

    db = get_db()
    try:
        users = db.get_all_users()
        target_user = next((u for u in users if u.get("id") == user_id), None)

        if not target_user:
            return JSONResponse({"error": "User not found"}, status_code=404)

        # Получить права экранов
        screen_permissions = []
        if hasattr(db, "get_user_screen_permissions"):
            screen_permissions = db.get_user_screen_permissions(user_id)

        # Получить режим просмотра маршрутов
        route_view_mode = "approved_only"
        if hasattr(db, "get_user_route_view_mode"):
            route_view_mode = db.get_user_route_view_mode(user_id)

        return JSONResponse(
            {
                "success": True,
                "user": {
                    "id": target_user.get("id"),
                    "username": target_user.get("username", ""),
                    "login": target_user.get("login", ""),
                    "role": target_user.get("role", "user"),
                    "workstations": target_user.get("workstations", ""),
                    "is_active": target_user.get("is_active", True),
                },
                "screen_permissions": screen_permissions,
                "route_view_mode": route_view_mode,
            }
        )
    except Exception as e:
        logger.error(f"Get user details error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)
