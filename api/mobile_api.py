"""Mobile API — объединённая версия из mobile_web"""

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from main import get_db, get_user
from datetime import datetime, timedelta
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mobile", tags=["mobile"])
templates = Jinja2Templates(directory="templates")


@router.get("/login", response_class=HTMLResponse)
async def mobile_login_page(request: Request):
    return templates.TemplateResponse("mobile/login.html", {"request": request})


@router.post("/login")
async def mobile_login_submit(
    request: Request, username: str = Form(...), password: str = Form(...)
):
    db = get_db()
    from services.auth_service import AuthService

    session = AuthService(db).login(username, password)

    if session:
        # Загружаем screen_permissions из БД
        screen_perms = None
        try:
            screen_perms = db.get_user_screen_permissions(session.user.id)
        except Exception:
            pass  # Если метод не существует — None

        # Обрабатываем workstations - убираем unicode escape sequences
        workstations = session.user.workstations
        if workstations and isinstance(workstations, str):
            # Убираем unicode escape sequences типа \u0424\u0440\u0435\u0437
            try:
                # Пробуем декодировать если это bytes repr
                workstations_decoded = workstations.encode("utf-8").decode(
                    "unicode_escape"
                )
                # Если результат содержит кириллицу - используем его
                if any("\u0400" <= c <= "\u04ff" for c in workstations_decoded):
                    workstations = workstations_decoded
            except Exception:
                pass

        request.session["user"] = {
            "id": session.user.id,
            "username": session.user.username,
            "login": session.user.login,
            "role": str(session.user.role),
            "workstation": session.user.workstation,
            "workstations": workstations,
            "screen_permissions": screen_perms,
        }
        return RedirectResponse(url="/my-page", status_code=303)

    return templates.TemplateResponse(
        "mobile/login.html",
        {
            "request": request,
            "error": "Неверное имя пользователя или пароль",
            "username": username,
        },
    )


@router.get("/my_page", response_class=HTMLResponse)
async def mobile_my_page(request: Request):
    user = get_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse(
        "mobile/my_page.html", {"request": request, "user": user}
    )


# === API ENDPOINTS ===


@router.post("/api/search")
async def api_search(request: Request, query: str = Form(...)):
    user = get_user(request)
    if not user:
        return JSONResponse(
            status_code=401, content={"success": False, "message": "Unauthorized"}
        )

    db = get_db()
    try:
        results = db.search_items(query)[:50]
        return JSONResponse(content={"success": True, "results": results})
    except Exception as e:
        return JSONResponse(
            content={"success": False, "message": str(e)}, status_code=500
        )


@router.post("/api/take_item")
async def api_take_item(
    request: Request,
    item_id: str = Form(...),
    quantity: int = Form(...),
    equipment_name: str = Form(None),
):
    user = get_user(request)
    if not user:
        return JSONResponse(
            status_code=401, content={"success": False, "message": "Unauthorized"}
        )

    db = get_db()
    try:
        from models import Item, Equipment, WorkshopInventory, User
        import json

        with db.get_session() as session:
            # Сначала списываем со склада - проверяем результат
            expense_success = db.expense_item(
                item_id, quantity, user["id"], "Выдача (мобильное)"
            )

            if not expense_success:
                return JSONResponse(
                    content={
                        "success": False,
                        "message": "Недостаточно товара на складе",
                    },
                    status_code=400,
                )

            # Определяем целевой станок
            target_workshop = equipment_name

            if not target_workshop:
                # Получаем станки пользователя
                user_obj = session.query(User).filter(User.id == user["id"]).first()
                workstations = (
                    user_obj.workstations if user_obj and user_obj.workstations else []
                )
                if isinstance(workstations, str):
                    try:
                        import ast

                        workstations = ast.literal_eval(workstations)
                    except:
                        workstations = [workstations] if workstations else []
                if not workstations and user_obj and user_obj.workstation:
                    workstations = [user_obj.workstation]
                target_workshop = workstations[0] if workstations else None

            if not target_workshop:
                return JSONResponse(
                    content={"success": False, "message": "Не указан станок"},
                    status_code=400,
                )

            # Находим оборудование
            equipment = (
                session.query(Equipment)
                .filter(Equipment.name == target_workshop)
                .first()
            )
            if not equipment:
                # Fuzzy matching
                equipment = (
                    session.query(Equipment)
                    .filter(Equipment.name.ilike(f"%{target_workshop}%"))
                    .first()
                )

            if not equipment:
                return JSONResponse(
                    content={
                        "success": False,
                        "message": f"Станок '{target_workshop}' не найден",
                    },
                    status_code=400,
                )

            # Находим item
            item = session.query(Item).filter(Item.item_id == item_id).first()
            if not item:
                return JSONResponse(
                    content={"success": False, "message": "Инструмент не найден"},
                    status_code=404,
                )

            # Добавляем на склад станка
            ws_item = (
                session.query(WorkshopInventory)
                .filter(
                    WorkshopInventory.equipment_id == equipment.id,
                    WorkshopInventory.item_id == item.id,
                )
                .first()
            )

            if ws_item:
                ws_item.quantity += quantity
            else:
                ws_item = WorkshopInventory(
                    equipment_id=equipment.id, item_id=item.id, quantity=quantity
                )
                session.add(ws_item)

            session.commit()
            db.invalidate_items_cache()
            return JSONResponse(
                content={
                    "success": True,
                    "message": f"Инструмент выдан на станок '{target_workshop}'",
                }
            )
    except Exception as e:
        logger.error(f"Take item error: {e}")
        return JSONResponse(
            content={"success": False, "message": str(e)}, status_code=500
        )


@router.post("/api/return_item")
async def api_return_item(
    request: Request,
    item_code: str = Form(...),
    quantity: int = Form(...),
    return_to_workshop: str = Form("false"),
):
    user = get_user(request)
    if not user:
        return JSONResponse(
            status_code=401, content={"success": False, "message": "Unauthorized"}
        )

    db = get_db()
    try:
        db.income_item(item_code, quantity, user["id"], "Возврат (мобильное)")
        db.return_item_from_user(item_code, user["id"], quantity)
        if return_to_workshop.lower() == "true" and user.get("workstation"):
            equipment = db.get_all_equipment()
            eq_map = {eq.get("name"): eq.get("id") for eq in equipment}
            eq_id = eq_map.get(user["workstation"])
            if eq_id:
                db.add_to_workshop_inventory(item_code, eq_id, quantity)
        db.invalidate_items_cache()
        return JSONResponse(
            content={"success": True, "message": "Инструмент возвращен"}
        )
    except Exception as e:
        return JSONResponse(
            content={"success": False, "message": str(e)}, status_code=500
        )


@router.post("/api/writeoff_item")
async def api_writeoff_item(
    request: Request,
    item_code: str = Form(...),
    quantity: int = Form(...),
    reason: str = Form(...),
):
    user = get_user(request)
    if not user:
        return JSONResponse(
            status_code=401, content={"success": False, "message": "Unauthorized"}
        )

    db = get_db()
    try:
        db.writeoff_item_from_user(item_code, user["id"], quantity, reason)
        db.invalidate_items_cache()
        return JSONResponse(content={"success": True, "message": "Инструмент списан"})
    except Exception as e:
        return JSONResponse(
            content={"success": False, "message": str(e)}, status_code=500
        )


@router.get("/api/item/{item_id}")
async def api_get_item(request: Request, item_id: str):
    user = get_user(request)
    if not user:
        return JSONResponse(
            status_code=401, content={"success": False, "message": "Unauthorized"}
        )

    db = get_db()
    try:
        item = db.get_item_by_id(item_id)
        if item:
            return JSONResponse(content={"success": True, "item": item})
        return JSONResponse(
            content={"success": False, "message": "Не найден"}, status_code=404
        )
    except Exception as e:
        return JSONResponse(
            content={"success": False, "message": str(e)}, status_code=500
        )


@router.get("/api/user_items")
async def api_user_items(request: Request):
    user = get_user(request)
    if not user:
        return JSONResponse(
            status_code=401, content={"success": False, "message": "Unauthorized"}
        )

    db = get_db()
    try:
        items = db.get_user_items(user["id"])
        return JSONResponse(content={"success": True, "items": items})
    except Exception as e:
        return JSONResponse(
            content={"success": False, "message": str(e)}, status_code=500
        )


@router.get("/api/workshop_inventory")
async def api_workshop_inventory(request: Request):
    user = get_user(request)
    if not user:
        return JSONResponse(
            status_code=401, content={"success": False, "message": "Unauthorized"}
        )

    db = get_db()
    try:
        equipment = db.get_all_equipment()
        # Создаём маппинг: lowercase name → id
        equipment_map = {
            eq.get("name", "").lower(): eq.get("id")
            for eq in equipment
            if eq.get("name")
        }

        # Собираем workstations
        user_workstations = []
        if user.get("workstation"):
            user_workstations.append(user["workstation"])
        if user.get("workstations"):
            try:
                user_workstations.extend(json.loads(user["workstations"]))
            except:
                pass
        user_workstations = list(
            set(w.strip().lower() for w in user_workstations if w.strip())
        )

        # Fuzzy matching - ищем частичное вхождение workstation в название станка
        user_equipment_ids = []
        for ws in user_workstations:
            for eq_name, eq_id in equipment_map.items():
                if ws in eq_name or eq_name in ws:
                    if eq_id not in user_equipment_ids:
                        user_equipment_ids.append(eq_id)

        all_items = []
        # Создаём обратный маппинг id → name
        id_to_name = {v: k for k, v in equipment_map.items()}
        for eq_id in user_equipment_ids:
            ws_items = db.get_workshop_inventory(equipment_id=eq_id)
            ws_name = id_to_name.get(eq_id, "")
            for item in ws_items:
                if isinstance(item, dict):
                    item["workshop_name"] = ws_name
                    all_items.append(item)
        return JSONResponse(content={"success": True, "items": all_items})
    except Exception as e:
        return JSONResponse(
            content={"success": False, "message": str(e)}, status_code=500
        )


@router.post("/api/return_workshop_item")
async def api_return_workshop_item(
    request: Request,
    inventory_id: int = Form(...),
    item_code: str = Form(...),
    quantity: int = Form(...),
    workshop_name: str = Form(...),
):
    user = get_user(request)
    if not user:
        return JSONResponse(
            status_code=401, content={"success": False, "message": "Unauthorized"}
        )

    db = get_db()
    try:
        db.delete_workshop_inventory_item(inventory_id)
        db.income_item(item_code, quantity, user["id"], f"Возврат из {workshop_name}")
        db.invalidate_items_cache()
        return JSONResponse(
            content={"success": True, "message": "Инструмент возвращен"}
        )
    except Exception as e:
        return JSONResponse(
            content={"success": False, "message": str(e)}, status_code=500
        )


@router.get("/api/tasks")
async def api_tasks(request: Request, period: str = "today"):
    import logging

    logger = logging.getLogger(__name__)
    logger.info(f"api_tasks called with period={period}")

    user = get_user(request)
    if not user:
        logger.warning("User not authenticated")
        return JSONResponse(
            status_code=401, content={"success": False, "message": "Unauthorized"}
        )

    # Только пользователи с ролью "user" могут получать задачи
    if user.get("role") != "user":
        return JSONResponse(
            status_code=403, content={"success": False, "message": "Access denied"}
        )

    logger.info(
        f"User: {user.get('username')}, workstations: {user.get('workstations')}"
    )

    db = get_db()
    try:
        # Собираем workstation'ы - могут быть ID или названия
        raw_workstations = []
        if user.get("workstation"):
            raw_workstations.append(user["workstation"])
        if user.get("workstations"):
            ws = user["workstations"]
            if isinstance(ws, str):
                try:
                    parsed = json.loads(ws)
                    if isinstance(parsed, list):
                        raw_workstations.extend(parsed)
                    elif isinstance(parsed, str):
                        raw_workstations.append(parsed)
                except:
                    try:
                        decoded = bytes(ws, "utf-8").decode("unicode_escape")
                        parsed = json.loads(decoded)
                        if isinstance(parsed, list):
                            raw_workstations.extend(parsed)
                        elif isinstance(parsed, str):
                            raw_workstations.append(parsed)
                    except:
                        raw_workstations.extend(
                            [w.strip() for w in ws.split(",") if w.strip()]
                        )
            elif isinstance(ws, list):
                raw_workstations.extend(ws)

        # Получаем все оборудование
        equipment = db.get_all_equipment()
        equipment_by_id = {eq.get("id"): eq for eq in equipment if eq.get("id")}
        equipment_by_name = {
            eq.get("name", "").lower(): eq.get("id")
            for eq in equipment
            if eq.get("name")
        }

        # Сначала пытаемся использовать как ID (числа)
        user_equipment_ids = []
        for ws in raw_workstations:
            if not ws:
                continue
            # Пробуем как integer ID
            try:
                eq_id = int(ws)
                if eq_id in equipment_by_id and eq_id not in user_equipment_ids:
                    user_equipment_ids.append(eq_id)
                    continue
            except (ValueError, TypeError):
                pass
            # Пробуем как название (fuzzy matching)
            ws_lower = str(ws).lower().strip()
            ws_clean = "".join(c for c in ws_lower if c.isalnum() or c.isspace())
            for eq_name, eq_id in equipment_by_name.items():
                eq_clean = "".join(c for c in eq_name if c.isalnum() or c.isspace())
                if ws_clean in eq_clean or eq_clean in ws_clean or ws_lower in eq_name:
                    if eq_id not in user_equipment_ids:
                        user_equipment_ids.append(eq_id)

        logger.info(f"User raw workstations: {repr(raw_workstations)}")
        logger.info(f"Matched Equipment IDs: {user_equipment_ids}")
        logger.info(f"All equipment IDs: {list(equipment_by_id.keys())}")

        if not user_equipment_ids:
            return JSONResponse(
                content={
                    "success": True,
                    "tasks": [],
                    "debug": {
                        "raw_workstations": raw_workstations,
                        "matched_equipment_ids": [],
                        "all_equipment": [
                            {"id": eq.get("id"), "name": eq.get("name")}
                            for eq in equipment[:10]
                        ],
                    },
                }
            )

        today = datetime.now().date()
        week_end = today + timedelta(days=30)  # Расширено с 7 до 30 дней
        all_tasks = []
        schedule_debug = []

        # DEBUG: получить все запланированные задачи без фильтра по дате
        all_scheduled_debug = []
        for eq_id in user_equipment_ids:
            try:
                all_schedule = db.get_production_schedule(equipment_id=eq_id)
                planned_count = len(
                    [t for t in all_schedule if t.get("status") == "planned"]
                )
                in_progress_count = len(
                    [t for t in all_schedule if t.get("status") == "in_progress"]
                )
                all_scheduled_debug.append(
                    {
                        "equipment_id": eq_id,
                        "total_in_db": len(all_schedule),
                        "planned_in_db": planned_count,
                        "in_progress_in_db": in_progress_count,
                    }
                )
            except Exception as e:
                logger.error(f"Debug schedule error: {e}")

        for eq_id in user_equipment_ids:
            try:
                schedule = db.get_production_schedule(
                    date_from=today.isoformat(),
                    date_to=week_end.isoformat(),
                    equipment_id=eq_id,
                )
                schedule_debug.append(
                    {
                        "equipment_id": eq_id,
                        "total_tasks": len(schedule),
                        "tasks_statuses": list(set(t.get("status") for t in schedule))
                        if schedule
                        else [],
                        "planned_count": len(
                            [t for t in schedule if t.get("status") == "planned"]
                        ),
                        "in_progress_count": len(
                            [t for t in schedule if t.get("status") == "in_progress"]
                        ),
                    }
                )
                for task in schedule:
                    # Показываем planned и in_progress
                    if task.get("status") not in ("planned", "in_progress"):
                        continue

                    # Фильтруем по дате ДО сериализации
                    if period == "today":
                        task_date = task.get("planned_date")
                        if isinstance(task_date, str):
                            try:
                                task_date = datetime.strptime(
                                    task_date[:10], "%Y-%m-%d"
                                ).date()
                            except:
                                try:
                                    task_date = datetime.strptime(
                                        task_date, "%d.%m.%Y"
                                    ).date()
                                except:
                                    continue
                        elif hasattr(task_date, "date"):
                            task_date = task_date.date()

                        if task_date != today:
                            continue

                    # Сериализуем datetime в строки для JSON
                    task_copy = {}
                    for k, v in task.items():
                        if isinstance(v, datetime):
                            task_copy[k] = v.isoformat()
                        else:
                            task_copy[k] = v

                    task = task_copy

                    # Добавляем события
                    task_id = task.get("id")
                    events = db.get_schedule_events(task_id) if task_id else []
                    task["events"] = [e["event_type"] for e in events]
                    task["has_no_drawing"] = "no_drawing" in task["events"]
                    task["has_no_nc_program"] = "no_nc_program" in task["events"]
                    task["has_first_piece_checked"] = (
                        "first_piece_checked" in task["events"]
                    )
                    task["has_otk_pending"] = "otk_pending" in task["events"]
                    task["has_otk_approved"] = "otk_approved" in task["events"]
                    task["has_otk_rejected"] = "otk_rejected" in task["events"]

                    # Добавляем инструменты из route_card_data заказа
                    order_id = task.get("order_id")
                    if order_id:
                        order_tools = db.get_order_tools(order_id)
                        task["tools"] = order_tools
                        logger.info(f"Task {task_id}: loaded {len(order_tools)} tools from order {order_id}")

                    # Среднее время на деталь
                    if task.get("taken_at") and task.get("completed_at"):
                        try:
                            from datetime import datetime as dt

                            t1 = dt.fromisoformat(task["taken_at"])
                            t2 = dt.fromisoformat(task["completed_at"])
                            elapsed_min = (t2 - t1).total_seconds() / 60
                            qty = (
                                task.get("actual_quantity") or task.get("quantity") or 1
                            )
                            task["avg_time_per_unit"] = round(elapsed_min / qty, 1)
                        except:
                            task["avg_time_per_unit"] = None
                    else:
                        task["avg_time_per_unit"] = None

                    all_tasks.append(task)
            except Exception as e:
                logger.error(f"Error loading schedule for eq {eq_id}: {e}")

        return JSONResponse(
            content={
                "success": True,
                "tasks": all_tasks,
                "debug": {
                    "raw_workstations": raw_workstations,
                    "user_equipment_ids": user_equipment_ids,
                    "schedule_debug": schedule_debug,
                    "all_scheduled_debug": all_scheduled_debug,
                },
            }
        )
    except Exception as e:
        logger.error(f"Error in api_tasks: {e}")
        return JSONResponse(
            content={
                "success": False,
                "message": str(e),
            },
            status_code=500,
        )


@router.post("/api/take_task_with_tools")
async def api_take_task_with_tools(
    request: Request, schedule_id: int = Form(...), tools_json: str = Form(...)
):
    """Взять задачу в работу с инструментами"""
    user = get_user(request)
    if not user:
        return JSONResponse(
            status_code=401, content={"success": False, "message": "Unauthorized"}
        )

    db = get_db()
    try:
        import json

        tools = json.loads(tools_json) if tools_json else []

        # Получаем schedule для проверки
        schedule = db.get_schedule_by_id(schedule_id)
        if not schedule:
            return JSONResponse(
                content={"success": False, "message": "Задача не найдена"},
                status_code=404,
            )

        order_id = schedule.get("order_id")

        # Сохраняем инструменты в route_card_data заказа
        if order_id and tools:
            from models import Order

            with db.get_session() as session:
                order = session.query(Order).filter(Order.id == order_id).first()
                if order:
                    existing_tools = []
                    if order.route_card_data:
                        try:
                            # Проверяем: если уже dict - используем как есть
                            if isinstance(order.route_card_data, dict):
                                rcd = order.route_card_data
                            else:
                                rcd = json.loads(order.route_card_data)
                            existing_tools = rcd.get("tools", [])
                        except:
                            pass

                    # Получаем информацию об операции из schedule
                    route_operation_id = schedule.get("route_operation_id")
                    operation_name = schedule.get("operation_name", "")
                    equipment_name = schedule.get("equipment_name", "")
                    
                    # Добавляем новые инструменты
                    for tool in tools:
                        tool_data = {
                            "item_id": tool.get("item_id"),
                            "item_name": tool.get("item_name"),
                            "quantity": tool.get("quantity"),
                            "source": tool.get("source"),
                            "source_name": tool.get("source_name"),
                            "equipment_id": tool.get("equipment_id"),
                        }
                        # Добавляем информацию об операции если есть - из schedule или из tool
                        if tool.get("operation_name"):
                            tool_data["operation_name"] = tool.get("operation_name")
                        elif operation_name:
                            tool_data["operation_name"] = operation_name
                        if tool.get("operation_id"):
                            tool_data["operation_id"] = tool.get("operation_id")
                        elif route_operation_id:
                            tool_data["operation_id"] = route_operation_id
                        # Добавляем станок
                        if tool.get("equipment_name"):
                            tool_data["equipment_name"] = tool.get("equipment_name")
                        elif equipment_name:
                            tool_data["equipment_name"] = equipment_name
                        existing_tools.append(tool_data)

                    # НЕ списываем инструменты со склада - они остаются на складе станка
                    # Инструменты только "бронируются" за заказом для отображения

                    # Сохраняем обновленные инструменты - сливаем с существующими данными
                    # Сначала получаем полные данные
                    full_rcd = {}
                    if order.route_card_data:
                        try:
                            if isinstance(order.route_card_data, dict):
                                full_rcd = order.route_card_data
                            else:
                                full_rcd = json.loads(order.route_card_data)
                        except:
                            pass
                    
                    # Обновляем tools
                    full_rcd["tools"] = existing_tools
                    
                    order.route_card_data = json.dumps(full_rcd)
                    session.commit()
                    logger.info(f"Saved tools to order {order_id}: {len(existing_tools)} tools")

        # Берем задачу в работу
        db.mark_schedule_taken(schedule_id, user["username"])

        return JSONResponse(
            content={"success": True, "message": "Задача взята в работу"}
        )
    except Exception as e:
        logger.error(f"Take task with tools error: {e}")
        return JSONResponse(
            content={"success": False, "message": str(e)}, status_code=500
        )


@router.post("/api/take_task")
async def api_take_task(request: Request, schedule_id: int = Form(...)):
    user = get_user(request)
    if not user:
        return JSONResponse(
            status_code=401, content={"success": False, "message": "Unauthorized"}
        )

    db = get_db()
    try:
        # Получаем schedule для проверки
        schedule = db.get_schedule_by_id(schedule_id)
        if not schedule:
            return JSONResponse(
                content={"success": False, "message": "Задача не найдена"},
                status_code=404,
            )

        # Проверяем, есть ли уже инструменты в route_card_data заказа
        order_id = schedule.get("order_id")
        if order_id:
            from models import Order
            import json

            with db.get_session() as session:
                order = session.query(Order).filter(Order.id == order_id).first()
                if order and order.route_card_data:
                    try:
                        rcd = json.loads(order.route_card_data)
                        tools = rcd.get("tools", [])
                    except:
                        tools = []
                    if tools:
                        # Инструменты уже есть — просто берем задачу
                        db.mark_schedule_taken(schedule_id, user["username"])
                        return JSONResponse(
                            content={
                                "success": True,
                                "message": "Задача взята в работу",
                                "tools_already_selected": True,
                            }
                        )

        # Инструменты не выбраны — возвращаем сигнал для выбора
        db.mark_schedule_taken(schedule_id, user["username"])
        return JSONResponse(
            content={
                "success": True,
                "message": "Задача взята в работу",
                "tools_already_selected": False,
                "need_select_tools": True,
                "order_id": order_id,
            }
        )
    except Exception as e:
        return JSONResponse(
            content={"success": False, "message": str(e)}, status_code=500
        )


@router.post("/api/complete_task")
async def api_complete_task(
    request: Request, schedule_id: int = Form(...), actual_quantity: int = Form(...)
):
    user = get_user(request)
    if not user:
        return JSONResponse(
            status_code=401, content={"success": False, "message": "Unauthorized"}
        )

    db = get_db()
    result = db.complete_task_with_recalc(
        schedule_id, actual_quantity, user["username"]
    )
    if result["success"]:
        return JSONResponse(
            content={
                "success": True,
                "message": result["message"],
                "remainder": result.get("remainder", 0),
            }
        )
    return JSONResponse(
        content={"success": False, "message": result["message"]}, status_code=500
    )


@router.post("/api/save_order_tools")
async def api_save_order_tools(
    request: Request, order_id: int = Form(...), tools_json: str = Form(...)
):
    """Сохранить инструменты для заказа"""
    user = get_user(request)
    if not user:
        return JSONResponse(
            status_code=401, content={"success": False, "message": "Unauthorized"}
        )

    import json

    try:
        tools = json.loads(tools_json)
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=400, content={"success": False, "message": "Invalid JSON"}
        )

    db = get_db()
    try:
        from models import Order

        with db.get_session() as session:
            import json

            order = session.query(Order).filter(Order.id == order_id).first()
            if not order:
                return JSONResponse(
                    status_code=404,
                    content={"success": False, "message": "Заказ не найден"},
                )

            # Десериализуем JSON
            route_card_data = {}
            if order.route_card_data:
                try:
                    route_card_data = json.loads(order.route_card_data)
                except:
                    pass
            route_card_data["tools"] = tools
            order.route_card_data = json.dumps(route_card_data)
            session.commit()

        return JSONResponse(
            content={"success": True, "tools": tools, "message": "Инструменты сохранены"}
        )
    except Exception as e:
        return JSONResponse(
            content={"success": False, "message": str(e)}, status_code=500
        )


@router.post("/api/flag_no_drawing")
async def api_flag_no_drawing(request: Request, schedule_id: int = Form(...)):
    user = get_user(request)
    if not user:
        return JSONResponse(
            status_code=401, content={"success": False, "message": "Unauthorized"}
        )

    db = get_db()
    ok = db.create_schedule_event(schedule_id, "no_drawing", user["username"])
    return JSONResponse(
        content={
            "success": ok,
            "message": "Флаг 'Нет чертежа' установлен" if ok else "Ошибка",
        }
    )


@router.post("/api/flag_no_nc_program")
async def api_flag_no_nc_program(request: Request, schedule_id: int = Form(...)):
    user = get_user(request)
    if not user:
        return JSONResponse(
            status_code=401, content={"success": False, "message": "Unauthorized"}
        )

    db = get_db()
    ok = db.create_schedule_event(schedule_id, "no_nc_program", user["username"])
    return JSONResponse(
        content={
            "success": ok,
            "message": "Флаг 'Нет УП' установлен" if ok else "Ошибка",
        }
    )


@router.post("/api/flag_first_piece")
async def api_flag_first_piece(request: Request, schedule_id: int = Form(...)):
    user = get_user(request)
    if not user:
        return JSONResponse(
            status_code=401, content={"success": False, "message": "Unauthorized"}
        )

    db = get_db()
    ok = db.create_schedule_event(schedule_id, "first_piece_checked", user["username"])
    return JSONResponse(
        content={
            "success": ok,
            "message": "Первая деталь проверена" if ok else "Ошибка",
        }
    )


@router.post("/api/send_to_otk")
async def api_send_to_otk(request: Request, schedule_id: int = Form(...)):
    """Отправить деталь на проверку ОТК"""
    user = get_user(request)
    if not user:
        return JSONResponse(
            status_code=401, content={"success": False, "message": "Unauthorized"}
        )

    db = get_db()

    schedule = db.get_schedule_item(schedule_id)
    if not schedule:
        return JSONResponse(
            content={"success": False, "message": "Задача не найдена"}, status_code=404
        )

    if schedule.get("status") not in ("in_progress", "planned"):
        return JSONResponse(
            content={"success": False, "message": "Задача не в работе"}, status_code=400
        )

    ok = db.create_otk_event(schedule_id, "otk_pending", user["username"])

    return JSONResponse(
        content={
            "success": ok,
            "message": "Деталь отправлена на ОТК" if ok else "Ошибка",
        }
    )


# ============================================================
# MY IN PROGRESS TASKS — задачи в работе пользователя
# ============================================================


@router.get("/api/my-in-progress-tasks")
async def api_my_in_progress_tasks(request: Request):
    """Получить задачи пользователя в работе (in_progress)"""
    import logging

    logger = logging.getLogger(__name__)
    logger.info("api_my_in_progress_tasks called")

    user = get_user(request)
    if not user:
        logger.warning("User not authenticated")
        return JSONResponse(
            status_code=401, content={"success": False, "message": "Unauthorized"}
        )

    # Только пользователи с ролью "user"
    if user.get("role") != "user":
        return JSONResponse(
            status_code=403, content={"success": False, "message": "Access denied"}
        )

    logger.info(
        f"User: {user.get('username')}, workstations: {user.get('workstations')}"
    )

    db = get_db()
    try:
        # Собираем workstation'ы
        raw_workstations = []
        if user.get("workstation"):
            raw_workstations.append(user["workstation"])
        if user.get("workstations"):
            ws = user["workstations"]
            if isinstance(ws, str):
                try:
                    parsed = json.loads(ws)
                    if isinstance(parsed, list):
                        raw_workstations.extend(parsed)
                    elif isinstance(parsed, str):
                        raw_workstations.append(parsed)
                except:
                    try:
                        decoded = bytes(ws, "utf-8").decode("unicode_escape")
                        parsed = json.loads(decoded)
                        if isinstance(parsed, list):
                            raw_workstations.extend(parsed)
                        elif isinstance(parsed, str):
                            raw_workstations.append(parsed)
                    except:
                        raw_workstations.extend(
                            [w.strip() for w in ws.split(",") if w.strip()]
                        )
            elif isinstance(ws, list):
                raw_workstations.extend(ws)

        # Получаем все оборудование
        equipment = db.get_all_equipment()
        equipment_by_id = {eq.get("id"): eq for eq in equipment if eq.get("id")}
        equipment_by_name = {
            eq.get("name", "").lower(): eq.get("id")
            for eq in equipment
            if eq.get("name")
        }

        # Fuzzy matching工作站
        user_equipment_ids = []
        for ws in raw_workstations:
            if not ws:
                continue
            try:
                eq_id = int(ws)
                if eq_id in equipment_by_id and eq_id not in user_equipment_ids:
                    user_equipment_ids.append(eq_id)
                    continue
            except (ValueError, TypeError):
                pass
            ws_lower = str(ws).lower().strip()
            ws_clean = "".join(c for c in ws_lower if c.isalnum() or c.isspace())
            for eq_name, eq_id in equipment_by_name.items():
                eq_clean = "".join(c for c in eq_name if c.isalnum() or c.isspace())
                if ws_clean in eq_clean or eq_clean in eq_clean or ws_lower in eq_name:
                    if eq_id not in user_equipment_ids:
                        user_equipment_ids.append(eq_id)

        logger.info(f"User raw workstations: {repr(raw_workstations)}")
        logger.info(f"Matched Equipment IDs: {user_equipment_ids}")

        if not user_equipment_ids:
            return JSONResponse(
                content={
                    "success": True,
                    "tasks": [],
                    "debug": {
                        "raw_workstations": raw_workstations,
                        "matched_equipment_ids": [],
                    },
                }
            )

        all_tasks = []

        # Получаем задачи для всех станков пользователя (без фильтра по дате)
        for eq_id in user_equipment_ids:
            try:
                # Получаем ВСЕ расписание для станка (без фильтра по дате)
                schedule = db.get_production_schedule(equipment_id=eq_id)

                for task in schedule:
                    # Показываем ТОЛЬКО in_progress (не planned!)
                    if task.get("status") != "in_progress":
                        continue

                    # ФИЛЬТР: показываем только задачи, которые ЭТОТ пользователь взял
                    task_taken_by = task.get("taken_by")
                    current_username = user.get("username")
                    if task_taken_by and task_taken_by != current_username:
                        # Если задачу взял другой пользователь - пропускаем
                        continue

                    # Сериализуем datetime в строки для JSON
                    task_copy = {}
                    for k, v in task.items():
                        if isinstance(v, datetime):
                            task_copy[k] = v.isoformat()
                        else:
                            task_copy[k] = v

                    task = task_copy

                    # Добавляем события
                    task_id = task.get("id")
                    events = db.get_schedule_events(task_id) if task_id else []
                    task["events"] = [e["event_type"] for e in events]
                    task["has_no_drawing"] = "no_drawing" in task["events"]
                    task["has_no_nc_program"] = "no_nc_program" in task["events"]
                    task["has_first_piece_checked"] = (
                        "first_piece_checked" in task["events"]
                    )
                    task["has_otk_pending"] = "otk_pending" in task["events"]
                    task["has_otk_approved"] = "otk_approved" in task["events"]
                    task["has_otk_rejected"] = "otk_rejected" in task["events"]

                    # Добавляем инструменты из route_card_data заказа
                    order_id = task.get("order_id")
                    if order_id:
                        order_tools = db.get_order_tools(order_id)
                        task["tools"] = order_tools
                        logger.info(f"Task {task_id}: loaded {len(order_tools)} tools from order {order_id}")

                    all_tasks.append(task)
            except Exception as e:
                logger.error(f"Error loading schedule for eq {eq_id}: {e}")

        return JSONResponse(
            content={
                "success": True,
                "tasks": all_tasks,
                "debug": {
                    "raw_workstations": raw_workstations,
                    "user_equipment_ids": user_equipment_ids,
                    "task_count": len(all_tasks),
                },
            }
        )
    except Exception as e:
        logger.error(f"Error in api_my_in_progress_tasks: {e}")
        return JSONResponse(
            content={
                "success": False,
                "message": str(e),
            },
            status_code=500,
        )


# ============================================================
# QR SCANNER — страница сканера
# ============================================================


@router.get("/qr-scanner", response_class=HTMLResponse)
async def qr_scanner_page(request: Request):
    user = get_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse(
        "mobile/qr_scanner.html", {"request": request, "user": user}
    )


# ============================================================
# QR SCANNER — API endpoints
# ============================================================


@router.post("/api/qr/scan")
async def qr_scan(request: Request, scan_url: str = Form(...)):
    """Parse QR code URL and return order/route info"""
    user = get_user(request)
    if not user:
        return JSONResponse(
            status_code=401, content={"success": False, "message": "Unauthorized"}
        )

    db = get_db()
    try:
        from services.qr_scanner_handler import QRScannerHandler

        handler = QRScannerHandler(db)

        parsed = handler.parse_qr_url(scan_url)
        if not parsed:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": "Неверный формат QR-кода. Ожидается: sklad://order/{id}?route={id}",
                },
            )

        order_id = parsed["order_id"]
        route_id = parsed["route_id"]

        result = handler.get_full_qr_result(order_id, route_id)
        if not result.get("success"):
            return JSONResponse(status_code=404, content=result)

        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(
            content={"success": False, "error": str(e)}, status_code=500
        )


@router.post("/api/qr/take-order")
async def take_order(
    request: Request, order_id: int = Form(...), route_id: int = Form(None)
):
    """Mark order as taken (started)"""
    user = get_user(request)
    if not user:
        return JSONResponse(
            status_code=401, content={"success": False, "message": "Unauthorized"}
        )

    db = get_db()
    try:
        from services.qr_scanner_handler import QRScannerHandler

        handler = QRScannerHandler(db)

        result = handler.take_order(order_id, user["username"])
        if not result.get("success"):
            status_code = (
                409
                if result.get("already_taken") or result.get("already_completed")
                else 400
            )
            return JSONResponse(content=result, status_code=status_code)

        # Return updated order info
        full_result = handler.get_full_qr_result(order_id, route_id)
        full_result.update(result)
        return JSONResponse(content=full_result)
    except Exception as e:
        return JSONResponse(
            content={"success": False, "error": str(e)}, status_code=500
        )


@router.post("/api/qr/complete-order")
async def complete_order(
    request: Request, order_id: int = Form(...), route_id: int = Form(None)
):
    """Mark order as completed"""
    user = get_user(request)
    if not user:
        return JSONResponse(
            status_code=401, content={"success": False, "message": "Unauthorized"}
        )

    db = get_db()
    try:
        from services.qr_scanner_handler import QRScannerHandler

        handler = QRScannerHandler(db)

        result = handler.complete_order(order_id, user["username"])
        if not result.get("success"):
            status_code = 409 if result.get("already_completed") else 400
            return JSONResponse(content=result, status_code=status_code)

        # Return updated order info with statistics
        full_result = handler.get_full_qr_result(order_id, route_id)
        full_result.update(result)
        return JSONResponse(content=full_result)
    except Exception as e:
        return JSONResponse(
            content={"success": False, "error": str(e)}, status_code=500
        )


@router.get("/api/qr/order-status/{order_id}")
async def get_order_status(request: Request, order_id: int):
    """Get order status and statistics"""
    user = get_user(request)
    if not user:
        return JSONResponse(
            status_code=401, content={"success": False, "message": "Unauthorized"}
        )

    db = get_db()
    try:
        from services.qr_scanner_handler import QRScannerHandler

        handler = QRScannerHandler(db)

        result = handler.get_order_status(order_id)
        if not result.get("success"):
            return JSONResponse(status_code=404, content=result)

        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(
            content={"success": False, "error": str(e)}, status_code=500
        )


@router.get("/api/qr/route-info/{route_id}")
async def get_route_info(request: Request, route_id: int):
    """Get route details for display after scan"""
    user = get_user(request)
    if not user:
        return JSONResponse(
            status_code=401, content={"success": False, "message": "Unauthorized"}
        )

    db = get_db()
    try:
        from services.qr_scanner_handler import QRScannerHandler

        handler = QRScannerHandler(db)

        result = handler.get_route_info(route_id)
        if not result.get("success"):
            return JSONResponse(status_code=404, content=result)

        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(
            content={"success": False, "error": str(e)}, status_code=500
        )


@router.post("/api/order/take-with-tools")
async def take_order_with_tools(
    request: Request, order_id: int = Form(...), tools_json: str = Form(...)
):
    """Взять заказ с инструментами"""
    user = get_user(request)
    if not user:
        return JSONResponse(
            status_code=401, content={"success": False, "message": "Unauthorized"}
        )

    import json

    try:
        tools = json.loads(tools_json)
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=400, content={"success": False, "message": "Invalid JSON"}
        )

    db = get_db()
    try:
        from services.qr_scanner_handler import QRScannerHandler

        handler = QRScannerHandler(db)
        result = handler.take_order(order_id, user["username"])

        if not result.get("success"):
            return JSONResponse(content=result, status_code=400)

        if tools:
            db.take_tools_for_order(order_id, tools, user["id"])
            db.invalidate_items_cache()

        return JSONResponse(
            content={"success": True, "message": "Заказ взят с инструментами"}
        )
    except Exception as e:
        return JSONResponse(
            content={"success": False, "message": str(e)}, status_code=500
        )


@router.post("/api/order/complete-with-tools")
async def complete_order_with_tools(
    request: Request, order_id: int = Form(...), tools_json: str = Form(...)
):
    """Завершить заказ с инструментами"""
    user = get_user(request)
    if not user:
        return JSONResponse(
            status_code=401, content={"success": False, "message": "Unauthorized"}
        )

    import json

    try:
        tools = json.loads(tools_json)
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=400, content={"success": False, "message": "Invalid JSON"}
        )

    db = get_db()
    try:
        from services.qr_scanner_handler import QRScannerHandler

        handler = QRScannerHandler(db)
        result = handler.complete_order(order_id, user["username"])

        if not result.get("success"):
            return JSONResponse(content=result, status_code=400)

        if tools:
            db.complete_tools_for_order(order_id, tools, user["id"])
            db.invalidate_items_cache()

        return JSONResponse(
            content={"success": True, "message": "Завершено с инструментами"}
        )
    except Exception as e:
        return JSONResponse(
            content={"success": False, "message": str(e)}, status_code=500
        )


@router.get("/api/user/available-tools")
async def get_user_available_tools(
    request: Request, search: str = None, equipment_id: int = None
):
    """Получить доступные инструменты для пользователя или конкретного станка"""
    user = get_user(request)
    if not user:
        return JSONResponse(
            status_code=401, content={"success": False, "message": "Unauthorized"}
        )

    db = get_db()
    try:
        tools = db.get_user_available_tools(user["id"], search, equipment_id)
        logger.info(
            f"available-tools response: {len(tools)} tools, equipment_id={equipment_id}"
        )
        logger.info(f"First 3 tools: {tools[:3] if tools else 'none'}")
        return JSONResponse(content={"success": True, "tools": tools})
    except Exception as e:
        logger.error(f"available-tools error: {e}")
        return JSONResponse(
            content={"success": False, "message": str(e)}, status_code=500
        )


@router.post("/api/move-tool-to-workshop")
async def move_tool_to_workshop(
    request: Request,
    item_id: str = Form(...),
    quantity: int = Form(...),
    equipment_name: str = Form(None),
):
    """Переместить инструмент на склад станка"""
    user = get_user(request)
    if not user:
        return JSONResponse(
            status_code=401, content={"success": False, "message": "Unauthorized"}
        )

    db = get_db()
    try:
        from models import Item, WorkshopInventory, User, Equipment, UserItems
        import json

        with db.get_session() as session:
            # Получаем станок пользователя
            user_obj = session.query(User).filter(User.id == user["id"]).first()

            # Поддержка нескольких станков
            workstations = user_obj.workstations if user_obj else []
            if isinstance(workstations, str):
                import ast

                try:
                    workstations = ast.literal_eval(workstations)
                except:
                    workstations = [workstations]

            if not workstations:
                # Пробуем одиночный станок
                workstations = (
                    [user_obj.workstation] if user_obj and user_obj.workstation else []
                )

            if not workstations:
                return JSONResponse(
                    status_code=400,
                    content={
                        "success": False,
                        "message": "У пользователя не указан станок",
                    },
                )

            # Если станок не указан, используем первый
            target_equipment_name = equipment_name
            if not target_equipment_name:
                target_equipment_name = workstations[0] if workstations else None

            if not target_equipment_name:
                return JSONResponse(
                    status_code=400,
                    content={"success": False, "message": "Не указан станок"},
                )

            equipment = (
                session.query(Equipment)
                .filter(Equipment.name == target_equipment_name)
                .first()
            )
            if not equipment:
                return JSONResponse(
                    status_code=400,
                    content={
                        "success": False,
                        "message": f"Станок '{target_equipment_name}' не найден",
                    },
                )

            # Получаем item
            item = session.query(Item).filter(Item.item_id == item_id).first()
            if not item:
                return JSONResponse(
                    status_code=404,
                    content={"success": False, "message": "Инструмент не найден"},
                )

            # Добавляем на склад станка
            ws_item = (
                session.query(WorkshopInventory)
                .filter(
                    WorkshopInventory.equipment_id == equipment.id,
                    WorkshopInventory.item_id == item.id,
                )
                .first()
            )

            if ws_item:
                ws_item.quantity += quantity
            else:
                ws_item = WorkshopInventory(
                    equipment_id=equipment.id, item_id=item.id, quantity=quantity
                )
                session.add(ws_item)

            # Удаляем из "Мои инструменты" пользователя
            user_item = (
                session.query(UserItems)
                .filter(
                    UserItems.user_id == user_obj.id,
                    UserItems.item_id == item.id,
                )
                .first()
            )
            if user_item:
                if user_item.quantity > quantity:
                    user_item.quantity -= quantity
                else:
                    session.delete(user_item)

            session.commit()
            return JSONResponse(
                content={
                    "success": True,
                    "message": f"Инструмент перемещен на склад станка '{target_equipment_name}'",
                }
            )
    except Exception as e:
        logger.error(f"Move tool error: {e}")
        return JSONResponse(
            content={"success": False, "message": str(e)}, status_code=500
        )


@router.get("/api/orders-in-work")
async def api_orders_in_work(request: Request):
    """Получить заказы в работе"""
    user = get_user(request)
    if not user:
        return JSONResponse(
            status_code=401, content={"success": False, "message": "Unauthorized"}
        )

    db = get_db()
    try:
        # Получаем ID оборудования пользователя
        equipment_ids = []

        # Единый способ получения станков
        raw_workstations = []
        if user.get("workstation"):
            raw_workstations.append(user["workstation"])
        if user.get("workstations"):
            try:
                ws = json.loads(user["workstations"])
                if isinstance(ws, list):
                    raw_workstations.extend(ws)
                elif isinstance(ws, str):
                    raw_workstations.append(ws)
            except:
                raw_workstations.extend(
                    [w.strip() for w in user["workstations"].split(",") if w.strip()]
                )

        equipment = db.get_all_equipment()
        equipment_by_name = {
            eq.get("name", "").lower(): eq.get("id")
            for eq in equipment
            if eq.get("name")
        }

        for ws in raw_workstations:
            if not ws:
                continue
            ws_lower = str(ws).lower().strip()
            for eq_name, eq_id in equipment_by_name.items():
                if ws_lower in eq_name or eq_name in ws_lower:
                    if eq_id not in equipment_ids:
                        equipment_ids.append(eq_id)

        if not equipment_ids:
            return JSONResponse(content={"success": True, "orders": []})

        # Получаем заказы в работе для станков пользователя
        orders = []
        for eq_id in equipment_ids:
            try:
                schedule = db.get_production_schedule(equipment_id=eq_id)
                for item in schedule:
                    if item.get("status") == "in_progress":
                        order_id = item.get("order_id")
                        # Проверяем, не завершён ли уже
                        order = db.get_order(order_id)
                        if order and order.get("status") != "completed":
                            # Проверяем, не добавлен ли уже
                            existing = next(
                                (o for o in orders if o["id"] == order_id), None
                            )
                            if not existing:
                                # Получаем инструменты из route_card_data
                                tool_names = ""
                                route_card_data = order.get("route_card_data", {})
                                if route_card_data and isinstance(
                                    route_card_data, dict
                                ):
                                    tools = route_card_data.get("tools", [])
                                    if tools:
                                        tool_names = ", ".join(
                                            [t.get("item_name", "") for t in tools[:3]]
                                        )
                                        if len(tools) > 3:
                                            tool_names += f" (+{len(tools) - 3})"

                                orders.append(
                                    {
                                        "id": order_id,
                                        "product_name": order.get("product_name", ""),
                                        "status": order.get("status", ""),
                                        "tool_names": tool_names,
                                    }
                                )
            except Exception as e:
                logger.error(f"Error getting schedule: {e}")

        return JSONResponse(content={"success": True, "orders": orders})
    except Exception as e:
        logger.error(f"Orders in work error: {e}")
        return JSONResponse(
            content={"success": False, "message": str(e)}, status_code=500
        )


@router.get("/api/order/tools/{order_id}")
async def get_order_tools(request: Request, order_id: int):
    """Получить инструменты заказа"""
    user = get_user(request)
    if not user:
        return JSONResponse(
            status_code=401, content={"success": False, "message": "Unauthorized"}
        )

    db = get_db()
    try:
        from models import Order
        import json

        with db.get_session() as session:
            order = session.query(Order).filter(Order.id == order_id).first()
            if not order:
                return JSONResponse(
                    status_code=404,
                    content={"success": False, "message": "Заказ не найден"},
                )

            tools = []
            if order.route_card_data:
                try:
                    rcd = json.loads(order.route_card_data)
                    tools = rcd.get("tools", [])
                except:
                    pass

            return JSONResponse(content={"success": True, "tools": tools})
    except Exception as e:
        logger.error(f"Get order tools error: {e}")
        return JSONResponse(
            content={"success": False, "message": str(e)}, status_code=500
        )


@router.post("/api/order/complete-with-tool-actions")
async def api_complete_with_tool_actions(
    request: Request,
    schedule_id: int = Form(...),
    actual_quantity: int = Form(...),
    tools_json: str = Form(...),
):
    """Завершить задачу с инструментами (списать/вернуть)"""
    user = get_user(request)
    if not user:
        return JSONResponse(
            status_code=401, content={"success": False, "message": "Unauthorized"}
        )

    import json

    try:
        tool_actions = json.loads(tools_json) if tools_json else []
    except json.JSONDecodeError:
        tool_actions = []

    db = get_db()
    try:
        # Сначала завершаем задачу
        result = db.complete_task_with_recalc(
            schedule_id, actual_quantity, user["username"]
        )
        if not result["success"]:
            return JSONResponse(
                content={"success": False, "message": result["message"]},
                status_code=500,
            )

        # Обрабатываем инструменты
        for action in tool_actions:
            item_id = action.get("item_id")
            quantity = action.get("quantity", 1)
            action_type = action.get("action")  # "writeoff" или "return"
            equipment_id = action.get("equipment_id")

            if action_type == "writeoff":
                # Списываем инструмент
                try:
                    db.writeoff_item_from_user(
                        item_id,
                        user["id"],
                        quantity,
                        "Списание при завершении операции",
                    )
                except Exception as e:
                    logger.error(f"Writeoff error: {e}")

            elif action_type == "return" and equipment_id:
                # Возвращаем на склад станка
                try:
                    db.add_to_workshop_inventory(item_id, equipment_id, quantity)
                    # Также удаляем из "Мои инструменты"
                    db.return_item_from_user(item_id, user["id"], quantity)
                except Exception as e:
                    logger.error(f"Return to workshop error: {e}")

        db.invalidate_items_cache()
        return JSONResponse(
            content={
                "success": True,
                "message": "Задача завершена",
                "remainder": result.get("remainder", 0),
            }
        )
    except Exception as e:
        logger.error(f"Complete with tools error: {e}")
        return JSONResponse(
            content={"success": False, "message": str(e)}, status_code=500
        )


@router.post("/api/order/complete")
async def api_order_complete(request: Request, order_id: int = Form(...)):
    """Завершить заказ"""
    user = get_user(request)
    if not user:
        return JSONResponse(
            status_code=401, content={"success": False, "message": "Unauthorized"}
        )

    db = get_db()
    try:
        from models import Order

        with db.get_session() as session:
            order = session.query(Order).filter(Order.id == order_id).first()
            if not order:
                return JSONResponse(
                    status_code=404,
                    content={"success": False, "message": "Заказ не найден"},
                )

            order.status = "completed"
            session.commit()

        return JSONResponse(content={"success": True, "message": "Заказ завершён"})
    except Exception as e:
        logger.error(f"Complete order error: {e}")
        return JSONResponse(
            content={"success": False, "message": str(e)}, status_code=500
        )
