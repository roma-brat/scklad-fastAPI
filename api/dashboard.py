"""
API роуты для Dashboard
"""
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from database import DatabaseManager
from main import get_db, get_user, require_login

router = APIRouter(tags=["dashboard"])
templates = Jinja2Templates(directory="templates")


@router.get("/dashboard", response_class=HTMLResponse)
@router.get("/dashboard/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Главная панель"""
    user = get_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    # Получаем статистику
    db = get_db()
    try:
        stats = db.get_statistics()
        # Нормализуем ключи для шаблона
        stats = {
            "total_items": stats.get("total_operations", 0),
            "low_stock_count": stats.get("low_stock_items", 0),
            "today_transactions": stats.get("income_operations", 0) + stats.get("expense_operations", 0),
            "total_users": stats.get("active_users", 0)
        }
    except Exception as e:
        stats = {
            "total_items": 0,
            "low_stock_count": 0,
            "today_transactions": 0,
            "total_users": 0
        }

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "current_user": user,
        "stats": stats
    })
