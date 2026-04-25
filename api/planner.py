"""
Planner API — создание и редактирование маршрутов обработки
Аналог planner_screen_1.py из Flet проекта
"""

import logging
import os
import uuid
import shutil
from fastapi import APIRouter, Request, Form, File, Depends, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from typing import Optional
from database import DatabaseManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/planner", tags=["planner"])

# Директория для PDF файлов маршрутов
ROUTE_PDF_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "route_pdfs")
os.makedirs(ROUTE_PDF_DIR, exist_ok=True)


def get_db() -> DatabaseManager:
    from main import db_manager

    return db_manager


# ========== PLANNER PAGE ==========


@router.get("/", response_class=HTMLResponse)
async def planner_page(request: Request, detail: Optional[str] = None):
    """Страница создания/редактирования маршрута"""
    from main import get_user, require_login

    redirect_resp = require_login(request)
    if redirect_resp:
        return redirect_resp

    user = get_user(request)
    db = get_db()

    # Загружаем справочные данные
    operation_types = db.get_all_operation_types()
    equipment = db.get_all_equipment(active_only=True)
    workshops = db.get_all_workshops()
    cooperatives = db.get_all_cooperatives()
    material_instances = db.get_all_material_instances()

    # Строим структуру для каскадных dropdown материалов
    materials_data = {}
    for mi in material_instances:
        sortament = mi.get("sortament_name") or ""
        mark = mi.get("mark_name") or ""
        if not sortament or not mark:
            continue

        if sortament not in materials_data:
            materials_data[sortament] = {}
        if mark not in materials_data[sortament]:
            materials_data[sortament][mark] = []

        dim_parts = []
        for d_key in ["dimension1", "dimension2", "dimension3"]:
            d_val = mi.get(d_key)
            if d_val is not None:
                dim_parts.append(str(int(d_val)) if d_val == int(d_val) else str(d_val))

        materials_data[sortament][mark].append(
            {
                "id": mi["id"],
                "dimension_str": " х ".join(dim_parts) if dim_parts else "",
                "dimensions": (
                    mi.get("dimension1"),
                    mi.get("dimension2"),
                    mi.get("dimension3"),
                ),
                "mark_name": mark,
                "sortament_name": sortament,
            }
        )

    return templates.TemplateResponse(
        "planner/create_route.html",
        {
            "request": request,
            "current_user": user,
            "prefill_detail": detail,
            "operation_types": operation_types,
            "equipment": equipment,
            "workshops": workshops,
            "cooperatives": cooperatives,
            "materials_data": materials_data,
        },
    )


# ========== MATERIAL INSTANCES API ==========


@router.get("/api/materials")
async def get_materials():
    """Получить все экземпляры материалов для каскадных dropdown"""
    db = get_db()
    instances = db.get_all_material_instances()

    result = {}
    for mi in instances:
        sortament = mi.get("sortament_name") or ""
        mark = mi.get("mark_name") or ""
        if not sortament or not mark:
            continue

        if sortament not in result:
            result[sortament] = {}
        if mark not in result[sortament]:
            result[sortament][mark] = []

        dim_parts = []
        for d_key in ["dimension1", "dimension2", "dimension3"]:
            d_val = mi.get(d_key)
            if d_val is not None:
                dim_parts.append(str(int(d_val)) if d_val == int(d_val) else str(d_val))

        result[sortament][mark].append(
            {
                "id": mi["id"],
                "dimension_str": " х ".join(dim_parts) if dim_parts else "",
                "mark_name": mark,
                "sortament_name": sortament,
            }
        )

    return result


@router.get("/api/materials/{sortament}/{mark}")
async def get_material_by_sortament_mark(sortament: str, mark: str):
    """Получить размеры для конкретного сортамента и марки"""
    db = get_db()
    from sqlalchemy import text

    with db.get_session() as session:
        result = session.execute(
            text("""
                SELECT id, dimension1, dimension2, dimension3
                FROM material_instances
                WHERE sortament_name = :sortament AND mark_name = :mark
                ORDER BY dimension1
            """),
            {"sortament": sortament, "mark": mark},
        )
        rows = result.fetchall()

    materials = []
    for row in rows:
        dim_parts = []
        for d_key in ["dimension1", "dimension2", "dimension3"]:
            d_val = getattr(row, d_key)
            if d_val is not None:
                dim_parts.append(str(int(d_val)) if d_val == int(d_val) else str(d_val))

        materials.append(
            {
                "id": row.id,
                "dimension_str": " х ".join(dim_parts) if dim_parts else "",
            }
        )

    return {"materials": materials}


# ========== OPERATION TYPES + EQUIPMENT ==========


@router.get("/api/operation-types")
async def get_operation_types(workshop_id: Optional[int] = None):
    """Получить типы операций, отфильтрованные по цеху (если указан)"""
    db = get_db()
    if workshop_id:
        ops = db.get_operations_by_workshop(workshop_id)
    else:
        ops = db.get_all_operation_types()
    return {"operation_types": ops}


@router.get("/api/equipment")
async def get_equipment():
    """Получить всё оборудование"""
    db = get_db()
    return {"equipment": db.get_all_equipment(active_only=True)}


@router.get("/api/equipment/by-operation/{operation_type_id}")
async def get_equipment_by_operation(operation_type_id: int):
    """Получить оборудование, подходящее для конкретного типа операции"""
    db = get_db()
    equipment = db.get_equipment_by_operation(operation_type_id)
    return {"equipment": equipment}


# ========== WORKSHOPS & COOPERATIVES ==========


@router.get("/api/workshops")
async def get_workshops():
    """Получить все цеха"""
    db = get_db()
    return {"workshops": db.get_all_workshops()}


@router.get("/api/cooperatives")
async def get_cooperatives():
    """Получить все кооперативы"""
    db = get_db()
    return {"cooperatives": db.get_all_cooperatives()}


@router.get("/api/cooperatives/{coop_id}/operations")
async def get_cooperative_operations(coop_id: int):
    """Получить операции конкретного кооператива"""
    db = get_db()
    operations = db.get_operations_by_cooperative(coop_id)
    return {"operations": operations}


# ========== CREATE / UPDATE ROUTE ==========


@router.post("/save")
async def save_route(
    request: Request,
    detail_name: str = Form(...),
    designation: Optional[str] = Form(None),
    version: Optional[str] = Form(None),
    material_instance_id: Optional[int] = Form(None),
    quantity: int = Form(1),
    length: Optional[int] = Form(None),
    diameter: Optional[int] = Form(None),
    width: Optional[int] = Form(None),
    return_percent: float = Form(0),
    item_type: str = Form("detail"),
    preprocessing: bool = Form(False),
    form_type: Optional[str] = Form(None),
    param_l: Optional[str] = Form(None),
    param_w: Optional[str] = Form(None),
    param_s: Optional[str] = Form(None),
    param_d: Optional[str] = Form(None),
    param_d1: Optional[str] = Form(None),
    operations: str = Form(...),  # JSON string
    route_id: Optional[int] = Form(None),  # Если редактирование
    pdf_file: Optional[UploadFile] = File(None),
):
    """
    Создать или обновить маршрут с операциями.
    operations — JSON массив:
    [
      {"operation_id": 1, "equipment_id": 5, "seq": 1, "duration": 45, "workshop_id": 2, "is_cooperation": false, "notes": ""}
    ]
    """
    import json
    import uuid
    from main import get_user, require_login
    from sqlalchemy import text

    redirect_resp = require_login(request)
    if redirect_resp:
        return redirect_resp

    user = get_user(request)
    db = get_db()
    creator_id = user.get("id") if user else None

    # Логирование для отладки
    logger.info(
        f"Planner save: length={length}, width={width}, dimension1={length}, dimension2={width}"
    )

    try:
        ops_list = json.loads(operations)
    except:
        return JSONResponse({"error": "Неверный формат операций"}, status_code=400)

    # Подготовка preprocessing_data
    pre_data = {
        "preprocessing": preprocessing,
        "return_percent": return_percent,
        "item_type": item_type,
        "width": width or 0,
    }
    if preprocessing and form_type:
        pre_data["form_type"] = form_type
        pre_data["param_l"] = param_l or None
        pre_data["param_w"] = param_w or None
        pre_data["param_s"] = param_s or None
        pre_data["param_d"] = param_d or None
        pre_data["param_d1"] = param_d1 or None

    preprocessing_json = json.dumps(pre_data)

    # Находим или создаём деталь
    detail_id = None
    with db.get_session() as session:
        detail_result = session.execute(
            text("SELECT id FROM details WHERE designation = :designation"),
            {"designation": designation},
        )
        detail_row = detail_result.fetchone()

        if detail_row:
            detail_id = detail_row.id
        else:
            # Создаём новую деталь
            result = session.execute(
                text("""
                    INSERT INTO details (detail_id, detail_type, designation, name, version, is_actual, correct_designation, creator_id)
                    VALUES (:detail_id, :detail_type, :designation, :name, 1.0, true, true, :creator_id)
                    RETURNING id
                """),
                {
                    "detail_id": str(uuid.uuid4()),
                    "detail_type": item_type,
                    "designation": designation,
                    "name": detail_name,
                    "creator_id": creator_id,
                },
            )
            detail_id = result.scalar()
            session.commit()

    # Маппинг полей формы на колонки БД:
    # length (из формы) → dimension1 (БД)
    # width (из формы) → dimension2 (БД)
    dimension1_value = float(length) if length else None
    dimension2_value = float(width) if width else None

    # INSERT или UPDATE маршрута
    # В БД есть И length/diameter, И dimension1/dimension2
    # Обновляем оба набора для совместимости
    if route_id:
        # UPDATE
        with db.get_session() as session:
            session.execute(
                text("""
                    UPDATE detail_routes
                    SET detail_name = :name, designation = :desig, version = :version,
                        material_instance_id = :mat_id, quantity = :qty,
                        length = :dimension1, diameter = :dimension2,
                        dimension1 = :dimension1, dimension2 = :dimension2,
                        preprocessing_data = :pre_data, detail_id = :detail_id,
                        updated_at = NOW()
                    WHERE id = :id
                """),
                {
                    "name": detail_name,
                    "desig": designation,
                    "version": version,
                    "mat_id": material_instance_id,
                    "qty": quantity,
                    "dimension1": dimension1_value,
                    "dimension2": dimension2_value,
                    "pre_data": preprocessing_json,
                    "detail_id": detail_id,
                    "id": route_id,
                },
            )
            session.commit()

        # Удаляем старые операции
        db.delete_route_operations(route_id)

        final_route_id = route_id
    else:
        # INSERT
        with db.get_session() as session:
            result = session.execute(
                text("""
                    INSERT INTO detail_routes
                    (detail_name, designation, version, material_instance_id,
                     created_by, quantity, length, diameter, dimension1,
                     dimension2, preprocessing_data, detail_id)
                    VALUES (:name, :desig, :version, :mat_id, :created_by,
                            :qty, :dimension1, :dimension2, :dimension1,
                            :dimension2, :pre_data, :detail_id)
                    RETURNING id
                """),
                {
                    "name": detail_name,
                    "desig": designation,
                    "version": version,
                    "mat_id": material_instance_id,
                    "created_by": user.get("username") if user else None,
                    "qty": quantity,
                    "dimension1": dimension1_value,
                    "dimension2": dimension2_value,
                    "pre_data": preprocessing_json,
                    "detail_id": detail_id,
                },
            )
            final_route_id = result.scalar()
            session.commit()

            # Сохраняем PDF файл если загружен
            pdf_filename = None
            if pdf_file and pdf_file.filename:
                if not pdf_file.filename.lower().endswith('.pdf'):
                    logger.warning(f"Skipped non-PDF file: {pdf_file.filename}")
                else:
                    try:
                        unique_filename = f"route_{final_route_id}_{uuid.uuid4().hex[:8]}.pdf"
                        file_path = os.path.join(ROUTE_PDF_DIR, unique_filename)

                        with open(file_path, "wb") as buffer:
                            shutil.copyfileobj(pdf_file.file, buffer)

                        pdf_filename = unique_filename
                        session.execute(
                            text("""
                                UPDATE detail_routes
                                SET pdf_file = :pdf_file, pdf_path = :pdf_path
                                WHERE id = :route_id
                            """),
                            {
                                "pdf_file": pdf_filename,
                                "pdf_path": f"/routes/{final_route_id}/pdf",
                                "route_id": final_route_id,
                            }
                        )
                        session.commit()
                        logger.info(f"PDF uploaded for route {final_route_id}: {pdf_filename}")
                    except Exception as pdf_err:
                        logger.error(f"PDF upload error: {pdf_err}")

    # Вставляем операции
    for op in ops_list:
        if op.get("is_cooperation"):
            # Для кооперации — только стоимость и название
            db.add_route_operation(
                route_id=final_route_id,
                operation_type_id=None,
                equipment_id=None,
                sequence_number=int(op["seq"]),
                duration_minutes=int(
                    float(op.get("duration", 0))
                ),  # Это стоимость для кооперации
                notes=op.get("notes") or None,
                workshop_id=None,
                is_cooperation=True,
                coop_company_id=int(op["coop_company_id"])
                if op.get("coop_company_id")
                else None,
                coop_duration_days=int(op.get("coop_duration_days", 0)),
                coop_position=op.get("coop_position", "start"),
            )
        else:
            # Свое производство
            db.add_route_operation(
                route_id=final_route_id,
                operation_type_id=int(op["operation_id"]),
                equipment_id=int(op["equipment_id"]),
                sequence_number=int(op["seq"]),
                duration_minutes=int(op.get("duration", 60)),
                prep_time=int(op.get("prep_time", 0)),
                control_time=int(op.get("control_time", 0)),
                parts_count=int(op.get("parts_count", 1)),
                notes=op.get("notes") or None,
                workshop_id=int(op["workshop_id"]) if op.get("workshop_id") else None,
                is_cooperation=False,
            )

    return JSONResponse(
        {
            "success": True,
            "route_id": final_route_id,
            "detail_name": detail_name,
        }
    )


# ========== DETAIL LOOKUP ==========


@router.get("/api/detail/{designation}")
async def get_detail_by_designation(designation: str):
    """Получить деталь по обозначению (для автозаполнения)"""
    db = get_db()
    from sqlalchemy import text

    with db.get_session() as session:
        result = session.execute(
            text(
                "SELECT id, designation, name, detail_type FROM details WHERE designation = :designation LIMIT 1"
            ),
            {"designation": designation},
        )
        row = result.fetchone()

    if row:
        return {"found": True, "detail": dict(row._mapping)}
    return {"found": False}


# ========== UPDATE EQUIPMENT IN ROUTE ==========


@router.post("/api/routes/{route_id}/update-equipment")
async def update_route_equipment(request: Request, route_id: int):
    """
    Обновить оборудование для операций маршрута.
    Вызывается при выборе альтернативного станка в диалоге конфликтов.

    Body:
    {
        "operations": [
            {"operation_seq": 1, "new_equipment_id": 48},
            {"operation_seq": 2, "new_equipment_id": 49}
        ]
    }
    """
    user = get_user(request)
    if not user:
        return JSONResponse(
            {"success": False, "message": "Не авторизован"}, status_code=401
        )

    db = get_db()
    try:
        body = await request.json()
        operations = body.get("operations", [])

        if not operations:
            return JSONResponse(
                {"success": False, "message": "Нет операций для обновления"},
                status_code=400,
            )

        from sqlalchemy import text

        updated_count = 0
        with db.get_session() as session:
            for op in operations:
                op_seq = op.get("operation_seq")
                new_eq_id = op.get("new_equipment_id")

                if op_seq is None or new_eq_id is None:
                    logger.warning(f"Skipping invalid operation: {op}")
                    continue

                result = session.execute(
                    text("""
                        UPDATE route_operations
                        SET equipment_id = :new_eq_id
                        WHERE route_id = :route_id
                          AND sequence_number = :op_seq
                    """),
                    {"route_id": route_id, "new_eq_id": new_eq_id, "op_seq": op_seq},
                )

                if result.rowcount > 0:
                    updated_count += 1
                    logger.info(
                        f"Updated route {route_id}, op {op_seq}: equipment -> {new_eq_id}"
                    )
                else:
                    logger.warning(f"Operation {op_seq} not found in route {route_id}")

            session.commit()

        return JSONResponse(
            {
                "success": True,
                "updated_count": updated_count,
                "message": f"Обновлено {updated_count} операций",
            }
        )

    except Exception as e:
        logger.error(f"Update route equipment error: {e}", exc_info=True)
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


# ========== MATERIAL CREATION ==========


@router.post("/api/materials/create")
async def create_material(request: Request):
    """Создание нового материала (сортамента с маркой и размерами)"""
    from main import get_user, require_login
    from sqlalchemy import text
    from datetime import datetime

    redirect_resp = require_login(request)
    if redirect_resp:
        return JSONResponse(
            {"success": False, "message": "Unauthorized"}, status_code=401
        )

    user = get_user(request)

    try:
        form_data = await request.form()
        mark_name = form_data.get("mark_name", "").strip()
        mark_gost = form_data.get("mark_gost", "").strip() or None
        sortament_name = form_data.get("sortament_name", "").strip()
        sortament_gost = form_data.get("sortament_gost", "").strip() or None
        dim1 = form_data.get("dim1", "").strip() or None
        dim2 = form_data.get("dim2", "").strip() or None
        dim3 = form_data.get("dim3", "").strip() or None
        price_ton = form_data.get("price_ton", "").strip() or None
        price_piece = form_data.get("price_piece", "").strip() or None

        if not mark_name or not sortament_name:
            return JSONResponse(
                {"success": False, "message": "Марка и сортамент обязательны"},
                status_code=400,
            )

        db = get_db()
        with db.get_session() as session:
            app_id = f"MAT_{int(datetime.now().timestamp())}"
            result = session.execute(
                text("""
                    INSERT INTO material_instances 
                    (mark_name, mark_gost, sortament_name, sortament_gost, 
                     dimension1, dimension2, dimension3, price_per_ton, price_per_piece,
                     created_by, app_id)
                    VALUES (:mark_name, :mark_gost, :sortament_name, :sortament_gost,
                            :dim1, :dim2, :dim3, :price_ton, :price_piece,
                            :created_by, :app_id)
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
                    "price_ton": float(price_ton) if price_ton else None,
                    "price_piece": float(price_piece) if price_piece else None,
                    "created_by": user.get("username") if user else None,
                    "app_id": app_id,
                },
            )
            new_id = result.scalar()
            session.commit()

        return JSONResponse(
            {
                "success": True,
                "material_id": new_id,
                "message": f"Материал '{mark_name}' создан",
            }
        )

    except Exception as e:
        logger.error(f"Create material error: {e}", exc_info=True)
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


# ========== TEMPLATE REFERENCE ==========
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")
