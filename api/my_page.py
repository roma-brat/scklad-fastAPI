"""API роуты для персональной страницы"""

from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from main import get_db, get_user, is_mobile
from typing import Optional

router = APIRouter(prefix="/my-page", tags=["my_page"])
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def my_page(request: Request, search: Optional[str] = Query(None)):
    user = get_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    # Только пользователи с ролью "user" видят эту страницу
    # Остальные роли (admin, technologist и др.) -> на десктопную версию
    if user.get("role") != "user":
        return RedirectResponse(url="/dashboard", status_code=303)

    # Единая страница для всех устройств - адаптивный дизайн
    return templates.TemplateResponse(
        "mobile/my_page.html",
        {
            "request": request,
            "user": user,
        },
    )
