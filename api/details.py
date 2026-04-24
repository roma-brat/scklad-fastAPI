"""API роуты для деталей"""
from fastapi import APIRouter, Request, Query, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from main import get_db, get_user
from typing import Optional
from sqlalchemy import text
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/details", tags=["details"])
templates = Jinja2Templates(directory="templates")


def _serialize_detail(detail: dict) -> dict:
    """Сериализация детали для JSON/шаблона"""
    result = detail.copy()
    
    # Преобразуем datetime в строку
    created_at = result.get("created_at")
    if isinstance(created_at, datetime):
        result["created_at"] = created_at.isoformat()
    
    return result


@router.get("/", response_class=HTMLResponse)
async def details_list(
    request: Request,
    search: Optional[str] = Query(None),
    sort_by: Optional[str] = Query("designation"),
    sort_order: Optional[str] = Query("asc"),
):
    user = get_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    db = get_db()
    try:
        # Получаем все детали
        details = db.get_all_details()

        # Добавляем информацию о маршрутах (как в Flet версии)
        routes_map = {}
        with db.get_session() as session:
            result = session.execute(
                text("""
                SELECT dr.designation, dr.id, dr.detail_name, dr.version, dr.approved, dr.created_at,
                       mi.mark_name, mi.sortament_name
                FROM detail_routes dr
                LEFT JOIN material_instances mi ON dr.material_instance_id = mi.id
                ORDER BY dr.created_at DESC
            """)
            )
            for row in result:
                des = row.designation
                if des not in routes_map:
                    routes_map[des] = {
                        "route_id": row.id,
                        "route_name": row.detail_name,
                        "route_version": row.version,
                        "route_approved": row.approved,
                        "route_material": f"{row.mark_name} {row.sortament_name}" if row.mark_name else "",
                    }

        # Присоединяем маршруты к деталям
        for detail in details:
            designation = detail.get("designation", "")
            route = routes_map.get(designation)

            detail["has_route"] = route is not None
            if route:
                detail["route_id"] = route["route_id"]
                detail["route_name"] = route["route_name"]
                detail["route_version"] = route["route_version"]
                detail["route_approved"] = route["route_approved"]
                detail["route_material"] = route["route_material"]

        # Сериализуем все детали (datetime → строка) ДО фильтрации
        all_details_serialized = [_serialize_detail(d) for d in details]

        # Фильтрация по поиску (для отображения таблицы)
        if search:
            query = search.lower()
            details = [
                d for d in details
                if query in (d.get("designation") or "").lower()
                or query in (d.get("name") or "").lower()
                or query in (d.get("detail_id") or "").lower()
            ]

        # Сортировка
        if sort_by == "designation":
            details.sort(
                key=lambda x: (x.get("designation") or "").lower(),
                reverse=(sort_order == "desc"),
            )
        elif sort_by == "name":
            details.sort(
                key=lambda x: (x.get("name") or "").lower(),
                reverse=(sort_order == "desc"),
            )
        elif sort_by == "date":
            details.sort(
                key=lambda x: x.get("created_at") or "",
                reverse=(sort_order == "desc"),
            )

        # Сериализуем отфильтрованные для таблицы
        filtered_details_serialized = [_serialize_detail(d) for d in details]

        all_details_json = json.dumps(all_details_serialized, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Error getting details: {e}")
        all_details_serialized = []
        filtered_details_serialized = []
        all_details_json = "[]"

    return templates.TemplateResponse("details/list.html", {
        "request": request,
        "current_user": user,
        "details": filtered_details_serialized,
        "all_details_json": all_details_json,  # ВСЕ детали для клиентского поиска
        "search": search,
        "sort_by": sort_by,
        "sort_order": sort_order,
        "total_count": len(all_details_serialized),
        "highlight_route_id": request.query_params.get("highlight_route"),
    })


@router.post("/create")
async def create_detail(
    request: Request,
    designation: str = Form(...),
    name: str = Form(...),
    detail_type: str = Form("detail"),
    version: float = Form(1.0),
):
    user = get_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    db = get_db()
    try:
        new_detail = db.create_detail(
            designation=designation,
            name=name,
            detail_type="Сборочная единица" if detail_type == "assembly" else "Деталь",
            creator_id=user.get("id"),
            version=version,
        )

        if new_detail:
            logger.info(f"Detail created: {designation}")
        else:
            logger.error(f"Failed to create detail: {designation}")

    except Exception as e:
        logger.error(f"Create detail error: {e}")

    return RedirectResponse(url="/details", status_code=303)


@router.post("/delete/{detail_id}")
async def delete_detail(request: Request, detail_id: int):
    user = get_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    db = get_db()
    try:
        result = db.delete_detail(detail_id)
        if result:
            logger.info(f"Detail deleted: {detail_id}")
        else:
            logger.error(f"Failed to delete detail: {detail_id}")
    except Exception as e:
        logger.error(f"Delete detail error: {e}")

    return RedirectResponse(url="/details", status_code=303)


@router.get("/{detail_id}", response_class=HTMLResponse)
async def detail_info(request: Request, detail_id: int):
    user = get_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    db = get_db()
    try:
        detail = db.get_detail_by_id(detail_id)

        # Добавляем информацию о маршруте
        if detail:
            with db.get_session() as session:
                result = session.execute(
                    text("""
                    SELECT dr.id, dr.detail_name, dr.version, dr.approved, dr.created_at,
                           mi.mark_name, mi.sortament_name
                    FROM detail_routes dr
                    LEFT JOIN material_instances mi ON dr.material_instance_id = mi.id
                    WHERE dr.designation = :designation
                    ORDER BY dr.created_at DESC
                    LIMIT 1
                """),
                    {"designation": detail.get("designation")},
                )
                route = result.fetchone()

                if route:
                    detail["has_route"] = True
                    detail["route_id"] = route.id
                    detail["route_name"] = route.detail_name
                    detail["route_version"] = route.version
                    detail["route_approved"] = route.approved
                    detail["route_material"] = (
                        f"{route.mark_name} {route.sortament_name}" if route.mark_name else ""
                    )
                else:
                    detail["has_route"] = False

        return templates.TemplateResponse("details/info.html", {
            "request": request,
            "current_user": user,
            "detail": detail,
        })
    except Exception as e:
        logger.error(f"Error getting detail info: {e}")
        return RedirectResponse(url="/details", status_code=303)
