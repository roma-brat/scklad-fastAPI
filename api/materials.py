"""API роуты для материалов (MaterialInstance)"""

from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from datetime import datetime
import logging

# Lazy imports для избежания циклической зависимости
def _get_db():
    import main
    return main._get_db()

def _get_user(request):
    import main
    return main._get_user(request)

def _require_login(request):
    import main
    return main._require_login(request)

def _is_mobile(request):
    import main
    return main._is_mobile(request)


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/materials", tags=["materials"])
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def materials_list(request: Request):
    """Страница со списком материалов"""
    
    user = _get_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    db = _get_db()
    try:
        materials = db.get_all_material_instances()
    except Exception:
        materials = []

    # Группируем по сортаменту и марке
    grouped = {}
    for m in materials:
        sortament = m.get("sortament_name") or "Без сортамента"
        mark = m.get("mark_name") or "Без марки"
        if sortament not in grouped:
            grouped[sortament] = {}
        if mark not in grouped[sortament]:
            grouped[sortament][mark] = []
        grouped[sortament][mark].append(m)

    # Сортируем
    sorted_grouped = {}
    for sortament in sorted(grouped.keys()):
        sorted_grouped[sortament] = {}
        for mark in sorted(grouped[sortament].keys()):
            sorted_grouped[sortament][mark] = sorted(
                grouped[sortament][mark],
                key=lambda x: (x.get("dimension1") or 0, x.get("dimension2") or 0, x.get("dimension3") or 0)
            )

    return templates.TemplateResponse(
        "materials/list.html",
        {
            "request": request,
            "current_user": user,
            "grouped_materials": sorted_grouped,
        },
    )


@router.post("/create")
async def create_material(request: Request):
    """Создание нового MaterialInstance"""

    user = _get_user(request)
    if not user:
        return JSONResponse({"success": False, "message": "Unauthorized"}, status_code=401)

    try:
        form_data = await request.form()
        mark_name = form_data.get("mark_name", "").strip()
        mark_gost = form_data.get("mark_gost", "").strip() or None
        sortament_name = form_data.get("sortament_name", "").strip()
        sortament_gost = form_data.get("sortament_gost", "").strip() or None
        dim1 = form_data.get("dim1", "").strip() or None
        dim2 = form_data.get("dim2", "").strip() or None
        dim3 = form_data.get("dim3", "").strip() or None

        if not mark_name or not sortament_name:
            return JSONResponse(
                {"success": False, "message": "Марка и сортамент обязательны"},
                status_code=400,
            )

        db = _get_db()
        with db.get_session() as session:
            from sqlalchemy import text
            app_id = f"MAT_{int(datetime.now().timestamp())}"
            result = session.execute(
                text("""
                    INSERT INTO material_instances
                    (mark_name, mark_gost, sortament_name, sortament_gost,
                     dimension1, dimension2, dimension3, created_by, app_id)
                    VALUES (:mark_name, :mark_gost, :sortament_name, :sortament_gost,
                            :dim1, :dim2, :dim3, :created_by, :app_id)
                    RETURNING id
                """),
                {
                    "mark_name": mark_name,
                    "mark_gost": mark_gost,
                    "sortament_name": sortament_name,
                    "sortament_gost": sortament_gost,
                    "dim1": float(dim1) if dim1 else None,
                    "dim2": float(dim2) if dim2 else None,
                    "dim3": float(dim3) if dim3 else None,
                    "created_by": user.get("username") if user else None,
                    "app_id": app_id,
                },
            )
            new_id = result.scalar()
            session.commit()

        logger.info(f"Material created: id={new_id}, mark={mark_name}, sortament={sortament_name}")
        return JSONResponse({"success": True, "material_id": new_id})

    except Exception as e:
        logger.error(f"Create material error: {e}", exc_info=True)
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@router.put("/{material_id}")
async def update_material(request: Request, material_id: int):
    """Обновление MaterialInstance"""

    user = _get_user(request)
    if not user:
        return JSONResponse({"success": False, "message": "Unauthorized"}, status_code=401)

    try:
        form_data = await request.form()
        mark_name = form_data.get("mark_name", "").strip()
        mark_gost = form_data.get("mark_gost", "").strip() or None
        sortament_name = form_data.get("sortament_name", "").strip()
        sortament_gost = form_data.get("sortament_gost", "").strip() or None
        dim1 = form_data.get("dim1", "").strip() or None
        dim2 = form_data.get("dim2", "").strip() or None
        dim3 = form_data.get("dim3", "").strip() or None

        if not mark_name or not sortament_name:
            return JSONResponse(
                {"success": False, "message": "Марка и сортамент обязательны"},
                status_code=400,
            )

        db = _get_db()
        from sqlalchemy import text
        with db.get_session() as session:
            session.execute(
                text("""
                    UPDATE material_instances SET
                        mark_name = :mark_name,
                        mark_gost = :mark_gost,
                        sortament_name = :sortament_name,
                        sortament_gost = :sortament_gost,
                        dimension1 = :dim1,
                        dimension2 = :dim2,
                        dimension3 = :dim3
                    WHERE id = :id
                """),
                {
                    "mark_name": mark_name,
                    "mark_gost": mark_gost,
                    "sortament_name": sortament_name,
                    "sortament_gost": sortament_gost,
                    "dim1": float(dim1) if dim1 else None,
                    "dim2": float(dim2) if dim2 else None,
                    "dim3": float(dim3) if dim3 else None,
                    "id": material_id,
                },
            )
            session.commit()

        logger.info(f"Material updated: id={material_id}")
        return JSONResponse({"success": True})

    except Exception as e:
        logger.error(f"Update material error: {e}", exc_info=True)
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@router.delete("/{material_id}")
async def delete_material(request: Request, material_id: int):
    """Удаление MaterialInstance"""

    user = _get_user(request)
    if not user:
        return JSONResponse({"success": False, "message": "Unauthorized"}, status_code=401)

    try:
        db = _get_db()
        result = db.delete_material_instance(material_id)
        if result:
            logger.info(f"Material deleted: id={material_id}")
            return JSONResponse({"success": True})
        else:
            return JSONResponse({"success": False, "message": "Material not found"}, status_code=404)
    except Exception as e:
        logger.error(f"Delete material error: {e}", exc_info=True)
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@router.get("/api/all")
async def get_all_materials_json(request: Request):
    """API для получения всех материалов в JSON (для автодополнения и т.д.)"""

    user = _get_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    db = _get_db()
    try:
        materials = db.get_all_material_instances()
        return JSONResponse({"success": True, "materials": materials})
    except Exception as e:
        logger.error(f"Get materials error: {e}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)
