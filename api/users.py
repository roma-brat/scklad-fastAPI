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

# Полный список всех страниц системы с группировкой
ALL_SCREENS = [
    # Основные
    {"id": "dashboard", "title": "Главная", "group": "main"},

    # Склад
    {"id": "inventory", "title": "Склад инструментов", "group": "sklad"},
    {"id": "workshop_inventory", "title": "Инструменты на станках", "group": "sklad"},
    {"id": "transactions", "title": "История операций", "group": "sklad"},

    # Производство
    {"id": "details", "title": "Детали (ДСЕ)", "group": "production"},
    {"id": "routes", "title": "Маршруты", "group": "production"},

    # Планирование
    {"id": "planning", "title": "План заказов", "group": "planning"},
    {"id": "planning_calendar", "title": "Календарь", "group": "planning"},
    {"id": "planning_gantt", "title": "Ганта", "group": "planning"},
    {"id": "planning_settings", "title": "Настройки плана", "group": "planning"},

    # Материалы и оборудование
    {"id": "materials", "title": "Материалы", "group": "materials"},
    {"id": "equipment", "title": "Оборудование", "group": "materials"},

    # Администрирование
    {"id": "reports", "title": "Отчёты", "group": "admin"},
    {"id": "import_export", "title": "Импорт/Экспорт", "group": "admin"},
    {"id": "users", "title": "Пользователи", "group": "admin"},
]

# Группировка экранов (только для отображения в UI)
SCREEN_GROUPS = {
    "main": {"title": "Основные", "icons": "fa-home"},
    "sklad": {"title": "Склад", "icons": "fa-boxes"},
    "production": {"title": "Производство", "icons": "fa-cogs"},
    "planning": {"title": "Планирование", "icons": "fa-calendar-alt"},
    "materials": {"title": "Материалы и оборудование", "icons": "fa-layer-group"},
    "admin": {"title": "Администрирование", "icons": "fa-chart-bar"},
}

# Права по умолчанию для ролей (без автоматических)
ROLE_DEFAULT_SCREENS = {
    "user": ["dashboard", "inventory", "transactions"],
    "technologist": ["dashboard", "inventory", "details", "routes", "materials", "transactions"],
    "storekeeper": ["dashboard", "inventory", "transactions", "import_export", "workshop_inventory"],
    "master": ["dashboard", "inventory", "details", "routes", "materials", "equipment", "transactions", "workshop_inventory"],
    "foreman": ["dashboard", "inventory", "details", "routes", "materials", "equipment", "reports", "transactions", "workshop_inventory", "planning", "planning_calendar", "planning_gantt"],
    "admin": [s["id"] for s in ALL_SCREENS],
    "chief_designer": ["dashboard", "details", "routes", "materials", "reports", "planning_settings", "transactions"],
    "chief_engineer": ["dashboard", "inventory", "details", "routes", "materials", "equipment", "reports", "transactions", "workshop_inventory", "planning", "planning_calendar", "planning_gantt"],
    "technologist_designer": ["dashboard", "details", "routes", "materials", "equipment", "transactions", "workshop_inventory"],
    "otk": ["dashboard", "otk"],
}

# Экраны которые добавляются автоматически по роли (НЕ в списке выбора)
ROLE_AUTO_SCREENS = {
    "user": ["my_page"],
    "otk": ["otk", "order_card"],
}

# Роли с кастомным режимом просмотра маршрутов
ROLE_ROUTE_VIEW_MODES = {
    "otk": "all",
    "admin": "all",
}


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
            "all_screens": ALL_SCREENS,
            "screen_groups": SCREEN_GROUPS,
            "role_default_screens": ROLE_DEFAULT_SCREENS,
            "role_auto_screens": ROLE_AUTO_SCREENS,
            "role_route_view_mode": {
                "user": "approved_only",
                "otk": "all",
                "storekeeper": "approved_only",
                "technologist": "approved_only",
                "technologist_designer": "approved_only",
                "master": "approved_only",
                "foreman": "approved_only",
                "chief_designer": "approved_only",
                "chief_engineer": "approved_only",
                "admin": "all",
            },
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

        # Получить текущие permissions чтобы не потерять route_view_mode
        current_perms = None
        if hasattr(db, "get_user_screen_permissions"):
            current_perms = db.get_user_screen_permissions(user_id)

        # Формируем новые permissions как словарь {screens: [...], route_view_mode: "..."}
        if isinstance(current_perms, dict):
            # Сохраняем существующий route_view_mode если он там был
            existing_mode = current_perms.get("route_view_mode", "approved_only")
            screen_data = {
                "screens": screen,
                "route_view_mode": route_view_mode if route_view_mode else existing_mode,
            }
        else:
            screen_data = {
                "screens": screen,
                "route_view_mode": route_view_mode if route_view_mode else "approved_only",
            }

        # Обновить permissions одним запросом (сохраняет и screens и route_view_mode)
        if hasattr(db, "update_user_screen_permissions_dict"):
            db.update_user_screen_permissions_dict(user_id, screen_data)

        # Если админ редактирует себя — обновить сессию
        if user.get("id") == user_id:
            request.session["user"]["screen_permissions"] = screen_data
            request.session["user"]["role"] = role
            request.session["user"]["route_view_mode"] = screen_data["route_view_mode"]

        logger.info(
            f"User {user_id} updated: role={role}, workstations={workstation}, "
            f"screens={screen}, route_view_mode={route_view_mode}, "
            f"screen_data={screen_data}"
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
