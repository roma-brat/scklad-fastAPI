"""API роуты для ОТК (Отдел Технического Контроля)"""

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/otk", tags=["otk"])
templates = Jinja2Templates(directory="templates")


def get_db():
    """Получить DatabaseManager"""
    from main import get_db as _get_db

    return _get_db()


def get_user(request: Request):
    """Получить пользователя из сессии"""
    return request.session.get("user")


def require_otk(request: Request):
    """Проверить роль ОТК"""
    user = get_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if user.get("role") != "otk":
        return RedirectResponse(url="/dashboard", status_code=303)
    return None


@router.get("/", response_class=HTMLResponse)
async def otk_page(request: Request):
    """Страница ОТК"""
    redirect_resp = require_otk(request)
    if redirect_resp:
        return redirect_resp

    user = get_user(request)
    db = get_db()

    otk_tasks = db.get_otk_pending_tasks()

    return templates.TemplateResponse(
        "otk_page.html",
        {
            "request": request,
            "current_user": user,
            "otk_tasks": otk_tasks,
        },
    )


@router.get("/api/tasks", response_class=JSONResponse)
async def otk_api_tasks(request: Request):
    """API: получить задачи на проверку"""
    redirect_resp = require_otk(request)
    if redirect_resp:
        return JSONResponse(
            {"success": False, "message": "Access denied"}, status_code=403
        )

    db = get_db()
    tasks = db.get_otk_pending_tasks()

    return JSONResponse({"success": True, "tasks": tasks})


@router.post("/api/approve")
async def otk_api_approve(request: Request, schedule_id: int = Form(...)):
    """API: подтвердить проверку (всё хорошо)"""
    redirect_resp = require_otk(request)
    if redirect_resp:
        return JSONResponse(
            {"success": False, "message": "Access denied"}, status_code=403
        )

    user = get_user(request)
    db = get_db()

    ok = db.create_schedule_event(schedule_id, "first_piece_checked", user["username"])

    if ok:
        db.create_otk_event(schedule_id, "otk_approved", user["username"])

    return JSONResponse(
        {"success": ok, "message": "Деталь проверена, все хорошо" if ok else "Ошибка"}
    )


@router.post("/api/reject")
async def otk_api_reject(
    request: Request, schedule_id: int = Form(...), comment: str = Form("")
):
    """API: замечание (есть проблемы)"""
    redirect_resp = require_otk(request)
    if redirect_resp:
        return JSONResponse(
            {"success": False, "message": "Access denied"}, status_code=403
        )

    if not comment or not comment.strip():
        return JSONResponse(
            {"success": False, "message": "Введите комментарий"}, status_code=400
        )

    user = get_user(request)
    db = get_db()

    ok = db.create_otk_event(schedule_id, "otk_rejected", user["username"], comment)

    return JSONResponse(
        {"success": ok, "message": "Замечание отправлено" if ok else "Ошибка"}
    )


@router.get("/cards", response_class=HTMLResponse)
async def otk_cards_page(request: Request):
    """Страница ОТК - ЭМК (список заказов)"""
    redirect_resp = require_otk(request)
    if redirect_resp:
        return redirect_resp

    user = get_user(request)

    return templates.TemplateResponse(
        "otk/cards.html",
        {
            "request": request,
            "current_user": user,
        },
    )
