"""API для Электронной маршрутной карты (ЭМК)"""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from starlette.templating import Jinja2Templates

logger = logging.getLogger(__name__)
router = APIRouter(prefix="", tags=["order-card"])

templates = Jinja2Templates(directory="templates")


def get_db():
    """Получить DatabaseManager"""
    from main import get_db as _get_db

    return _get_db()


def get_user(request: Request) -> Optional[dict]:
    """Получить текущего пользователя из сессии"""
    return request.session.get("user")


def format_fio(full_name: str) -> str:
    """Преобразует 'Иванов Иван' в 'Иванов И.' или 'Иванов И.И.'"""
    if not full_name:
        return ""
    parts = full_name.strip().split()
    if len(parts) >= 2:
        last_name = parts[0]
        initials = "".join(p[0] + "." for p in parts[1:] if p)
        return f"{last_name} {initials}"
    return full_name


def get_operators_for_equipment(db, equipment_ids: List[int]) -> List[dict]:
    """Получить список операторов для указанных станков"""
    try:
        users = db.get_all_users()
        operators = []

        user_role_users = [u for u in users if u.get("role") == "user"]

        for user in user_role_users:
            user_workstations = user.get("workstations", "") or ""
            user_ws_list = [
                int(ws.strip())
                for ws in user_workstations.split(",")
                if ws.strip().isdigit()
            ]

            if equipment_ids:
                for eq_id in equipment_ids:
                    if eq_id and eq_id in user_ws_list:
                        operators.append(
                            {
                                "id": user["id"],
                                "username": user["username"],
                                "fio_short": format_fio(user["username"]),
                            }
                        )
                        break
            else:
                operators.append(
                    {
                        "id": user["id"],
                        "username": user["username"],
                        "fio_short": format_fio(user["username"]),
                    }
                )

        if not operators and user_role_users:
            operators = [
                {
                    "id": u["id"],
                    "username": u["username"],
                    "fio_short": format_fio(u["username"]),
                }
                for u in user_role_users
            ]

        logger.info(
            f"get_operators_for_equipment: equipment_ids={equipment_ids}, found {len(operators)} operators (role=user)"
        )
        return operators
    except Exception as e:
        logger.error(f"Get operators error: {e}", exc_info=True)
        return []


def check_access(request: Request) -> dict:
    """Проверить доступ и вернуть права пользователя"""
    user = get_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Не авторизован")

    role = user.get("role", "")

    can_edit = role in ("admin", "otk", "foreman")
    can_approve_otk = role == "otk"
    can_view = role != "user"

    if not can_view:
        raise HTTPException(status_code=403, detail="Доступ запрещён")

    return {
        "can_edit": can_edit,
        "can_approve_otk": can_approve_otk,
        "role": role,
        "user_id": user.get("id"),
        "username": user.get("username", ""),
    }


@router.get("/api/orders/{order_id}/card")
async def get_order_card(request: Request, order_id: int):
    """Получить данные ЭМК для заказа"""
    access = check_access(request)
    db = get_db()

    try:
        order = db.get_order(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Заказ не найден")

        route_id = order.get("route_id")
        if not route_id:
            raise HTTPException(status_code=400, detail="У заказа нет маршрута")

        operations = db.get_route_operations(route_id)

        # Логируем IDs операций маршрута
        op_ids = [op.get("id") for op in operations]
        logger.info(f"route_operations IDs: {op_ids}")

        # Получаем производственный план для заказа
        schedule = db.get_production_schedule(order_id=order_id)

        logger.info(
            f"get_order_card: order_id={order_id}, schedule_items={len(schedule)}"
        )

        # Создаём словарь schedule по route_operation_id для быстрого доступа
        # Группируем по route_operation_id
        # - Для даты: последняя planned_date
        # - Для taken_by: in_progress/completed (любой с взятым в работу)
        schedule_by_op = {}
        schedule_by_op_taken = {}  # отдельный словарь для taken_by

        for sch in schedule:
            route_op_id = sch.get("route_operation_id")
            if route_op_id:
                status = sch.get("status")
                planned_date = sch.get("planned_date")
                taken_by = sch.get("taken_by")
                # Оборудование уже есть в schedule из JOIN
                schedule_equipment_id = sch.get("equipment_id")
                schedule_equipment_name = sch.get("equipment_name", "")

                # 1. Для даты - всегда берём последнюю planned_date
                if route_op_id not in schedule_by_op:
                    schedule_by_op[route_op_id] = sch
                else:
                    existing = schedule_by_op[route_op_id]
                    existing_date = existing.get("planned_date")

                    def parse_date(val):
                        if val is None:
                            return None
                        if isinstance(val, datetime):
                            return val
                        if isinstance(val, str):
                            try:
                                return datetime.fromisoformat(val.replace("Z", "+00:"))
                            except:
                                return None
                        return val

                    existing_parsed = parse_date(existing_date)
                    new_parsed = parse_date(planned_date)

                    if existing_parsed and new_parsed and new_parsed > existing_parsed:
                        schedule_by_op[route_op_id] = sch

                # 2. Для taken_by - берём запись со статусом in_progress/completed
                if taken_by and status in ("in_progress", "completed"):
                    if route_op_id not in schedule_by_op_taken:
                        schedule_by_op_taken[route_op_id] = sch

        logger.info(f"schedule_by_op keys: {list(schedule_by_op.keys())}")

        # Детальное логирование - выводим ВСЕ поля schedule
        for i, sch in enumerate(schedule[:3]):
            logger.info(f"  schedule[{i}]: {dict(sch)}")

        route_card_data = order.get("route_card_data") or {}

        # Если нет данных ЭМК - создаём новые данные
        if not route_card_data:
            operations_with_data = []
            for op in operations:
                equipment_id = op.get("equipment_id")
                op_id = op.get("id")

                schedule_item = schedule_by_op.get(op_id, {})
                taken_item = schedule_by_op_taken.get(op_id, {})
                
                # Получаем оборудование из schedule (приоритет!) или из маршрута
                schedule_eq_id = schedule_item.get("equipment_id") if schedule_item else None
                schedule_eq_name = schedule_item.get("equipment_name", "") if schedule_item else ""
                final_equipment_id = schedule_eq_id if schedule_eq_id else equipment_id
                final_equipment_name = schedule_eq_name if schedule_eq_name else op.get("equipment_name", "")
                
                # Логируем equipment из schedule для отладки
                logger.info(f"DEBUG: op_id={op_id}, schedule_equipment_id={schedule_eq_id}, schedule_equipment_name={schedule_eq_name}, final={final_equipment_name}")

                # Получаем операторов для актуального оборудования из schedule!
                operators = get_operators_for_equipment(
                    db, [final_equipment_id] if final_equipment_id else []
                )

                completed_at = schedule_item.get("completed_at")
                actual_date = schedule_item.get("actual_date")
                planned_date = schedule_item.get("planned_date")
                duration_minutes = schedule_item.get("duration_minutes", 0) or 0
                quantity = schedule_item.get("quantity", 1) or 1
                taken_by = taken_item.get("taken_by", "")

                operation_date = ""
                operator_fio = ""

                # Вычисляем end_date как в planning.py
                computed_end_date = None
                if planned_date and duration_minutes and quantity:
                    # Рабочий день 7 часов = 420 минут
                    total_minutes = duration_minutes * quantity
                    working_minutes_per_day = 420
                    days_needed = total_minutes // working_minutes_per_day
                    if total_minutes % working_minutes_per_day > 0:
                        days_needed += 1

                    # Находим дату окончания
                    current_date = planned_date
                    days_added = 0
                    while days_added < days_needed:
                        current_date += timedelta(days=1)
                        if current_date.weekday() < 5:  # Пн-Пт
                            days_added += 1
                    computed_end_date = current_date

                # Показываем дату завершения/выполнения
                # Приоритет: completed_at > actual_date > computed_end_date > planned_date
                if completed_at:
                    if isinstance(completed_at, datetime):
                        operation_date = completed_at.strftime("%Y-%m-%d")
                    else:
                        operation_date = str(completed_at)[:10]
                elif actual_date:
                    if isinstance(actual_date, datetime):
                        operation_date = actual_date.strftime("%Y-%m-%d")
                    else:
                        operation_date = str(actual_date)[:10]
                elif computed_end_date:
                    if isinstance(computed_end_date, datetime):
                        operation_date = computed_end_date.strftime("%Y-%m-%d")
                    else:
                        operation_date = str(computed_end_date)[:10]
                elif planned_date:
                    if isinstance(planned_date, datetime):
                        operation_date = planned_date.strftime("%Y-%m-%d")
                    else:
                        operation_date = str(planned_date)[:10]

                if taken_by:
                    users = db.get_all_users()
                    for u in users:
                        if (
                            str(u.get("id")) == str(taken_by)
                            or u.get("username") == taken_by
                        ):
                            operator_fio = format_fio(u.get("username", ""))
                            break

                # Получаем оборудование из schedule (приоритет) или из маршрута
                schedule_eq_id = schedule_item.get("equipment_id") if schedule_item else None
                schedule_eq_name = schedule_item.get("equipment_name", "") if schedule_item else ""
                # Используем оборудование из schedule если есть, иначе из маршрута
                final_equipment_id = schedule_eq_id if schedule_eq_id else equipment_id
                final_equipment_name = schedule_eq_name if schedule_eq_name else op.get("equipment_name", "")

                operations_with_data.append(
                    {
                        "operation_id": op_id,
                        "sequence_number": op.get("sequence_number"),
                        "operation_name": op.get("operation_name", ""),
                        "equipment_name": final_equipment_name,
                        "equipment_id": final_equipment_id,
                        "workshop_name": op.get("workshop_name", ""),
                        "operator_fio": operator_fio,
                        "operation_date": operation_date,
                        "quantity_plan": order.get("quantity", 1),
                        "quantity_fact": 0,
                        "defects": 0,
                        "comment": "",
                        "otk_approved": False,
                        "otk_approved_by": None,
                        "otk_approved_at": None,
                        "operators": operators,
                    }
                )

            route_card_data = {
                "operations": operations_with_data,
                "history": [],
            }
            db.update_order_card_data(order_id, route_card_data)
        else:
            # Если route_card_data уже есть - проверяем и обновляем данные из schedule если нужно
            existing_ops = {
                op.get("operation_id") for op in route_card_data.get("operations", [])
            }
            current_op_ids = {op.get("id") for op in operations}

            # Обновляем если изменились операции
            if existing_ops != current_op_ids or not route_card_data.get(
                "operations", []
            ):
                operations_with_data = []
                for op in operations:
                    equipment_id = op.get("equipment_id")
                    op_id = op.get("id")

                    operators = get_operators_for_equipment(
                        db, [equipment_id] if equipment_id else []
                    )

                    existing = next(
                        (
                            e
                            for e in route_card_data.get("operations", [])
                            if e.get("operation_id") == op_id
                        ),
                        None,
                    )

                    # Пытаемся получить данные из производственного плана
                    schedule_item = schedule_by_op.get(op_id, {})
                    taken_item = schedule_by_op_taken.get(op_id, {})
                    completed_at = schedule_item.get("completed_at")
                    actual_date = schedule_item.get("actual_date")
                    planned_date = schedule_item.get("planned_date")
                    duration_minutes = schedule_item.get("duration_minutes", 0) or 0
                    quantity = schedule_item.get("quantity", 1) or 1
                    taken_by = taken_item.get("taken_by", "")
                    
                    # Получаем оборудование из schedule (приоритет!) или из маршрута
                    schedule_eq_id = schedule_item.get("equipment_id") if schedule_item else None
                    schedule_eq_name = schedule_item.get("equipment_name", "") if schedule_item else ""
                    final_equipment_id = schedule_eq_id if schedule_eq_id else equipment_id
                    final_equipment_name = schedule_eq_name if schedule_eq_name else op.get("equipment_name", "")
                    
                    # Получаем операторов для актуального оборудования из schedule!
                    operators = get_operators_for_equipment(
                        db, [final_equipment_id] if final_equipment_id else []
                    )

                    # Форматируем дату - пробуем разные поля
                    operation_date = ""
                    operator_fio = ""

                    # Вычисляем end_date как в planning.py
                    computed_end_date = None
                    if planned_date and duration_minutes and quantity:
                        total_minutes = duration_minutes * quantity
                        working_minutes_per_day = 420
                        days_needed = total_minutes // working_minutes_per_day
                        if total_minutes % working_minutes_per_day > 0:
                            days_needed += 1

                        current_date = planned_date
                        days_added = 0
                        while days_added < days_needed:
                            current_date += timedelta(days=1)
                            if current_date.weekday() < 5:
                                days_added += 1
                        computed_end_date = current_date

                    # Приоритет: completed_at > actual_date > computed_end_date > planned_date
                    if completed_at:
                        if isinstance(completed_at, datetime):
                            operation_date = completed_at.strftime("%Y-%m-%d")
                        else:
                            operation_date = str(completed_at)[:10]
                    elif actual_date:
                        if isinstance(actual_date, datetime):
                            operation_date = actual_date.strftime("%Y-%m-%d")
                        else:
                            operation_date = str(actual_date)[:10]
                    elif computed_end_date:
                        if isinstance(computed_end_date, datetime):
                            operation_date = computed_end_date.strftime("%Y-%m-%d")
                        else:
                            operation_date = str(computed_end_date)[:10]
                    elif planned_date:
                        if isinstance(planned_date, datetime):
                            operation_date = planned_date.strftime("%Y-%m-%d")
                        else:
                            operation_date = str(planned_date)[:10]

                    # Получаем ФИО оператора из taken_by
                    if taken_by:
                        users = db.get_all_users()
                        for u in users:
                            if (
                                str(u.get("id")) == str(taken_by)
                                or u.get("username") == taken_by
                            ):
                                operator_fio = format_fio(u.get("username", ""))
                                break

                    operations_with_data.append(
                        {
                            "operation_id": op_id,
                            "sequence_number": op.get("sequence_number"),
                            "operation_name": op.get("operation_name", ""),
                            "equipment_name": final_equipment_name,
                            "equipment_id": final_equipment_id,
                            "workshop_name": op.get("workshop_name", ""),
                            # Всегда используем НОВУЮ дату из schedule, не старую
                            "operator_fio": operator_fio,
                            "operation_date": operation_date,
                            "quantity_plan": existing.get(
                                "quantity_plan", order.get("quantity", 1)
                            )
                            if existing
                            else order.get("quantity", 1),
                            "quantity_fact": existing.get("quantity_fact", 0)
                            if existing
                            else 0,
                            "defects": existing.get("defects", 0) if existing else 0,
                            "comment": existing.get("comment", "") if existing else "",
                            "otk_approved": existing.get("otk_approved", False)
                            if existing
                            else False,
                            "otk_approved_by": existing.get("otk_approved_by")
                            if existing
                            else None,
                            "otk_approved_at": existing.get("otk_approved_at")
                            if existing
                            else None,
                            "operators": operators,
                        }
                    )

                route_card_data["operations"] = operations_with_data
                db.update_order_card_data(order_id, route_card_data)
            else:
                for card_op, route_op in zip(
                    route_card_data.get("operations", []), operations
                ):
                    equipment_id = route_op.get("equipment_id")
                    if equipment_id:
                        card_op["operators"] = get_operators_for_equipment(
                            db, [equipment_id] if equipment_id else []
                        )
                    else:
                        card_op["operators"] = []
                    card_op["equipment_name"] = route_op.get("equipment_name", "")
                    card_op["workshop_name"] = route_op.get("workshop_name", "")

                    # Обновляем дату и оператора из schedule ВСЕГДА - перезаписываем старые данные новыми
                    op_id = route_op.get("id")
                    schedule_item = schedule_by_op.get(op_id, {})

                    if schedule_item:
                        # Обновляем дату - показываем дату завершения если есть
                        completed_at = schedule_item.get("completed_at")
                        actual_date = schedule_item.get("actual_date")
                        planned_date = schedule_item.get("planned_date")
                        duration_minutes = schedule_item.get("duration_minutes", 0) or 0
                        quantity = schedule_item.get("quantity", 1) or 1

                        new_date = ""

                        # Вычисляем end_date как в planning.py
                        computed_end_date = None
                        if planned_date and duration_minutes and quantity:
                            total_minutes = duration_minutes * quantity
                            working_minutes_per_day = 420
                            days_needed = total_minutes // working_minutes_per_day
                            if total_minutes % working_minutes_per_day > 0:
                                days_needed += 1

                            current_date = planned_date
                            days_added = 0
                            while days_added < days_needed:
                                current_date += timedelta(days=1)
                                if current_date.weekday() < 5:
                                    days_added += 1
                            computed_end_date = current_date

                        if completed_at:
                            if isinstance(completed_at, datetime):
                                new_date = completed_at.strftime("%Y-%m-%d")
                            else:
                                new_date = str(completed_at)[:10]
                        elif actual_date:
                            if isinstance(actual_date, datetime):
                                new_date = actual_date.strftime("%Y-%m-%d")
                            else:
                                new_date = str(actual_date)[:10]
                        elif computed_end_date:
                            if isinstance(computed_end_date, datetime):
                                new_date = computed_end_date.strftime("%Y-%m-%d")
                            else:
                                new_date = str(computed_end_date)[:10]
                        elif planned_date:
                            if isinstance(planned_date, datetime):
                                new_date = planned_date.strftime("%Y-%m-%d")
                            else:
                                new_date = str(planned_date)[:10]

                        if new_date:
                            card_op["operation_date"] = new_date

                        # Обновляем оператора - используем отдельный словарь для taken_by
                        taken_item = schedule_by_op_taken.get(op_id, {})
                        taken_by = taken_item.get("taken_by", "")
                        logger.info(f"Processing op_id={op_id}, taken_by='{taken_by}'")
                        if taken_by:
                            users = db.get_all_users()
                            logger.info(
                                f"Looking for user with taken_by='{taken_by}', total users={len(users)}"
                            )
                            found = False
                            for u in users:
                                if (
                                    str(u.get("id")) == str(taken_by)
                                    or u.get("username") == taken_by
                                ):
                                    card_op["operator_fio"] = format_fio(
                                        u.get("username", "")
                                    )
                                    logger.info(
                                        f"FOUND USER: id={u.get('id')}, username={u.get('username')}, setting operator_fio={card_op['operator_fio']}"
                                    )
                                    found = True
                                    break
                            if not found:
                                logger.warning(
                                    f"User not found for taken_by='{taken_by}'"
                                )

                db.update_order_card_data(order_id, route_card_data)

        for key, val in order.items():
            if isinstance(val, (datetime,)):
                order[key] = val.isoformat()

        return JSONResponse(
            {
                "success": True,
                "order": order,
                "operations": operations,
                "card_data": route_card_data,
                "access": access,
                "tools": route_card_data.get("tools", []),
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get order card error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/orders/{order_id}/card")
async def save_order_card(request: Request, order_id: int):
    """Сохранить данные ЭМК для заказа"""
    from database import DatabaseManager

    access = check_access(request)
    if not access["can_edit"]:
        raise HTTPException(status_code=403, detail="Нет прав на редактирование")

    db = get_db()

    try:
        # Получаем заказ
        order = db.get_order(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Заказ не найден")

        # Получаем данные из запроса
        body = await request.json()
        operation_id = body.get("operation_id")
        field = body.get("field")
        value = body.get("value")

        if not operation_id or not field:
            raise HTTPException(
                status_code=400, detail="Не указаны operation_id или field"
            )

        # Получаем текущие данные ЭМК
        route_card_data = order.get("route_card_data") or {
            "operations": [],
            "history": [],
        }

        # Находим операцию и обновляем
        operations = route_card_data.get("operations", [])
        operation_updated = False

        for op in operations:
            if op.get("operation_id") == operation_id:
                # Записываем старое значение для истории
                old_value = op.get(field, "")

                # Обновляем значение
                op[field] = value

                # Добавляем запись в историю
                history_entry = {
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "user_id": access["user_id"],
                    "username": access["username"],
                    "field": field,
                    "old_value": str(old_value),
                    "new_value": str(value),
                }
                route_card_data.setdefault("history", []).append(history_entry)

                operation_updated = True
                break

        if not operation_updated:
            raise HTTPException(status_code=404, detail="Операция не найдена в карте")

        # Сохраняем в БД
        db.update_order_card_data(order_id, route_card_data)

        return JSONResponse({"success": True, "message": "Сохранено"})

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Save order card error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/orders/{order_id}/card/approve-otk")
async def approve_otk(request: Request, order_id: int):
    """Подтвердить ОТК для операции"""
    from database import DatabaseManager

    access = check_access(request)
    if not access["can_approve_otk"]:
        raise HTTPException(status_code=403, detail="Только ОТК может подтверждать")

    db = get_db()

    try:
        # Получаем заказ
        order = db.get_order(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Заказ не найден")

        # Получаем данные из запроса
        body = await request.json()
        operation_id = body.get("operation_id")
        approved = body.get("approved", True)

        if not operation_id:
            raise HTTPException(status_code=400, detail="Не указан operation_id")

        # Получаем текущие данные ЭМК
        route_card_data = order.get("route_card_data") or {
            "operations": [],
            "history": [],
        }

        # Находим операцию и обновляем
        operations = route_card_data.get("operations", [])
        operation_updated = False

        for op in operations:
            if op.get("operation_id") == operation_id:
                old_value = op.get("otk_approved", False)

                op["otk_approved"] = approved
                op["otk_approved_by"] = access["user_id"] if approved else None
                op["otk_approved_at"] = (
                    datetime.utcnow().isoformat() if approved else None
                )

                # История
                history_entry = {
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "user_id": access["user_id"],
                    "username": access["username"],
                    "field": "otk_approved",
                    "old_value": str(old_value),
                    "new_value": str(approved),
                }
                route_card_data.setdefault("history", []).append(history_entry)

                operation_updated = True
                break

        if not operation_updated:
            raise HTTPException(status_code=404, detail="Операция не найдена в карте")

        # Сохраняем в БД
        db.update_order_card_data(order_id, route_card_data)

        return JSONResponse(
            {
                "success": True,
                "message": "ОТК подтверждено" if approved else "ОТК отозвано",
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Approve OTK error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# HTML страница ЭМК заказа
@router.get("/orders/{order_id}/card", response_class=HTMLResponse)
async def order_card_page(request: Request, order_id: int):
    """Страница ЭМК заказа"""
    user = get_user(request)
    if not user:
        from fastapi.responses import RedirectResponse

        return RedirectResponse(url="/login", status_code=303)

    role = user.get("role", "")
    access = {
        "can_edit": role in ("admin", "otk", "foreman"),
        "can_approve_otk": role == "otk",
        "role": role,
        "user_id": user.get("id"),
        "username": user.get("username", ""),
    }

    # Получаем данные заказа для шаблона
    db = get_db()
    order = db.get_order(order_id)
    route_card_data = {}
    if order and order.get("route_card_data"):
        import json

        try:
            # Проверяем: если уже dict - используем как есть
            if isinstance(order.get("route_card_data"), dict):
                route_card_data = order.get("route_card_data")
            else:
                route_card_data = json.loads(order["route_card_data"])
        except:
            route_card_data = {}
    
    logger.info(f"order_card_page: order_id={order_id}, route_card_data has tools: {bool(route_card_data.get('tools', []))}")

    return templates.TemplateResponse(
        "orders/card.html",
        {
            "request": request,
            "current_user": user,
            "order_id": order_id,
            "access": access,
            "card_data": route_card_data,
        },
    )


# Страница ОТК - список заказов
@router.get("/otk/cards", response_class=HTMLResponse)
async def otk_cards_page(request: Request):
    """Страница ОТК - список заказов для ЭМК"""
    user = get_user(request)
    if not user:
        from fastapi.responses import RedirectResponse

        return RedirectResponse(url="/login", status_code=303)

    # Проверяем роль ОТК
    if user.get("role") != "otk":
        from fastapi.responses import RedirectResponse

        return RedirectResponse(url="/dashboard", status_code=303)

    return templates.TemplateResponse(
        "otk/cards.html",
        {"request": request, "current_user": user},
    )


# API для списка заказов на странице ОТК
@router.get("/api/otk/orders")
async def get_otk_orders(request: Request):
    """Получить список заказов для ОТК (запланированные)"""
    user = get_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Не авторизован")

    role = user.get("role", "")
    if role not in ("admin", "otk", "foreman", "technologist", "master"):
        raise HTTPException(status_code=403, detail="Доступ запрещён")

    db = get_db()

    try:
        orders = db.get_all_orders()
        logger.info(f"get_all_orders returned: {len(orders)} orders")

        planned_statuses = ["новый", "Запланировано", "В работе", "Задержка"]

        result = []
        for order in orders:
            status = order.get("status") or "Запланировано"
            order_id = order.get("id")

            logger.info(f"Order {order_id}: status={status}, checking schedule...")

            if order_id and status in planned_statuses:
                schedule = db.get_production_schedule(order_id=order_id)
                logger.info(
                    f"Order {order_id}: schedule={type(schedule)}, len={len(schedule) if schedule else 0}"
                )

                if schedule and len(schedule) > 0:
                    for key, val in order.items():
                        if isinstance(val, (datetime,)):
                            order[key] = val.isoformat()

                    order["is_planned"] = True
                    result.append(order)
                    logger.info(f"Order {order_id} added to result")

        logger.info(f"get_otk_orders: found {len(result)} orders")
        return JSONResponse({"success": True, "orders": result})

    except Exception as e:
        logger.error(f"Get OTK orders error: {e}", exc_info=True)
        return JSONResponse({"success": False, "error": str(e)})


@router.get("/api/orders/{order_id}/card/pdf")
async def get_order_card_pdf(request: Request, order_id: int):
    """Генерация PDF для ЭМК заказа"""
    from fastapi.responses import FileResponse
    import json
    
    access = check_access(request)
    db = get_db()

    try:
        order = db.get_order(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Заказ не найден")

        route_id = order.get("route_id")
        if not route_id:
            raise HTTPException(status_code=400, detail="У заказа нет маршрута")

        operations = db.get_route_operations(route_id)
        
        # Получаем schedule для актуального оборудования
        schedule = db.get_production_schedule(order_id=order_id)
        
        # Создаём словарь schedule по route_operation_id для оборудования
        schedule_by_op = {}
        for sch in schedule:
            route_op_id = sch.get("route_operation_id")
            if route_op_id:
                schedule_by_op[route_op_id] = sch
        
        # Обновляем operations с актуальным оборудованием из schedule
        for op in operations:
            op_id = op.get("id")
            sch = schedule_by_op.get(op_id, {})
            # Логируем для отладки
            logger.info(f"PDF: op_id={op_id}, schedule_eq={sch.get('equipment_name') if sch else 'none'}")
            # Если в schedule есть оборудование - используем его
            if sch and sch.get("equipment_id"):
                op["equipment_id"] = sch.get("equipment_id")
                op["equipment_name"] = sch.get("equipment_name", "")
        
        # Конвертируем datetime в строки для JSON
        order_clean = {}
        for key, val in order.items():
            if isinstance(val, datetime):
                order_clean[key] = val.isoformat()
            else:
                order_clean[key] = val
        
        # Получаем route_card_data
        route_card_data = {}
        if order and order.get("route_card_data"):
            try:
                if isinstance(order.get("route_card_data"), dict):
                    route_card_data = order.get("route_card_data")
                else:
                    route_card_data = json.loads(order["route_card_data"])
            except:
                route_card_data = {}
        
        # Генерируем PDF
        from services.emc_card_pdf_generator import EMCCardPDFGenerator
        
        generator = EMCCardPDFGenerator()
        pdf_bytes = generator.generate(order_clean, operations, route_card_data)

        # Сохраняем во временный файл
        import os
        os.makedirs("/tmp/emc_pdf", exist_ok=True)
        filepath = f"/tmp/emc_pdf/emc_{order_id}.pdf"
        
        with open(filepath, "wb") as f:
            f.write(pdf_bytes)
        
        # Формируем имя файла
        designation = order_clean.get("designation", "unknown")
        detail_name = order_clean.get("detail_name", "")
        if detail_name:
            filename = f"ЭМК_{designation}_{detail_name}.pdf"
        else:
            filename = f"ЭМК_{order_id}.pdf"
        
        return FileResponse(
            filepath, 
            media_type="application/pdf", 
            filename=filename.replace(" ", "_")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get EMC PDF error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
