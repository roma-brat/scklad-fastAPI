"""API роуты для маршрутов"""

from fastapi import APIRouter, Request, Query, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, FileResponse
from fastapi.templating import Jinja2Templates
from main import get_db, get_user
from typing import Optional
from datetime import datetime
import logging
import math
import os
import json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/routes", tags=["routes"])
templates = Jinja2Templates(directory="templates")

# Добавляем фильтр для парсинга JSON в шаблонах
templates.env.filters["from_json"] = lambda s: json.loads(s) if s else {}


@router.get("/", response_class=HTMLResponse)
async def routes_list(
    request: Request,
    search: Optional[str] = Query(None),
    approved_only: bool = Query(False),
    sort_by: str = Query("date_desc"),
    highlight_detail_id: Optional[str] = Query(None),
):
    user = get_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    db = get_db()

    # Проверяем route_view_mode пользователя
    # Если в БД установлен режим 'approved_only' — показываем только утверждённые по умолчанию
    user_id = user.get("id")
    route_view_mode = "all"  # По умолчанию показываем все
    if user_id and hasattr(db, "get_user_route_view_mode"):
        saved_mode = db.get_user_route_view_mode(user_id)
        if saved_mode == "approved_only":
            route_view_mode = "approved_only"
            approved_only = True  # Автоматически фильтруем

    try:
        routes = db.get_all_routes()
    except Exception:
        routes = []

    # Фильтрация по статусу
    if approved_only:
        routes = [r for r in routes if r.get("approved", False)]

    # Поиск
    if search:
        q = search.lower()
        routes = [
            r
            for r in routes
            if q in (r.get("detail_name") or "").lower()
            or q in (r.get("designation") or "").lower()
            or q in (r.get("version") or "").lower()
        ]

    # Сортировка
    if sort_by == "date_asc":
        routes = sorted(routes, key=lambda x: x.get("created_at", ""))
    elif sort_by == "name_asc":
        routes = sorted(routes, key=lambda x: (x.get("detail_name") or "").lower())
    else:  # date_desc
        routes = sorted(routes, key=lambda x: x.get("created_at", ""), reverse=True)

    # Роли для утверждения
    APPROVER_ROLES = {
        "admin",
        "chief_designer",
        "chief_engineer",
        "technologist_designer",
        "technologist",
    }
    can_approve = user.get("role") in APPROVER_ROLES
    is_admin = user.get("role") == "admin"

    return templates.TemplateResponse(
        "routes/list.html",
        {
            "request": request,
            "current_user": user,
            "routes": routes,
            "search": search,
            "approved_only": approved_only,
            "sort_by": sort_by,
            "highlight_detail_id": highlight_detail_id,
            "can_approve": can_approve,
            "is_admin": is_admin,
            "route_view_mode": route_view_mode,
        },
    )


@router.get("/create", response_class=HTMLResponse)
async def create_route_page(
    request: Request, detail_designation: Optional[str] = Query(None)
):
    """Страница создания маршрута"""
    user = get_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    db = get_db()
    try:
        details = db.get_all_details()
        materials = db.get_all_materials() if hasattr(db, "get_all_materials") else []
        workshops = db.get_all_workshops() if hasattr(db, "get_all_workshops") else []
        operation_types = (
            db.get_all_operation_types()
            if hasattr(db, "get_all_operation_types")
            else []
        )
        equipment_list = (
            db.get_all_equipment() if hasattr(db, "get_all_equipment") else []
        )
        cooperatives = (
            db.get_cooperative_companies()
            if hasattr(db, "get_cooperative_companies")
            else []
        )

        # Получаем уникальные сортаменты и строим materials_data для каскадных dropdown
        sortaments = []
        materials_data = {}
        if hasattr(db, "get_all_material_instances"):
            instances = db.get_all_material_instances()
            for mi in instances:
                sortament = mi.get("sortament_name") or ""
                mark = mi.get("mark_name") or ""
                if not sortament or not mark:
                    continue

                if sortament not in sortaments:
                    sortaments.append(sortament)

                if sortament not in materials_data:
                    materials_data[sortament] = {}
                if mark not in materials_data[sortament]:
                    materials_data[sortament][mark] = []

                dim_parts = []
                for d_key in ["dimension1", "dimension2", "dimension3"]:
                    d_val = mi.get(d_key)
                    if d_val is not None:
                        dim_parts.append(
                            str(int(d_val)) if d_val == int(d_val) else str(d_val)
                        )

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

            sortaments = sorted(sortaments)
    except Exception as e:
        logger.error(f"Error loading route form data: {e}")
        details = []
        materials = []
        workshops = []
        operation_types = []
        equipment_list = []
        cooperatives = []
        sortaments = []
        materials_data = {}

    return templates.TemplateResponse(
        "routes/create.html",
        {
            "request": request,
            "current_user": user,
            "details": details,
            "materials": materials,
            "workshops": workshops,
            "operation_types": operation_types,
            "equipment_list": equipment_list,
            "cooperatives": cooperatives,
            "sortaments": sortaments,
            "materials_data": materials_data,
            "detail_designation": detail_designation,
        },
    )


@router.post("/create")
async def create_route(
    request: Request,
    detail_name: str = Form(...),
    designation: str = Form(...),
    version: str = Form("1.0"),
    material_instance_id: int = Form(None),
    quantity: int = Form(1),
    length: float = Form(None),
    width: float = Form(None),
    waste_percent: float = Form(0),
    operations: str = Form(...),
):
    """Создание нового маршрута"""
    user = get_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    import json

    db = get_db()
    try:
        logger.info(
            f"Creating route: detail_name={detail_name}, length={length}, width={width}, quantity={quantity}, waste_percent={waste_percent}"
        )

        # Создаем маршрут
        route = db.create_route(
            detail_name=detail_name,
            designation=designation,
            material_instance_id=material_instance_id,
            created_by=user.get("username"),
            quantity=quantity,
        )

        if route:
            route_id = route["id"]

            # Обновляем параметры заготовки
            update_params = {}
            if length is not None:
                update_params["dimension1"] = length
            if width is not None:
                update_params["dimension2"] = width
            if waste_percent is not None:
                update_params["waste_percent"] = waste_percent

            if update_params:
                db.update_route(route_id=route_id, **update_params)

            # Добавляем операции
            ops_data = json.loads(operations)
            for idx, op in enumerate(ops_data, 1):
                db.add_route_operation(
                    route_id=route_id,
                    operation_type_id=op.get("operation_type_id"),
                    equipment_id=op.get("equipment_id"),
                    sequence_number=idx,
                    duration_minutes=op.get("duration_minutes"),
                    notes=op.get("notes"),
                    workshop_id=op.get("workshop_id"),
                    is_cooperation=op.get("is_cooperation", False),
                    coop_company_id=op.get("coop_company_id"),
                    coop_duration_days=op.get("coop_duration_days", 0),
                    coop_position=op.get("coop_position", "start"),
                )

            logger.info(f"Route created: {route_id}")

        return RedirectResponse(
            url=f"/routes?highlight_detail_id={designation}", status_code=303
        )

    except Exception as e:
        logger.error(f"Create route error: {e}")
        import traceback

        traceback.print_exc()
        return RedirectResponse(url="/routes/create", status_code=303)


@router.post("/{route_id}/duplicate")
async def duplicate_route(request: Request, route_id: int):
    """Дублирование маршрута с увеличением версии"""
    user = get_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    db = get_db()
    try:
        result = db.copy_route_with_operations(
            route_id, created_by=user.get("username")
        )
        if result:
            logger.info(
                f"Route {route_id} duplicated to {result['id']} (v{result['version']})"
            )
            return RedirectResponse(url=f"/routes/{result['id']}/edit", status_code=303)
        else:
            logger.error(f"Failed to duplicate route {route_id}")
    except Exception as e:
        logger.error(f"Duplicate route error: {e}")

    return RedirectResponse(url="/routes", status_code=303)


@router.get("/{route_id}", response_class=HTMLResponse)
async def view_route(request: Request, route_id: int):
    """Просмотр маршрута"""
    user = get_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    db = get_db()
    try:
        route = db.get_route_by_id(route_id)

        if not route:
            return RedirectResponse(url="/routes", status_code=303)

        route_operations = db.get_route_operations(route_id)

        # Загружаем справочные данные для диалога добавления операции
        workshops = db.get_all_workshops() if hasattr(db, "get_all_workshops") else []
        operation_types = (
            db.get_all_operation_types()
            if hasattr(db, "get_all_operation_types")
            else []
        )
        equipment_list = (
            db.get_all_equipment() if hasattr(db, "get_all_equipment") else []
        )
        cooperatives = (
            db.get_cooperative_companies()
            if hasattr(db, "get_cooperative_companies")
            else []
        )

        return templates.TemplateResponse(
            "routes/view.html",
            {
                "request": request,
                "current_user": user,
                "route": route,
                "operations": route_operations,
                "workshops": workshops,
                "operation_types": operation_types,
                "equipment_list": equipment_list,
                "cooperatives": cooperatives,
            },
        )
    except Exception as e:
        logger.error(f"Error viewing route: {e}")
        return RedirectResponse(url="/routes", status_code=303)


@router.post("/{route_id}/delete")
async def delete_route(request: Request, route_id: int):
    """Удаление маршрута"""
    user = get_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    db = get_db()
    try:
        result = db.delete_route(route_id)
        if result:
            logger.info(f"Route deleted: {route_id}")
    except Exception as e:
        logger.error(f"Delete route error: {e}")

    return RedirectResponse(url="/routes", status_code=303)


@router.post("/{route_id}/toggle-approve")
async def toggle_approve_route(request: Request, route_id: int):
    """Утверждение/отзыв маршрута"""
    user = get_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    APPROVER_ROLES = {
        "admin",
        "chief_designer",
        "chief_engineer",
        "technologist_designer",
        "technologist",
    }
    if user.get("role") not in APPROVER_ROLES:
        return RedirectResponse(url="/routes", status_code=303)

    db = get_db()
    try:
        routes = db.get_all_routes()
        route = next((r for r in routes if r["id"] == route_id), None)
        if not route:
            return RedirectResponse(url="/routes", status_code=303)

        current_approved = bool(route.get("approved", False))
        new_approved = not current_approved
        db.toggle_route_approve(route_id, new_approved)
        logger.info(
            f"Route {route_id} approval toggled to {new_approved} by {user.get('username')}"
        )
    except Exception as e:
        logger.error(f"Toggle approve error: {e}")

    return RedirectResponse(url="/routes", status_code=303)


@router.post("/{route_id}/copy")
async def copy_route(request: Request, route_id: int):
    """Копирование маршрута с увеличением версии"""
    user = get_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    db = get_db()
    try:
        result = db.copy_route_with_operations(
            route_id, created_by=user.get("username")
        )
        if result:
            logger.info(
                f"Route {route_id} copied to {result['id']} (v{result['version']})"
            )
            return RedirectResponse(
                url=f"/routes?highlight_detail_id={result['id']}", status_code=303
            )
        else:
            logger.error(f"Failed to copy route {route_id}")
    except Exception as e:
        logger.error(f"Copy route error: {e}")

    return RedirectResponse(url="/routes", status_code=303)


@router.post("/{route_id}/create-order")
async def create_order(
    request: Request,
    route_id: int,
    production_type: str = Form("piece"),
    quantity: int = Form(...),
    auto_schedule: bool = Form(
        False
    ),  # Автоматическое планирование (по умолчанию ВЫКЛ)
    start_date: Optional[str] = Form(None),  # Дата начала планирования (YYYY-MM-DD)
    priority: int = Form(5),  # Приоритет заказа
):
    """Создание заказа из маршрута с автоматическим планированием"""
    user = get_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    db = get_db()
    try:
        # Получаем маршрут для определения quantity из заготовки
        routes = db.get_all_routes()
        route = next((r for r in routes if r["id"] == route_id), None)
        if not route:
            logger.error(f"Route {route_id} not found for order creation")
            return RedirectResponse(url="/routes", status_code=303)

        route_quantity = route.get("quantity", 1)
        blanks_needed = (
            math.ceil(quantity / route_quantity) if route_quantity > 0 else quantity
        )

        result = db.create_order_from_route(
            route_id=route_id,
            quantity=quantity,
            blanks_needed=blanks_needed,
            route_quantity=route_quantity,
            created_by=user.get("username"),
            production_type=production_type,
        )

        if result:
            order_id = result.get("id")
            batch_num = result.get("batch_number", "")
            type_name = "Штучное" if production_type == "piece" else "Партийное"

            logger.info(
                f"Order created from route {route_id}: ID={order_id}, "
                f"batch={batch_num}, type={type_name}, qty={quantity}"
            )

            # Автоматическое планирование если включено
            if auto_schedule and order_id:
                try:
                    from services.production_planner import ProductionPlanner

                    planner = ProductionPlanner(db)

                    # Парсим дату начала если указана
                    start_dt = None
                    if start_date:
                        try:
                            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                        except ValueError:
                            logger.warning(
                                f"Invalid start_date format: {start_date}, using None"
                            )

                    # Рассчитываем расписание
                    schedule_result = planner.calculate_schedule(
                        order_id=order_id, start_date=start_dt, priority=priority
                    )

                    if schedule_result.get("success"):
                        logger.info(
                            f"Schedule calculated for order {order_id}: "
                            f"start={schedule_result.get('start_date')}, "
                            f"end={schedule_result.get('end_date')}, "
                            f"operations={len(schedule_result.get('schedule', []))}"
                        )
                        # Перенаправляем на страницу планирования чтобы увидеть результат
                        return RedirectResponse(
                            url=f"/planning/plan?highlight_order={order_id}",
                            status_code=303,
                        )
                    else:
                        logger.warning(
                            f"Schedule calculation failed for order {order_id}: "
                            f"{schedule_result.get('message')}"
                        )
                        # Все равно идем в план даже если расчет не удался
                        return RedirectResponse(
                            url=f"/planning/plan?highlight_order={order_id}",
                            status_code=303,
                        )
                except Exception as e:
                    logger.error(
                        f"Auto-schedule error for order {order_id}: {e}", exc_info=True
                    )

            # Если автопланирование выключено, идем в план
            return RedirectResponse(
                url=f"/planning/plan?highlight_order={order_id}", status_code=303
            )
        else:
            logger.error(f"Failed to create order from route {route_id}")
    except Exception as e:
        logger.error(f"Create order error: {e}", exc_info=True)

    return RedirectResponse(url="/routes", status_code=303)


@router.get("/{route_id}/operations", response_class=JSONResponse)
async def get_route_operations_json(request: Request, route_id: int):
    """Получение операций маршрута в формате JSON (для AJAX)"""
    user = get_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    db = get_db()
    try:
        operations = db.get_route_operations(route_id)
        return JSONResponse({"success": True, "operations": operations})
    except Exception as e:
        logger.error(f"Get route operations error: {e}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@router.get("/{route_id}/api", response_class=JSONResponse)
async def get_route_api(request: Request, route_id: int):
    """Получение полных данных маршрута в JSON (для модального редактирования)"""
    user = get_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    db = get_db()
    try:
        route = db.get_route_by_id(route_id)
        if not route:
            return JSONResponse({"error": "Route not found"}, status_code=404)

        operations = db.get_route_operations(route_id)

        # Конвертируем datetime в строки
        for key, val in route.items():
            if hasattr(val, "isoformat"):
                route[key] = val.isoformat()

        return JSONResponse({"success": True, "route": route, "operations": operations})
    except Exception as e:
        logger.error(f"Get route API error: {e}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@router.put("/{route_id}/api", response_class=JSONResponse)
async def update_route_api(request: Request, route_id: int):
    """Обновление маршрута через JSON (для модального редактирования)"""
    user = get_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    db = get_db()
    try:
        body = await request.json()

        # Обновляем основные поля маршрута
        update_params = {}
        if "detail_name" in body:
            update_params["detail_name"] = body["detail_name"]
        if "designation" in body:
            update_params["designation"] = body["designation"]
        if "version" in body:
            update_params["version"] = body["version"]
        if "material_instance_id" in body:
            update_params["material_instance_id"] = body["material_instance_id"]
        if "quantity" in body:
            update_params["quantity"] = body["quantity"]
        if "length" in body:
            update_params["dimension1"] = body["length"]
        if "width" in body:
            update_params["dimension2"] = body["width"]
        if "waste_percent" in body:
            update_params["waste_percent"] = body["waste_percent"]

        if update_params:
            db.update_route(route_id=route_id, **update_params)

        # Обновляем операции если они переданы
        if "operations" in body:
            db.delete_route_operations(route_id)
            for idx, op in enumerate(body["operations"], 1):
                db.add_route_operation(
                    route_id=route_id,
                    operation_type_id=op.get("operation_type_id"),
                    equipment_id=op.get("equipment_id"),
                    sequence_number=idx,
                    duration_minutes=op.get("duration_minutes"),
                    notes=op.get("notes"),
                    workshop_id=op.get("workshop_id"),
                    is_cooperation=op.get("is_cooperation", False),
                    coop_company_id=op.get("coop_company_id"),
                    coop_duration_days=op.get("coop_duration_days", 0),
                    coop_position=op.get("coop_position", "start"),
                )

        logger.info(f"Route updated via API: {route_id} by {user.get('username')}")
        return JSONResponse({"success": True, "route_id": route_id})
    except Exception as e:
        logger.error(f"Update route API error: {e}")
        import traceback

        traceback.print_exc()
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@router.post("/{route_id}/operations", response_class=JSONResponse)
async def add_operation_to_route(request: Request, route_id: int):
    """Добавление операции к маршруту через JSON"""
    user = get_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    db = get_db()
    try:
        body = await request.json()

        # Получаем текущий максимальный sequence_number
        operations = db.get_route_operations(route_id)
        max_seq = max((op.get("sequence_number", 0) for op in operations), default=0)

        db.add_route_operation(
            route_id=route_id,
            operation_type_id=body.get("operation_type_id"),
            equipment_id=body.get("equipment_id"),
            sequence_number=max_seq + 1,
            duration_minutes=body.get("duration_minutes", 0),
            prep_time=body.get("prep_time", 0),
            control_time=body.get("control_time", 0),
            parts_count=body.get("parts_count", 1),
            notes=body.get("notes", ""),
            is_cooperation=body.get("is_cooperation", False),
            coop_company_id=body.get("coop_company_id"),
            coop_duration_days=body.get("coop_duration_days", 0),
            coop_position=body.get("coop_position", "start"),
        )

        logger.info(f"Operation added to route {route_id} by {user.get('username')}")
        return JSONResponse({"success": True})
    except Exception as e:
        logger.error(f"Add operation error: {e}")
        import traceback

        traceback.print_exc()
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@router.post("/{route_id}/operations/{op_id}/move", response_class=JSONResponse)
async def move_operation(request: Request, route_id: int, op_id: int):
    """Перемещение операции вверх/вниз"""
    user = get_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    db = get_db()
    try:
        body = await request.json()
        direction = body.get("direction", 0)  # -1 = вверх, 1 = вниз

        # Получаем все операции маршрута
        operations = db.get_route_operations(route_id)
        op_list = sorted(operations, key=lambda x: x.get("sequence_number", 0))

        # Находим нужную операцию
        op_index = next(
            (i for i, op in enumerate(op_list) if op.get("id") == op_id), None
        )
        if op_index is None:
            return JSONResponse(
                {"success": False, "error": "Operation not found"}, status_code=404
            )

        # Проверяем границы
        new_index = op_index + direction
        if new_index < 0 or new_index >= len(op_list):
            return JSONResponse(
                {"success": False, "error": "Cannot move beyond bounds"},
                status_code=400,
            )

        # Меняем местами sequence_number
        op_list[op_index]["sequence_number"], op_list[new_index]["sequence_number"] = (
            op_list[new_index]["sequence_number"],
            op_list[op_index]["sequence_number"],
        )

        # Обновляем в БД
        for op in op_list:
            db.update_route_operation(op["id"], sequence_number=op["sequence_number"])

        logger.info(
            f"Operation {op_id} moved in route {route_id} by {user.get('username')}"
        )
        return JSONResponse({"success": True})
    except Exception as e:
        logger.error(f"Move operation error: {e}")
        import traceback

        traceback.print_exc()
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@router.put("/{route_id}/operations/{op_id}", response_class=JSONResponse)
async def update_operation(request: Request, route_id: int, op_id: int):
    """Обновить параметры операции маршрута"""
    user = get_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    db = get_db()
    try:
        body = await request.json()

        updates = {}
        if "operation_type_id" in body:
            updates["operation_type_id"] = body["operation_type_id"]
        if "equipment_id" in body:
            updates["equipment_id"] = body["equipment_id"]
        if "duration_minutes" in body:
            updates["duration_minutes"] = body["duration_minutes"]
        if "prep_time" in body:
            updates["prep_time"] = body["prep_time"]
        if "control_time" in body:
            updates["control_time"] = body["control_time"]
        if "parts_count" in body:
            updates["parts_count"] = body["parts_count"]
        if "notes" in body:
            updates["notes"] = body["notes"]
        if "is_cooperation" in body:
            updates["is_cooperation"] = body["is_cooperation"]
        if "coop_company_id" in body:
            updates["coop_company_id"] = body["coop_company_id"]
        if "coop_duration_days" in body:
            updates["coop_duration_days"] = body["coop_duration_days"]
        if "coop_position" in body:
            updates["coop_position"] = body["coop_position"]
        if "operation_name" in body:
            updates["operation_name"] = body["operation_name"]

        if updates:
            db.update_route_operation(op_id, **updates)
            logger.info(
                f"Operation {op_id} updated in route {route_id} by {user.get('username')}"
            )

        return JSONResponse({"success": True})
    except Exception as e:
        logger.error(f"Update operation error: {e}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@router.delete("/{route_id}/operations/{op_id}", response_class=JSONResponse)
async def delete_operation(request: Request, route_id: int, op_id: int):
    """Удалить операцию из маршрута"""
    user = get_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    db = get_db()
    try:
        db.delete_route_operation(op_id)

        # Перенумеруем оставшиеся операции
        operations = db.get_route_operations(route_id)
        op_list = sorted(operations, key=lambda x: x.get("sequence_number", 0))
        for i, op in enumerate(op_list, 1):
            db.update_route_operation(op["id"], sequence_number=i)

        logger.info(
            f"Operation {op_id} deleted from route {route_id} by {user.get('username')}"
        )
        return JSONResponse({"success": True})
    except Exception as e:
        logger.error(f"Delete operation error: {e}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@router.get("/api/details")
async def get_details_list(request: Request):
    """Получить список всех деталей для dropdown"""
    db = get_db()
    try:
        details = db.get_all_details()
        return {"details": details}
    except Exception as e:
        logger.error(f"Get details list error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/{route_id}/edit-material")
async def update_route_material(request: Request, route_id: int):
    """Обновление материала, параметров и предварительной обработки маршрута (без операций)"""
    user = get_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    import json

    db = get_db()
    try:
        body = await request.json()
        designation = body.get("designation")
        detail_name = body.get("detail_name")
        detail_id = body.get("detail_id")  # ID детали
        version = body.get("version", "1.0")
        length = body.get("length")
        quantity = body.get("quantity", 1)
        waste_percent = body.get("waste_percent", 0)
        material_instance_id = body.get("material_instance_id")
        preprocessing_data = body.get("preprocessing_data")  # JSON string

        db.update_route(
            route_id=route_id,
            detail_name=detail_name,
            designation=designation,
            detail_id=detail_id,  # Обновляем привязку к детали
            version=version,
            material_instance_id=material_instance_id,
            quantity=quantity,
            dimension1=float(length) if length else None,
            waste_percent=float(waste_percent) if waste_percent else 0,
            preprocessing_data=preprocessing_data,
        )

        logger.info(
            f"Route material updated: {route_id}, detail_id={detail_id}, designation={designation} by {user.get('username')}"
        )
        return JSONResponse({"success": True, "route_id": route_id})

    except Exception as e:
        logger.error(f"Update route material error: {e}")
        return JSONResponse({"error": f"Failed to update: {str(e)}"}, status_code=500)
