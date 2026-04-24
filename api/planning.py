"""API роуты для планирования производства"""

from fastapi import APIRouter, Request, Query, HTTPException, Body
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from main import get_db, get_user
from datetime import datetime, timedelta, date
from typing import Optional
import os
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/planning", tags=["planning"])
templates = Jinja2Templates(directory="templates")


def _count_working_days(year: int, month: int) -> int:
    """Посчитать рабочие дни в месяце (Пн-Пт)"""
    import calendar

    cal = calendar.monthcalendar(year, month)
    count = 0
    for week in cal:
        for day_idx, day in enumerate(week):
            if day > 0 and day_idx < 5:  # Пн-Пт
                count += 1
    return count


def _get_first_day_weekday(year: int, month: int) -> int:
    """Вернуть день недели 1-го числа (0=Пн, 6=Вс)"""
    import calendar

    # calendar.monthrange возвращает (weekday первого дня, дней в месяце)
    # calendar.weekday: 0=Пн ... 6=Вс
    return calendar.monthrange(year, month)[0]


# ==================== PAGE ROUTES ====================


@router.get("/plan", response_class=HTMLResponse)
async def plan_page(request: Request, highlight_order: int = None):
    """Страница плана заказов"""
    user = get_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    db = get_db()
    try:
        orders = db.get_all_orders()
        # Обогащаем заказы информацией о расписании и операциях
        for order in orders:
            order_id = order.get("id")
            schedule = db.get_production_schedule(order_id=order_id)

            # Если есть расписание - рассчитываем даты окончания
            for item in schedule:
                planned_date = item.get("planned_date")
                if not planned_date:
                    continue

                start_date = planned_date
                if isinstance(start_date, str):
                    start_date = datetime.strptime(start_date, "%Y-%m-%d")
                elif isinstance(start_date, date):
                    start_date = datetime.combine(start_date, datetime.min.time())

                # Логируем данные для отладки
                is_coop = item.get("is_cooperation")
                coop_days = item.get("coop_duration_days")
                coop_company = item.get("coop_company_name")

                # Для кооперативных операций рассчитываем end_date по coop_duration_days
                # Проверяем coop_company_name т.к. is_cooperation может быть None в БД
                coop_company = item.get("coop_company_name")
                if coop_company:
                    # Гарантируем форматирование planned_date в строку
                    if isinstance(start_date, datetime):
                        item["planned_date"] = start_date.strftime("%d.%m.%Y")

                    # Рассчитываем end_date если есть coop_duration_days
                    coop_days = item.get("coop_duration_days") or 0
                    if coop_days > 0:
                        end_date = start_date
                        days_added = 0
                        while days_added < coop_days:
                            end_date += timedelta(days=1)
                            if end_date.weekday() < 5:  # Пн-Пт
                                days_added += 1
                        item["end_date"] = end_date.strftime("%d.%m.%Y")
                    else:
                        # Если дней кооперации = 0 или нет, показываем дату начала
                        item["planned_date"] = start_date.strftime("%d.%m.%Y")
                        item["end_date"] = start_date.strftime("%d.%m.%Y")
                elif item.get("planned_date") and item.get("duration_minutes"):
                    duration = item["duration_minutes"]
                    prep_time = item.get("prep_time", 0) or 0
                    control_time = item.get("control_time", 0) or 0
                    total_minutes = duration + prep_time + control_time

                    qty = item.get("quantity", 1) or 1
                    total_minutes_for_all = total_minutes * qty

                    working_minutes_per_day = 420
                    days_needed = total_minutes_for_all // working_minutes_per_day
                    remaining_minutes = total_minutes_for_all % working_minutes_per_day

                    if remaining_minutes > 0:
                        days_needed += 1

                    end_date = start_date
                    days_added = 0
                    while days_added < days_needed:
                        end_date += timedelta(days=1)
                        if end_date.weekday() < 5:
                            days_added += 1

                    item["end_date"] = end_date.strftime("%d.%m.%Y")
                    # Форматируем planned_date в строку для корректного сравнения при группировке
                    if isinstance(start_date, datetime):
                        item["planned_date"] = start_date.strftime("%d.%m.%Y")
                else:
                    # Для операций без duration_minutes или без кооперации
                    item["end_date"] = None
                    # Гарантируем формат строки для planned_date
                    if isinstance(planned_date, datetime):
                        item["planned_date"] = planned_date.strftime("%d.%m.%Y")
                    elif isinstance(planned_date, date):
                        item["planned_date"] = planned_date.strftime("%d.%m.%Y")
                    elif isinstance(planned_date, str):
                        # Уже строка - убедимся что формат правильный
                        pass

            # DEBUG: Выводим данные для отладки
            print(
                f"DEBUG plan_page: order_id={order_id}, schedule_items={len(schedule)}"
            )
            for i, item in enumerate(schedule[:5]):
                print(
                    f"  item[{i}]: seq={item.get('sequence_number')}, is_cooperation={item.get('is_cooperation')}, coop_company_name={item.get('coop_company_name')}, coop_duration_days={item.get('coop_duration_days')}, planned_date={item.get('planned_date')}, end_date={item.get('end_date')}"
                )

            # ГРУППИРУЕМ schedule_items по sequence_number (убираем дубликаты операций)
            order_quantity = order.get(
                "quantity", 1
            )  # Общее количество деталей в заказе

            grouped_schedule = {}
            for item in schedule:
                seq = item.get("sequence_number")
                if seq is None:
                    continue

                if seq not in grouped_schedule:
                    grouped_schedule[seq] = {
                        "sequence_number": seq,
                        "operation_name": item.get("operation_name"),
                        "equipment_names": [],
                        "equipment_ids": [],
                        "planned_dates": [],
                        "end_dates": [],
                        "statuses": [],
                        "durations": [],
                        # planned_date и end_date вычисляются после группировки (min/max)
                        "equipment_name": item.get("equipment_name"),
                        "status": item.get("status"),
                        "duration_minutes": item.get("duration_minutes"),
                        "quantity": order_quantity,  # Берём из заказа, не из schedule item!
                        # Поля кооперативной операции
                        "is_cooperation": item.get("is_cooperation"),
                        "coop_company_name": item.get("coop_company_name"),
                        "coop_duration_days": item.get("coop_duration_days"),
                    }
                    # Добавляем даты первого элемента!
                    if item.get("planned_date"):
                        grouped_schedule[seq]["planned_dates"].append(
                            item["planned_date"]
                        )
                    if item.get("end_date"):
                        grouped_schedule[seq]["end_dates"].append(item["end_date"])
                else:
                    # Добавляем уникальные станки
                    eq_name = item.get("equipment_name")
                    if (
                        eq_name
                        and eq_name not in grouped_schedule[seq]["equipment_names"]
                    ):
                        grouped_schedule[seq]["equipment_names"].append(eq_name)
                        # Если первое имя пустое - заполняем
                        if not grouped_schedule[seq]["equipment_name"]:
                            grouped_schedule[seq]["equipment_name"] = eq_name

                    # Собираем даты
                    if item.get("planned_date"):
                        grouped_schedule[seq]["planned_dates"].append(
                            item["planned_date"]
                        )

                    if item.get("end_date"):
                        grouped_schedule[seq]["end_dates"].append(item["end_date"])

                    # Статусы
                    if item.get("status"):
                        grouped_schedule[seq]["statuses"].append(item["status"])

                    # Длительности суммируем (время за все дни)
                    if item.get("duration_minutes"):
                        grouped_schedule[seq]["durations"].append(
                            item["duration_minutes"]
                        )

            # Формируем финальные данные для каждой группы
            final_schedule = []
            for seq, group in grouped_schedule.items():
                # Самая ранняя дата начала (MIN) и самая поздняя дата окончания (MAX)
                if group["planned_dates"]:
                    group["planned_date"] = min(group["planned_dates"])
                    print(
                        f"DEBUG GROUPING: seq={seq}, planned_dates={group['planned_dates']}, min={group['planned_date']}"
                    )

                # Самая поздняя дата окончания (MAX)
                if group["end_dates"]:
                    group["end_date"] = max(group["end_dates"])

                # Статус: если есть delayed → delayed, иначе in_progress → in_progress, иначе completed → completed, иначе planned
                status_priority = ["delayed", "in_progress", "planned", "completed"]
                for status in status_priority:
                    if status in group["statuses"]:
                        group["status"] = status
                        break

                # Суммарное время (если разбито на несколько дней)
                if group["durations"]:
                    group["duration_minutes"] = sum(group["durations"])

                # quantity уже установлен из order_quantity, не меняем!

                # Формируем список всех уникальных станков
                all_equipment = group["equipment_names"]
                if (
                    group["equipment_name"]
                    and group["equipment_name"] not in all_equipment
                ):
                    all_equipment.insert(0, group["equipment_name"])
                group["all_equipment_names"] = all_equipment

                final_schedule.append(group)

            # Сортируем по sequence_number
            final_schedule.sort(key=lambda x: x["sequence_number"] or 0)

            order["schedule_items"] = final_schedule
            order["is_planned"] = len(final_schedule) > 0
            order["is_urgent"] = order.get("priority", 5) == 1

            # Если нет расписания - загружаем операции маршрута
            if not final_schedule and order.get("route_id"):
                route_id = order.get("route_id")
                try:
                    route_ops = db.get_route_operations(route_id)
                    # Преобразуем в формат schedule_items для отображения
                    order["schedule_items"] = []
                    for op in route_ops:
                        order["schedule_items"].append(
                            {
                                "sequence_number": op.get("sequence_number"),
                                "operation_name": op.get("operation_name"),
                                "equipment_name": op.get("equipment_name"),
                                "equipment_id": op.get("equipment_id"),
                                "duration_minutes": op.get("duration_minutes"),
                                "planned_date": None,
                                "end_date": None,
                                "status": "not_planned",
                                "quantity": order.get("quantity", 1),
                            }
                        )
                except Exception as e:
                    logger.warning(
                        f"Could not load route operations for order {order_id}: {e}"
                    )
                    order["schedule_items"] = []
    except Exception as e:
        logger.error(f"Error loading plan page: {e}")
        orders = []

    return templates.TemplateResponse(
        "planning/plan.html",
        {
            "request": request,
            "current_user": user,
            "orders": orders,
            "now": datetime.now(),
            "highlight_order": highlight_order,  # ID заказа для подсветки
        },
    )


@router.get("/calendar", response_class=HTMLResponse)
async def calendar_page(request: Request):
    """Страница календаря производства"""
    user = get_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    db = get_db()
    now = datetime.now()
    year = int(request.query_params.get("year", now.year))
    month = int(request.query_params.get("month", now.month))

    try:
        equipment = db.get_all_equipment(active_only=True)

        # Загружаем сохранённый порядок оборудования
        import json

        user_id = (
            user.get("id") if isinstance(user, dict) else getattr(user, "id", None)
        )
        equipment_order = []
        if user_id:
            config = db.get_calendar_config(user_id)
            if config and config.get("equipment_order"):
                try:
                    equipment_order = (
                        json.loads(config.get("equipment_order", "[]"))
                        if isinstance(config.get("equipment_order"), str)
                        else config.get("equipment_order", [])
                    )
                except:
                    equipment_order = []

        # Сортируем оборудование по сохранённому порядку
        if equipment_order:
            order_map = {eq_id: idx for idx, eq_id in enumerate(equipment_order)}
            equipment.sort(key=lambda eq: order_map.get(eq["id"], len(equipment_order)))

        date_from = datetime(year, month, 1)
        if month == 12:
            date_to = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            date_to = datetime(year, month + 1, 1) - timedelta(days=1)

        schedule = db.get_production_schedule(date_from=date_from, date_to=date_to)

        # Обогащаем расписание номерами заказов
        orders_cache = {}
        for item in schedule:
            order_id = item.get("order_id")
            if order_id and order_id not in orders_cache:
                order = db.get_order(order_id)
                if order:
                    orders_cache[order_id] = {
                        "order_number": order.get("order_number"),
                        "batch_number": order.get("batch_number"),
                        "designation": order.get("designation"),
                        "detail_name": order.get("detail_name"),
                    }
            if order_id and order_id in orders_cache:
                cache = orders_cache[order_id]
                item["order_number"] = cache.get("order_number")
                if not item.get("batch_number"):
                    item["batch_number"] = cache.get("batch_number")
                if not item.get("designation"):
                    item["designation"] = cache.get("designation")
                if not item.get("detail_name"):
                    item["detail_name"] = cache.get("detail_name")

        # Группируем расписание по дням и оборудованию
        schedule_by_day_eq = {}
        for item in schedule:
            date_key = (
                item["planned_date"].strftime("%Y-%m-%d")
                if isinstance(item["planned_date"], datetime)
                else str(item["planned_date"])
            )
            eq_id = item.get("equipment_id")
            key = f"{date_key}_{eq_id}"
            if key not in schedule_by_day_eq:
                schedule_by_day_eq[key] = []
            schedule_by_day_eq[key].append(item)

        # Загружаем календарь
        calendar_data = db.get_all_equipment_calendar(date_from, date_to)
        calendar_by_day_eq = {}
        for entry in calendar_data:
            date_key = (
                entry["date"].strftime("%Y-%m-%d")
                if isinstance(entry["date"], datetime)
                else str(entry["date"])
            )
            eq_id = entry.get("equipment_id")
            calendar_by_day_eq[f"{date_key}_{eq_id}"] = entry

    except Exception as e:
        logger.error(f"Error loading calendar page: {e}")
        equipment, schedule, calendar_data = [], [], []
        schedule_by_day_eq, calendar_by_day_eq = {}, {}

    return templates.TemplateResponse(
        "planning/calendar.html",
        {
            "request": request,
            "current_user": user,
            "equipment": equipment,
            "schedule": schedule,
            "schedule_by_day_eq": schedule_by_day_eq,
            "calendar_by_day_eq": calendar_by_day_eq,
            "visible_equipment": [],  # Показывать всё оборудование
            "now": now,  # Для подсветки сегодняшнего дня
            "year": year,
            "month": month,
            "month_name": [
                "Январь",
                "Февраль",
                "Март",
                "Апрель",
                "Май",
                "Июнь",
                "Июль",
                "Август",
                "Сентябрь",
                "Октябрь",
                "Ноябрь",
                "Декабрь",
            ][month - 1],
            "days_in_month": _get_days_in_month(year, month),
            "first_day_weekday": _get_first_day_weekday(year, month),
        },
    )


@router.get("/gantt", response_class=HTMLResponse)
async def gantt_chart(request: Request):
    """Страница диаграммы Ганта"""
    user = get_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    db = get_db()
    now = datetime.now()
    year = int(request.query_params.get("year", now.year))
    month = int(request.query_params.get("month", now.month))

    try:
        equipment = db.get_all_equipment(active_only=True)
        date_from = datetime(year, month, 1)
        if month == 12:
            date_to = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            date_to = datetime(year, month + 1, 1) - timedelta(days=1)

        schedule = db.get_production_schedule(date_from=date_from, date_to=date_to)

        # Рассчитываем загрузку для каждого станка
        working_days = _count_working_days(year, month)
        total_minutes_available = working_days * 480

        equipment_load = []
        for eq in equipment:
            eq_id = eq.get("id")
            eq_schedule = [s for s in schedule if s.get("equipment_id") == eq_id]
            total_minutes = sum(
                (s.get("duration_minutes", 0) or 0) * (s.get("quantity", 1) or 1)
                for s in eq_schedule
            )
            percent = (
                round((total_minutes / total_minutes_available) * 100, 1)
                if total_minutes_available > 0
                else 0
            )
            equipment_load.append(
                {
                    "equipment": eq,
                    "load_percent": percent,
                    "total_minutes": total_minutes,
                    "operations_count": len(eq_schedule),
                }
            )

        # Статистика
        total_orders = len(
            set(s.get("order_id") for s in schedule if s.get("order_id"))
        )
        in_work = len(
            set(s.get("equipment_id") for s in schedule if s.get("equipment_id"))
        )

    except Exception as e:
        logger.error(f"Error loading gantt page: {e}")
        equipment, schedule, equipment_load = [], [], []
        working_days, total_orders, in_work = 0, 0, 0

    return templates.TemplateResponse(
        "planning/gantt.html",
        {
            "request": request,
            "current_user": user,
            "equipment": equipment,
            "equipment_load": equipment_load,
            "schedule": schedule,
            "year": year,
            "month": month,
            "now": now,
            "month_name": f"{['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'][month - 1]} {year}",
            "days_in_month": _get_days_in_month(year, month),
            "first_day_weekday": _get_first_day_weekday(year, month),
            "working_days": working_days,
            "total_orders": total_orders,
            "in_work": in_work,
        },
    )


@router.get("/settings", response_class=HTMLResponse)
async def planning_settings(request: Request):
    """Страница настроек планирования"""
    user = get_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    # Проверяем права через screen_permissions или роль
    db = get_db()
    user_id = user.get("id")
    has_access = False

    # Сначала проверяем screen_permissions
    if user_id and hasattr(db, "get_user_screen_permissions"):
        screens = db.get_user_screen_permissions(user_id)
        if screens is not None:
            has_access = "planning_settings" in screens
        else:
            # Если permissions не настроены — fallback на роль
            user_role = (
                user.get("role", "")
                if isinstance(user, dict)
                else getattr(user, "role", "")
            )
            has_access = user_role in ("admin", "chief_designer")
    else:
        # Fallback на роль
        user_role = (
            user.get("role", "")
            if isinstance(user, dict)
            else getattr(user, "role", "")
        )
        has_access = user_role in ("admin", "chief_designer")

    if not has_access:
        return HTMLResponse(
            content="""
            <div class="flex items-center justify-center min-h-screen bg-gray-100">
                <div class="bg-white p-8 rounded-lg shadow-lg text-center">
                    <i class="fas fa-lock text-6xl text-red-500 mb-4"></i>
                    <h1 class="text-2xl font-bold text-gray-900 mb-2">Доступ запрещён</h1>
                    <p class="text-gray-600">У вас нет прав для доступа к этой странице.</p>
                    <a href="/dashboard" class="mt-4 inline-block px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
                        Вернуться на главную
                    </a>
                </div>
            </div>
            """,
            status_code=403,
        )

    db = get_db()
    now = datetime.now()
    try:
        equipment = db.get_all_equipment(active_only=False)

        # Текущий месяц для календаря
        calendar_data = db.get_all_equipment_calendar(
            datetime(now.year, now.month, 1),
            datetime(now.year, now.month, _get_days_in_month(now.year, now.month)),
        )

        # Сериализуем даты в строки для Jinja2
        for cal in calendar_data:
            if hasattr(cal.get("date"), "strftime"):
                cal["date"] = cal["date"].strftime("%Y-%m-%d")
    except Exception as e:
        logger.error(f"Error loading settings page: {e}")
        equipment, calendar_data = [], []

    return templates.TemplateResponse(
        "planning/settings.html",
        {
            "request": request,
            "current_user": user,
            "equipment": equipment,
            "calendar_data": calendar_data,
            "now": now,
            "year": now.year,
            "month": now.month,
            "month_name": [
                "Январь",
                "Февраль",
                "Март",
                "Апрель",
                "Май",
                "Июнь",
                "Июль",
                "Август",
                "Сентябрь",
                "Октябрь",
                "Ноябрь",
                "Декабрь",
            ][now.month - 1],
            "days_in_month": _get_days_in_month(now.year, now.month),
            "first_day_weekday": _get_first_day_weekday(now.year, now.month),
        },
    )


# ==================== SCHEDULE CALCULATION API ====================


@router.get("/api/order/{order_id}/coop-operations")
async def get_order_coop_operations(request: Request, order_id: int):
    """Получить кооперативные операции заказа для отображения в диалоге планирования"""
    user = get_user(request)
    if not user:
        return JSONResponse(
            {"success": False, "message": "Не авторизован"}, status_code=401
        )

    db = get_db()
    try:
        order = db.get_order(order_id)
        if not order:
            return JSONResponse(
                {"success": False, "message": "Заказ не найден"}, status_code=404
            )

        route_id = order.get("route_id")
        if not route_id:
            return JSONResponse(
                {"success": False, "message": "У заказа нет маршрута"}, status_code=400
            )

        operations = db.get_route_operations(route_id)

        coop_operations = []
        for op in operations:
            if op.get("is_cooperation"):
                coop_operations.append(
                    {
                        "sequence_number": op.get("sequence_number"),
                        "operation_name": op.get("operation_name"),
                        "coop_company_name": op.get("coop_company_name", ""),
                        "coop_duration_days": op.get("coop_duration_days", 0),
                    }
                )

        return JSONResponse(
            {
                "success": True,
                "coop_operations": coop_operations,
                "has_coop_operations": len(coop_operations) > 0,
            }
        )

    except Exception as e:
        logger.error(f"Error getting coop operations: {e}", exc_info=True)
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@router.post("/api/calculate/{order_id}")
async def calculate_schedule(request: Request, order_id: int):
    """Рассчитать расписание для заказа"""
    user = get_user(request)
    if not user:
        return JSONResponse(
            {"success": False, "message": "Не авторизован"}, status_code=401
        )

    db = get_db()
    try:
        from services.production_planner import ProductionPlanner

        planner = ProductionPlanner(db)

        # Безопасно получаем тело запроса
        body = {}
        try:
            body = await request.json() if request.method == "POST" else {}
        except Exception:
            body = {}

        start_date_str = body.get("start_date")
        priority = body.get("priority", 3)
        equipment_overrides = body.get("equipment_overrides")  # Опционально

        start_date = (
            datetime.strptime(start_date_str, "%Y-%m-%d") if start_date_str else None
        )

        if equipment_overrides:
            logger.info(f"Equipment overrides: {len(equipment_overrides)} operations")

        result = planner.calculate_schedule(
            order_id, start_date, priority, equipment_overrides
        )

        # Обновляем приоритет заказа в БД
        if result.get("success"):
            try:
                logger.info(f"Updating order {order_id} priority to {priority}")
                db.update_order_priority(order_id, priority)
                logger.info(f"Order {order_id} priority updated successfully")
            except Exception as e:
                logger.warning(f"Could not update order priority: {e}")

        # Конвертируем datetime в строки для JSON
        if result.get("schedule"):
            for item in result["schedule"]:
                for key, val in item.items():
                    if isinstance(val, (datetime, date)):
                        item[key] = val.strftime("%d.%m.%Y")

        # Конвертируем start_date и end_date
        if result.get("start_date") and isinstance(
            result["start_date"], (datetime, date)
        ):
            result["start_date"] = result["start_date"].strftime("%d.%m.%Y")
        if result.get("end_date") and isinstance(result["end_date"], (datetime, date)):
            result["end_date"] = result["end_date"].strftime("%d.%m.%Y")

        return JSONResponse(result)
    except Exception as e:
        logger.error(f"Calculate schedule error: {e}", exc_info=True)
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@router.get("/api/order/{order_id}/pdf")
async def generate_order_pdf(request: Request, order_id: int):
    """Генерация PDF для заказа — маршрутная карта с информацией о заказе."""
    from fastapi.responses import FileResponse

    user = get_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    db = get_db()
    try:
        # Получаем заказ
        order = db.get_order(order_id)
        if not order:
            return JSONResponse({"error": "Заказ не найден"}, status_code=404)

        route_id = order.get("route_id")
        if not route_id:
            return JSONResponse({"error": "У заказа нет маршрута"}, status_code=400)

        # Получаем маршрут и операции
        route = db.get_route_by_id(route_id)
        if not route:
            return JSONResponse({"error": "Маршрут не найден"}, status_code=404)

        operations = db.get_route_operations(route_id)

        # Получаем расписание заказа
        schedule = db.get_production_schedule(order_id=order_id)

        # Если есть расписание - формируем операции из него (с фактическими станками)
        if schedule:
            # Группируем расписание по номеру операции
            ops_by_seq = {}
            for item in schedule:
                seq = item.get("sequence_number")
                if seq is not None:
                    if seq not in ops_by_seq:
                        ops_by_seq[seq] = []
                    ops_by_seq[seq].append(item)

            # Формируем операции на основе расписания (берём фактические станки)
            scheduled_operations = []
            seen_seqs = set()

            for item in sorted(schedule, key=lambda x: x.get("sequence_number") or 0):
                seq = item.get("sequence_number")
                if seq is None or seq in seen_seqs:
                    continue
                seen_seqs.add(seq)

                # Находим оригинальную операцию маршрута для получения metadata
                original_op = next(
                    (op for op in operations if op.get("sequence_number") == seq), {}
                )

                scheduled_operations.append(
                    {
                        "sequence_number": seq,
                        "operation_type_id": item.get("operation_type_id")
                        or original_op.get("operation_type_id"),
                        "equipment_id": item.get(
                            "equipment_id"
                        ),  # Фактический станок из расписания!
                        "equipment_name": item.get(
                            "equipment_name"
                        ),  # Фактическое имя станка
                        "operation_name": item.get("operation_name")
                        or original_op.get("operation_name"),
                        "duration_minutes": item.get("duration_minutes")
                        or original_op.get("duration_minutes"),
                        "prep_time": item.get("prep_time")
                        or original_op.get("prep_time", 0),
                        "control_time": item.get("control_time")
                        or original_op.get("control_time", 0),
                        "total_time": item.get("total_time")
                        or original_op.get("total_time", 0),
                        "parts_count": original_op.get("parts_count", 1),
                        "workshop_name": original_op.get("workshop_name", ""),
                        "notes": original_op.get("notes", ""),
                        # Кооперация
                        "is_cooperation": original_op.get("is_cooperation", False),
                        "coop_company_name": original_op.get("coop_company_name", ""),
                        # Сводка по расписанию
                        "schedule_summary": ops_by_seq.get(seq, []),
                    }
                )

            # Если операций из расписания нет - fallback на оригинальные
            if scheduled_operations:
                operations = scheduled_operations

        # Парсим preprocessing_data
        import json

        pre_data = {}
        if route.get("preprocessing_data"):
            try:
                pre_data = json.loads(route["preprocessing_data"])
            except (json.JSONDecodeError, TypeError):
                pre_data = {}

        # Добавляем поля из preprocessing_data
        route["preprocessing"] = pre_data.get("preprocessing", False)
        route["form_type"] = pre_data.get("form_type")
        route["param_l"] = pre_data.get("param_l")
        route["param_w"] = pre_data.get("param_w")
        route["param_s"] = pre_data.get("param_s")
        route["param_d"] = pre_data.get("param_d")
        route["param_d1"] = pre_data.get("param_d1")

        # Формируем габариты
        length_val = route.get("length") or route.get("dimension1")
        width_val = route.get("diameter") or route.get("dimension2")
        if length_val and width_val:
            route["dimensions"] = f"{int(length_val)} × {int(width_val)} мм"
        elif length_val:
            route["dimensions"] = f"{int(length_val)} мм"

        # Добавляем информацию о заказе в маршрут для PDF
        route["order_id"] = order_id
        route["order_number"] = order.get("order_number")
        route["order_quantity"] = order.get("quantity", 1)
        route["order_designation"] = order.get("designation", "")
        route["order_detail_name"] = order.get("detail_name", "")
        route["schedule"] = schedule  # Расписание для отображения в PDF

        # Получаем данные ЭМК для PDF
        route_card_data = order.get("route_card_data")

        # Генерируем PDF
        from services.route_pdf_generator import RoutePDFGenerator

        generator = RoutePDFGenerator()
        pdf_bytes = generator.generate(route, operations, route_card_data)

        # Сохраняем во временный файл
        os.makedirs("/tmp/orders_pdf", exist_ok=True)
        designation = order.get("designation", "unknown")
        detail_name = order.get("detail_name", "")
        filepath = f"/tmp/orders_pdf/order_{order_id}.pdf"
        with open(filepath, "wb") as f:
            f.write(pdf_bytes)

        filename = f"Заказ_{designation}_{detail_name}.pdf".replace(" ", "_")
        return FileResponse(filepath, media_type="application/pdf", filename=filename)

    except Exception as e:
        logger.error(f"Generate order PDF error: {e}", exc_info=True)
        return JSONResponse(
            {"error": f"Failed to generate PDF: {str(e)}"}, status_code=500
        )


@router.post("/api/calculate-all")
async def calculate_all_unplanned(request: Request):
    """Рассчитать расписание для всех незапланированных заказов"""
    user = get_user(request)
    if not user:
        return JSONResponse(
            {"success": False, "message": "Не авторизован"}, status_code=401
        )

    db = get_db()
    try:
        from services.production_planner import ProductionPlanner

        planner = ProductionPlanner(db)

        unplanned = db.get_unplanned_orders()
        results = []
        total_success = 0
        total_failed = 0

        for order in unplanned:
            order_id = order.get("id")
            priority = order.get("priority", 5)
            result = planner.calculate_schedule(order_id, None, priority)
            results.append({"order_id": order_id, "result": result})
            if result.get("success"):
                total_success += 1
            else:
                total_failed += 1

        return JSONResponse(
            {
                "success": True,
                "total": len(unplanned),
                "planned": total_success,
                "failed": total_failed,
                "results": results,
            }
        )
    except Exception as e:
        logger.error(f"Calculate all error: {e}", exc_info=True)
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@router.get("/api/schedule")
async def get_schedule(
    request: Request,
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    equipment_id: Optional[int] = Query(None),
    order_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
):
    """Получить производственное расписание с фильтрами"""
    user = get_user(request)
    if not user:
        return JSONResponse(
            {"success": False, "message": "Не авторизован"}, status_code=401
        )

    db = get_db()
    try:
        df = datetime.strptime(date_from, "%Y-%m-%d") if date_from else None
        dt = datetime.strptime(date_to, "%Y-%m-%d") if date_to else None

        schedule = db.get_production_schedule(
            date_from=df, date_to=dt, equipment_id=equipment_id, order_id=order_id
        )

        # Получаем всё активное оборудование
        all_equipment = db.get_all_equipment(active_only=True)

        # Фильтруем по статусу если указан
        if status:
            schedule = [s for s in schedule if s.get("status") == status]

        # Сериализуем даты и добавляем список всего оборудования
        for item in schedule:
            for key in ["planned_date", "taken_at", "completed_at"]:
                if item.get(key) and isinstance(item[key], datetime):
                    item[key] = item[key].strftime("%Y-%m-%d %H:%M")

            # Добавляем список всего доступного оборудования
            item["available_equipment"] = [
                {"id": eq["id"], "name": eq["name"]} for eq in all_equipment
            ]

        return JSONResponse({"success": True, "schedule": schedule})
    except Exception as e:
        logger.error(f"Get schedule error: {e}", exc_info=True)
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@router.get("/api/equipment-by-operation/{operation_type_id}")
async def get_equipment_by_operation_type(request: Request, operation_type_id: int):
    """Получить оборудование для конкретного типа операции"""
    user = get_user(request)
    if not user:
        return JSONResponse(
            {"success": False, "message": "Не авторизован"}, status_code=401
        )

    db = get_db()
    try:
        from sqlalchemy import text

        with db.get_session() as session:
            equipment = session.execute(
                text("""
                    SELECT e.id, e.name, e.inventory_number
                    FROM equipment e
                    JOIN operation_equipment oe ON oe.equipment_id = e.id
                    WHERE oe.operation_type_id = :operation_type_id
                      AND e.is_active = true
                    ORDER BY e.name
                """),
                {"operation_type_id": operation_type_id},
            ).fetchall()

            return JSONResponse(
                {
                    "success": True,
                    "equipment": [
                        {"id": row[0], "name": row[1], "inventory_number": row[2]}
                        for row in equipment
                    ],
                }
            )
    except Exception as e:
        logger.error(f"Get equipment by operation error: {e}", exc_info=True)
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@router.post("/api/check-conflicts")
async def check_schedule_conflicts(request: Request):
    """Проверить конфликты расписания и предложить альтернативные станки + рассчитать вместимость"""
    user = get_user(request)
    if not user:
        return JSONResponse(
            {"success": False, "message": "Не авторизован"}, status_code=401
        )

    db = get_db()
    try:
        body = await request.json()
        start_date_str = body.get("start_date")
        order_id = body.get("order_id")
        equipment_id = body.get("equipment_id")  # Опционально - для конкретного станка
        operation_type_id = body.get("operation_type_id")
        duration_minutes = body.get("duration_minutes", 0)
        quantity = body.get("quantity", 1)

        if not start_date_str or not order_id:
            return JSONResponse(
                {"success": False, "message": "start_date и order_id обязательны"},
                status_code=400,
            )

        from sqlalchemy import text
        from datetime import datetime, timedelta
        import math

        WORKING_MINUTES_PER_DAY = 420  # 7 часов
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")

        with db.get_session() as session:
            # Если equipment_id не указан - проверяем все станки маршрута
            if not equipment_id:
                # Получаем все операции маршрута и их станки
                route_ops = session.execute(
                    text("""
                        SELECT DISTINCT ro.equipment_id
                        FROM orders o
                        JOIN detail_routes dr ON o.route_id = dr.id
                        JOIN route_operations ro ON dr.id = ro.route_id
                        WHERE o.id = :order_id AND ro.equipment_id IS NOT NULL
                    """),
                    {"order_id": order_id},
                ).fetchall()

                # Проверяем каждый станок
                all_conflicts = []
                all_alternatives = []

                for (eq_id,) in route_ops:
                    busy_ops = session.execute(
                        text("""
                            SELECT ps.id, ps.order_id, ps.duration_minutes, ps.quantity,
                                   dr.designation, dr.detail_name, e.name as equipment_name
                            FROM production_schedule ps
                            JOIN orders o ON ps.order_id = o.id
                            LEFT JOIN detail_routes dr ON o.route_id = dr.id
                            LEFT JOIN equipment e ON ps.equipment_id = e.id
                            WHERE ps.equipment_id = :equipment_id
                              AND ps.planned_date = :start_date
                              AND ps.order_id != :order_id
                        """),
                        {
                            "equipment_id": eq_id,
                            "start_date": start_date,
                            "order_id": order_id,
                        },
                    ).fetchall()

                    for op in busy_ops:
                        (
                            op_id,
                            op_order_id,
                            op_duration,
                            op_qty,
                            desg,
                            detail,
                            eq_name,
                        ) = op
                        all_conflicts.append(
                            {
                                "schedule_id": op_id,
                                "order_id": op_order_id,
                                "equipment_id": eq_id,
                                "designation": desg or "",
                                "detail_name": detail or "",
                                "equipment_name": eq_name or "",
                                "duration_minutes": op_duration or 0,
                            }
                        )

                # Получаем альтернативные станки
                if operation_type_id:
                    alt_eq = session.execute(
                        text("""
                            SELECT e.id, e.name, e.inventory_number
                            FROM equipment e
                            JOIN operation_equipment oe ON oe.equipment_id = e.id
                            WHERE oe.operation_type_id = :operation_type_id
                              AND e.is_active = true
                            ORDER BY e.name
                        """),
                        {"operation_type_id": operation_type_id},
                    ).fetchall()

                    all_alternatives = [
                        {"id": row[0], "name": row[1], "inventory_number": row[2]}
                        for row in alt_eq
                    ]

                return JSONResponse(
                    {
                        "success": True,
                        "has_conflict": len(all_conflicts) > 0,
                        "conflicts": all_conflicts,
                        "alternative_equipment": all_alternatives,
                    }
                )
            else:
                # Проверяем конкретный станок
                busy_ops = session.execute(
                    text("""
                        SELECT ps.id, ps.order_id, ps.duration_minutes, ps.quantity,
                               dr.designation, dr.detail_name, e.name as equipment_name
                        FROM production_schedule ps
                        JOIN orders o ON ps.order_id = o.id
                        LEFT JOIN detail_routes dr ON o.route_id = dr.id
                        LEFT JOIN equipment e ON ps.equipment_id = e.id
                        WHERE ps.equipment_id = :equipment_id
                          AND ps.planned_date = :start_date
                          AND ps.order_id != :order_id
                    """),
                    {
                        "equipment_id": equipment_id,
                        "start_date": start_date,
                        "order_id": order_id,
                    },
                ).fetchall()

                total_busy_minutes = 0
                conflicts = []

                for op in busy_ops:
                    op_id, op_order_id, op_duration, op_qty, desg, detail, eq_name = op
                    op_duration = op_duration or 0
                    total_busy_minutes += op_duration

                    conflicts.append(
                        {
                            "schedule_id": op_id,
                            "order_id": op_order_id,
                            "equipment_id": equipment_id,
                            "designation": desg or "",
                            "detail_name": detail or "",
                            "equipment_name": eq_name or "",
                            "duration_minutes": op_duration,
                        }
                    )

                free_minutes = WORKING_MINUTES_PER_DAY - total_busy_minutes

                if duration_minutes > 0:
                    parts_can_fit = max(0, math.floor(free_minutes / duration_minutes))
                else:
                    parts_can_fit = quantity

                has_partial_fit = parts_can_fit > 0 and parts_can_fit < quantity
                is_completely_busy = free_minutes <= 0

                alternative_equipment = []
                if operation_type_id:
                    alt_eq = session.execute(
                        text("""
                            SELECT e.id, e.name, e.inventory_number
                            FROM equipment e
                            JOIN operation_equipment oe ON oe.equipment_id = e.id
                            WHERE oe.operation_type_id = :operation_type_id
                              AND e.is_active = true
                              AND e.id != :equipment_id
                            ORDER BY e.name
                        """),
                        {
                            "operation_type_id": operation_type_id,
                            "equipment_id": equipment_id,
                        },
                    ).fetchall()

                    alternative_equipment = [
                        {"id": row[0], "name": row[1], "inventory_number": row[2]}
                        for row in alt_eq
                    ]

                return JSONResponse(
                    {
                        "success": True,
                        "has_conflict": len(conflicts) > 0,
                        "is_completely_busy": is_completely_busy,
                        "has_partial_fit": has_partial_fit,
                        "total_busy_minutes": total_busy_minutes,
                        "free_minutes": max(0, free_minutes),
                        "parts_can_fit": parts_can_fit,
                        "quantity_needed": quantity,
                        "conflicts": conflicts,
                        "alternative_equipment": alternative_equipment,
                    }
                )
    except Exception as e:
        logger.error(f"Check conflicts error: {e}", exc_info=True)
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@router.post("/api/check-order-conflicts/{order_id}")
async def check_order_conflicts(request: Request, order_id: int):
    """
    Проверить конфликты ВСЕХ операций маршрута заказа на указанную дату начала.
    Возвращает список всех пересечений с уже запланированными заказами.
    """
    user = get_user(request)
    if not user:
        return JSONResponse(
            {"success": False, "message": "Не авторизован"}, status_code=401
        )

    db = get_db()
    try:
        body = await request.json()
        start_date_str = body.get("start_date")
        priority = body.get("priority", 5)

        if not start_date_str:
            return JSONResponse(
                {"success": False, "message": "start_date обязателен"}, status_code=400
            )

        from sqlalchemy import text
        from datetime import datetime, timedelta
        import math

        WORKING_MINUTES_PER_DAY = 420
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")

        with db.get_session() as session:
            # Получаем заказ и его маршрут
            order = session.execute(
                text("SELECT id, route_id, quantity FROM orders WHERE id = :order_id"),
                {"order_id": order_id},
            ).fetchone()

            if not order:
                return JSONResponse(
                    {"success": False, "message": "Заказ не найден"}, status_code=404
                )

            order_qty = order[2] or 1
            route_id = order[1]

            if not route_id:
                return JSONResponse(
                    {"success": False, "message": "У заказа нет маршрута"},
                    status_code=400,
                )

            # Загружаем все операции маршрута
            route_ops = session.execute(
                text("""
                    SELECT
                        ro.id, ro.sequence_number, ro.duration_minutes, ro.total_time,
                        ro.equipment_id, ot.name as operation_name, ot.id as operation_type_id,
                        e.name as equipment_name
                    FROM route_operations ro
                    LEFT JOIN operation_types ot ON ro.operation_type_id = ot.id
                    LEFT JOIN equipment e ON ro.equipment_id = e.id
                    WHERE ro.route_id = :route_id
                    ORDER BY ro.sequence_number
                """),
                {"route_id": route_id},
            ).fetchall()

            if not route_ops:
                return JSONResponse(
                    {
                        "success": True,
                        "has_conflicts": False,
                        "conflicts": [],
                        "message": "Нет операций в маршруте",
                    }
                )

            # Проверяем каждую операцию на конфликты
            all_conflicts = []
            current_date = start_date

            for op in route_ops:
                (
                    op_id,
                    seq_num,
                    duration,
                    total_time,
                    eq_id,
                    op_name,
                    op_type_id,
                    eq_name,
                ) = op
                duration = duration or 60
                total_time = total_time or duration
                eq_id = eq_id  # Может быть None

                if not eq_id:
                    continue

                # Рассчитываем сколько дней нужно для этой операции
                total_minutes_needed = total_time * order_qty
                days_needed = math.ceil(total_minutes_needed / WORKING_MINUTES_PER_DAY)
                days_needed = max(1, days_needed)

                # Проверяем каждый день операции на конфликты
                check_date = current_date
                for day_idx in range(days_needed):
                    # Пропускаем выходные
                    while check_date.weekday() >= 5:
                        check_date += timedelta(days=1)

                    # Ищем занятые операции на этот день на этом станке
                    busy_ops = session.execute(
                        text("""
                            SELECT ps.id, ps.order_id, ps.quantity, ps.duration_minutes,
                                   dr.designation, dr.detail_name, e.name as equipment_name,
                                   ps.priority as order_priority
                            FROM production_schedule ps
                            JOIN orders o ON ps.order_id = o.id
                            LEFT JOIN detail_routes dr ON o.route_id = dr.id
                            LEFT JOIN equipment e ON ps.equipment_id = e.id
                            WHERE ps.equipment_id = :equipment_id
                              AND ps.planned_date = :check_date
                              AND ps.order_id != :order_id
                        """),
                        {
                            "equipment_id": eq_id,
                            "check_date": check_date.date(),
                            "order_id": order_id,
                        },
                    ).fetchall()

                    if busy_ops:
                        for busy in busy_ops:
                            (
                                busy_id,
                                busy_order_id,
                                busy_qty,
                                busy_dur,
                                desg,
                                detail,
                                busy_eq,
                                busy_prio,
                            ) = busy
                            all_conflicts.append(
                                {
                                    "operation_sequence": seq_num,
                                    "operation_name": op_name or "",
                                    "operation_type_id": op_type_id,
                                    "conflict_date": check_date.strftime("%Y-%m-%d"),
                                    "equipment_id": eq_id,
                                    "equipment_name": eq_name or "",
                                    "busy_order_id": busy_order_id,
                                    "busy_order_designation": desg or "",
                                    "busy_order_detail": detail or "",
                                    "busy_order_priority": busy_prio or 5,
                                    "busy_equipment_name": busy_eq or "",
                                    "busy_duration_minutes": busy_dur or 0,
                                    "our_duration_minutes": duration,
                                    "message": f"Операция {seq_num} ({op_name}) на {eq_name} конфликтует с заказом #{busy_order_id} на {check_date.strftime('%d.%m.%Y')}",
                                }
                            )

                    check_date += timedelta(days=1)

                # Переходим к следующей операции (следующий рабочий день после завершения текущей)
                current_date = check_date
                while current_date.weekday() >= 5:
                    current_date += timedelta(days=1)

            # Для каждого конфликта находим альтернативные станки
            alternative_equipment_map = {}
            for conflict in all_conflicts:
                op_type_id = conflict.get("operation_type_id")
                op_name = conflict.get("operation_name", "").lower()
                current_eq_id = conflict["equipment_id"]

                alt_equipment = []

                # Способ 1: Ищем по operation_type_id
                if op_type_id:
                    alt_eq = session.execute(
                        text("""
                            SELECT e.id, e.name, e.inventory_number
                            FROM equipment e
                            JOIN operation_equipment oe ON oe.equipment_id = e.id
                            WHERE oe.operation_type_id = :operation_type_id
                              AND e.is_active = true
                              AND e.id != :current_eq_id
                            ORDER BY e.name
                        """),
                        {
                            "operation_type_id": op_type_id,
                            "current_eq_id": current_eq_id,
                        },
                    ).fetchall()
                    alt_equipment = [
                        {"id": row[0], "name": row[1], "inventory_number": row[2]}
                        for row in alt_eq
                    ]

                # Способ 2: Если не нашли - ищем по ключевым словам в названии операции
                if not alt_equipment:
                    keywords = []
                    if "токар" in op_name:
                        keywords.append("токарн")
                    elif "фрезер" in op_name:
                        keywords.append("фрезерн")
                    elif "шлиф" in op_name:
                        keywords.append("шлифов")
                    elif "сверл" in op_name or "расточ" in op_name:
                        keywords.append("сверл")

                    if keywords:
                        like_conditions = " OR ".join(
                            [f"LOWER(e.name) LIKE '%{kw}%'" for kw in keywords]
                        )
                        alt_eq = session.execute(
                            text(f"""
                                SELECT e.id, e.name, e.inventory_number
                                FROM equipment e
                                WHERE e.is_active = true
                                  AND e.id != :current_eq_id
                                  AND ({like_conditions})
                                ORDER BY e.name
                            """),
                            {"current_eq_id": current_eq_id},
                        ).fetchall()
                        alt_equipment = [
                            {"id": row[0], "name": row[1], "inventory_number": row[2]}
                            for row in alt_eq
                        ]

                conflict["alternative_equipment"] = alt_equipment

            has_conflicts = len(all_conflicts) > 0

            return JSONResponse(
                {
                    "success": True,
                    "has_conflicts": has_conflicts,
                    "conflicts_count": len(all_conflicts),
                    "conflicts": all_conflicts,
                    "message": f"Найдено {len(all_conflicts)} конфликтов"
                    if has_conflicts
                    else "Конфликтов не найдено",
                }
            )

    except Exception as e:
        logger.error(f"Check order conflicts error: {e}", exc_info=True)
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@router.put("/api/schedule/{schedule_id}")
async def update_schedule_item(request: Request, schedule_id: int):
    """Обновить операцию с пересчётом дат (7ч день) и автосдвигом всех последующих"""
    user = get_user(request)
    if not user:
        return JSONResponse(
            {"success": False, "message": "Не авторизован"}, status_code=401
        )

    db = get_db()
    try:
        body = await request.json()
        logger.info(f"Update schedule {schedule_id}: {body}")

        from sqlalchemy import text
        from datetime import timedelta
        import math

        WORKING_MINUTES_PER_DAY = 420  # 7 часов

        def add_working_days(start_date: datetime, days_to_add: int) -> datetime:
            """Добавить рабочие дни, пропуская выходные"""
            current = start_date
            added = 0
            while added < days_to_add:
                current += timedelta(days=1)
                if current.weekday() < 5:  # 0=Пн ... 4=Пт
                    added += 1
            return current

        def get_next_working_day(date: datetime) -> datetime:
            """Вернуть следующий рабочий день"""
            current = date
            while True:
                current += timedelta(days=1)
                if current.weekday() < 5:
                    return current

        new_date_str = body.get("planned_date")
        new_equipment_id = body.get("equipment_id")

        if not new_date_str:
            return JSONResponse(
                {"success": False, "message": "Дата обязательна"}, status_code=400
            )

        recalc_start = datetime.strptime(new_date_str, "%Y-%m-%d")

        # Всё в одной транзакции
        with db.get_session() as session:
            # Получаем order_id
            order_info = session.execute(
                text("SELECT order_id FROM production_schedule WHERE id = :id"),
                {"id": schedule_id},
            ).fetchone()

            if not order_info:
                return JSONResponse(
                    {"success": False, "message": "Операция не найдена"},
                    status_code=404,
                )

            order_id = order_info[0]

            # Находим все операции заказа, отсортированные по порядку
            all_ops = session.execute(
                text("""
                    SELECT ps.id, ps.planned_date, ps.equipment_id, ps.duration_minutes, ro.sequence_number
                    FROM production_schedule ps
                    LEFT JOIN route_operations ro ON ps.route_operation_id = ro.id
                    WHERE ps.order_id = :order_id
                    ORDER BY ro.sequence_number, ps.planned_date
                """),
                {"order_id": order_id},
            ).fetchall()

            if not all_ops:
                return JSONResponse(
                    {"success": False, "message": "Операции не найдены"},
                    status_code=404,
                )

            # Находим индекс и route_operation_id изменённой операции
            changed_op_route_id = None
            changed_idx = -1
            for i, op in enumerate(all_ops):
                if op[0] == schedule_id:
                    changed_idx = i
                    break

            # Получаем route_operation_id изменённой операции
            current = session.execute(
                text(
                    "SELECT route_operation_id FROM production_schedule WHERE id = :id"
                ),
                {"id": schedule_id},
            ).fetchone()

            if current and current[0]:
                changed_op_route_id = current[0]

            if changed_idx == -1:
                return JSONResponse(
                    {"success": False, "message": "Операция не найдена в заказе"},
                    status_code=404,
                )

            def is_day_busy(start_date, eq_id, excl_order_id):
                """Проверить занят ли конкретный день для станка"""
                busy = session.execute(
                    text("""
                        SELECT COUNT(*) FROM production_schedule
                        WHERE equipment_id = :eq_id 
                          AND planned_date = :date
                          AND order_id != :order_id
                    """),
                    {"eq_id": eq_id, "date": start_date, "order_id": excl_order_id},
                ).fetchone()[0]
                return busy > 0

            def find_next_free_day(start_date, eq_id, excl_order_id):
                """Найти ближайший свободный рабочий день для станка"""
                current = start_date
                attempts = 0
                for _ in range(365):
                    attempts += 1
                    if current.weekday() < 5:  # Только рабочие дни
                        busy = is_day_busy(current, eq_id, excl_order_id)
                        logger.info(
                            f"  Checking {current.strftime('%d.%m.%Y')} eq={eq_id}: busy={busy}"
                        )
                        if not busy:
                            logger.info(
                                f"  -> Found free day: {current.strftime('%d.%m.%Y')} after {attempts} attempts"
                            )
                            return current
                    current += timedelta(days=1)
                logger.warning(
                    f"  -> No free day found after {attempts} attempts, returning original: {start_date.strftime('%d.%m.%Y')}"
                )
                return start_date

            def find_consecutive_free_days(
                start_date, eq_id, excl_order_id, days_needed
            ):
                """Найти последовательные свободные дни"""
                current = start_date
                max_attempts = 365

                for attempt in range(max_attempts):
                    if current.weekday() >= 5:
                        current += timedelta(days=1)
                        continue

                    # Проверяем занятость текущего дня
                    if is_day_busy(current, eq_id, excl_order_id):
                        current += timedelta(days=1)
                        continue

                    # Нашли первый свободный день - проверяем остальные
                    free_days = [current]
                    check_date = current + timedelta(days=1)

                    while len(free_days) < days_needed:
                        if check_date.weekday() >= 5:
                            check_date += timedelta(days=1)
                            continue

                        if is_day_busy(check_date, eq_id, excl_order_id):
                            break  # День занят - начинаем сначала

                        free_days.append(check_date)
                        check_date += timedelta(days=1)

                    if len(free_days) == days_needed:
                        logger.info(
                            f"  -> Found {days_needed} consecutive free days starting: {free_days[0].strftime('%d.%m.%Y')}"
                        )
                        return free_days[0]

                    # Не хватило дней - двигаемся дальше
                    current += timedelta(days=1)

                logger.warning(
                    f"  -> No {days_needed} consecutive free days found, returning original: {start_date.strftime('%d.%m.%Y')}"
                )
                return start_date

            # Определяем целевой станок для каждой операции
            ops_to_update = []
            prev_end_date = None

            for i, op in enumerate(all_ops):
                op_id, op_date, op_eq, op_duration, op_seq = op
                op_duration = op_duration or 0

                # Проверяем, относится ли эта запись к той же операции маршрута
                op_route_id = session.execute(
                    text(
                        "SELECT route_operation_id FROM production_schedule WHERE id = :id"
                    ),
                    {"id": op_id},
                ).fetchone()
                op_route_id = op_route_id[0] if op_route_id else None

                # Операции ДО изменённой - не трогаем
                if i < changed_idx:
                    continue

                # Определяем станок: если это та же операция маршрута - используем новый станок
                if changed_op_route_id and op_route_id == changed_op_route_id:
                    current_eq = new_equipment_id if new_equipment_id else op_eq
                else:
                    current_eq = op_eq  # Сохраняем оригинальный станок

                # Определяем дату начала
                if i == changed_idx:
                    start_dt = recalc_start
                    logger.info(
                        f"Op {op_id}: Using requested start date {start_dt.strftime('%d.%m.%Y')}"
                    )
                else:
                    start_dt = get_next_working_day(prev_end_date)
                    logger.info(
                        f"Op {op_id}: Using next working day after {prev_end_date.strftime('%d.%m.%Y')} -> {start_dt.strftime('%d.%m.%Y')}"
                    )

                # Проверяем занятость станка и находим свободный день
                logger.info(
                    f"Op {op_id}: Checking availability for eq={current_eq} on {start_dt.strftime('%d.%m.%Y')}"
                )
                start_dt = find_next_free_day(start_dt, current_eq, order_id)
                logger.info(
                    f"Op {op_id}: Final start date: {start_dt.strftime('%d.%m.%Y')}"
                )

                # Считаем сколько дней займёт операция (7ч = 420 мин)
                days_needed = (
                    max(1, math.ceil(op_duration / WORKING_MINUTES_PER_DAY))
                    if op_duration > 0
                    else 1
                )

                # Находим последовательные свободные дни для операции
                if days_needed > 1:
                    logger.info(f"Op {op_id}: Need {days_needed} consecutive days")
                    start_dt = find_consecutive_free_days(
                        start_dt, current_eq, order_id, days_needed
                    )
                    end_dt = add_working_days(start_dt, days_needed - 1)
                else:
                    end_dt = start_dt

                ops_to_update.append(
                    {
                        "id": op_id,
                        "start_date": start_dt,
                        "end_date": end_dt,
                        "equipment_id": current_eq,
                    }
                )

                prev_end_date = end_dt
                logger.info(
                    f"Op {op_id} (seq {op_seq}, route_op={op_route_id}): {start_dt.strftime('%d.%m')} → {end_dt.strftime('%d.%m')} ({days_needed}д, {op_duration}мин) eq:{current_eq}"
                )

            # Применяем обновления
            for upd in ops_to_update:
                session.execute(
                    text("""
                        UPDATE production_schedule
                        SET planned_date = :start_date,
                            equipment_id = :equipment_id,
                            is_manual_override = true,
                            updated_at = NOW()
                        WHERE id = :id
                    """),
                    upd,
                )

            session.commit()
            logger.info(f"Successfully recalculated {len(ops_to_update)} operations")
            logger.info(f"Updated operations: {ops_to_update}")

        return JSONResponse({"success": True})
    except Exception as e:
        logger.error(f"Update schedule error: {e}", exc_info=True)
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@router.delete("/api/schedule/{schedule_id}")
async def delete_schedule_item(request: Request, schedule_id: int):
    """Удалить элемент расписания"""
    user = get_user(request)
    if not user:
        return JSONResponse(
            {"success": False, "message": "Не авторизован"}, status_code=401
        )

    db = get_db()
    try:
        result = db.delete_schedule_item(schedule_id)
        return JSONResponse({"success": result})
    except Exception as e:
        logger.error(f"Delete schedule error: {e}", exc_info=True)
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@router.post("/api/schedule/{schedule_id}/take")
async def take_schedule_item(request: Request, schedule_id: int):
    """Отметить операцию как взятую в работу"""
    user = get_user(request)
    if not user:
        return JSONResponse(
            {"success": False, "message": "Не авторизован"}, status_code=401
        )

    db = get_db()
    try:
        result = db.mark_schedule_taken(
            schedule_id, user=getattr(user, "username", "web_user")
        )
        return JSONResponse({"success": result})
    except Exception as e:
        logger.error(f"Take schedule error: {e}", exc_info=True)
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@router.post("/api/schedule/{schedule_id}/complete")
async def complete_schedule_item(request: Request, schedule_id: int):
    """Отметить операцию как завершённую"""
    user = get_user(request)
    if not user:
        return JSONResponse(
            {"success": False, "message": "Не авторизован"}, status_code=401
        )

    db = get_db()
    try:
        result = db.mark_schedule_completed(
            schedule_id, user=getattr(user, "username", "web_user")
        )
        return JSONResponse({"success": result})
    except Exception as e:
        logger.error(f"Complete schedule error: {e}", exc_info=True)
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


# ==================== MANUAL SCHEDULE API ====================


@router.post("/api/manual-schedule")
async def create_manual_schedule(request: Request):
    """Создать ручную запись в расписании (без маршрута) с автораспределением по дням"""
    user = get_user(request)
    if not user:
        return JSONResponse(
            {"success": False, "message": "Не авторизован"}, status_code=401
        )

    db = get_db()
    try:
        # Проверяем разрешено ли ручное добавление
        allow_manual = db.get_planning_setting("allow_manual_entry", "true")
        if allow_manual != "true":
            return JSONResponse(
                {
                    "success": False,
                    "message": "Ручное добавление отключено администратором",
                },
                status_code=403,
            )

        body = await request.json()
        detail_name = body.get("detail_name", "").strip()
        quantity = int(body.get("quantity", 1))
        equipment_id = int(body.get("equipment_id"))
        planned_date = body.get("planned_date")
        duration_minutes = int(body.get("duration_minutes", 60))
        priority = int(body.get("priority", 5))
        notes = body.get("notes", "")

        if not detail_name:
            return JSONResponse(
                {"success": False, "message": "Укажите название детали"},
                status_code=400,
            )
        if quantity < 1:
            return JSONResponse(
                {"success": False, "message": "Количество должно быть > 0"},
                status_code=400,
            )

        from datetime import datetime

        date_obj = (
            datetime.strptime(planned_date, "%Y-%m-%d")
            if planned_date
            else datetime.now()
        )

        # Проверяем total_time = duration × quantity
        total_time = duration_minutes * quantity
        workday_limit = 420  # 7 часов

        result = db.create_manual_order_with_schedule(
            detail_name=detail_name,
            quantity=quantity,
            equipment_id=equipment_id,
            planned_date=date_obj,
            duration_minutes=duration_minutes,
            priority=priority,
            notes=notes,
            workday_limit=workday_limit,
        )

        if result.get("success"):
            schedule_count = result.get("schedule_count", 1)
            message = f"Деталь добавлена в план"
            if schedule_count > 1:
                message = f"Деталь добавлена в план ({schedule_count} дн.)"

            return JSONResponse(
                {
                    "success": True,
                    "order_id": result["order_id"],
                    "schedule_id": result["schedule_id"],
                    "schedule_count": schedule_count,
                    "message": message,
                    "total_time": total_time,
                    "workday_limit": workday_limit,
                }
            )
        else:
            return JSONResponse(
                {"success": False, "message": result.get("message")}, status_code=500
            )

    except Exception as e:
        logger.error(f"Manual schedule error: {e}", exc_info=True)
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@router.get("/api/settings/manual-entry")
async def get_manual_entry_setting(request: Request):
    """Получить настройку ручного добавления"""
    user = get_user(request)
    if not user:
        return JSONResponse(
            {"success": False, "message": "Не авторизован"}, status_code=401
        )

    db = get_db()
    value = db.get_planning_setting("allow_manual_entry", "true")
    return JSONResponse({"success": True, "allow_manual_entry": value == "true"})


@router.put("/api/settings/manual-entry")
async def set_manual_entry_setting(request: Request):
    """Установить настройку ручного добавления (только admin)"""
    user = get_user(request)
    if not user or user.get("role") != "admin":
        return JSONResponse(
            {"success": False, "message": "Только для администратора"}, status_code=403
        )

    body = await request.json()
    value = body.get("allow_manual_entry", True)

    db = get_db()
    db.set_planning_setting("allow_manual_entry", "true" if value else "false")
    return JSONResponse({"success": True, "allow_manual_entry": value})


# ==================== EQUIPMENT CALENDAR API ====================


@router.get("/api/equipment-calendar")
async def get_equipment_calendar(
    request: Request,
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
):
    """Получить календарь всего оборудования"""
    user = get_user(request)
    if not user:
        return JSONResponse(
            {"success": False, "message": "Не авторизован"}, status_code=401
        )

    db = get_db()
    try:
        now = datetime.now()
        df = (
            datetime.strptime(date_from, "%Y-%m-%d")
            if date_from
            else datetime(now.year, now.month, 1)
        )
        if df.month == 12:
            dt = datetime(df.year + 1, 1, 1) - timedelta(days=1)
        else:
            dt = datetime(df.year, df.month + 1, 1) - timedelta(days=1)
        if date_to:
            dt = datetime.strptime(date_to, "%Y-%m-%d")

        calendar_data = db.get_all_equipment_calendar(df, dt)
        equipment = db.get_all_equipment(active_only=True)

        # Сериализуем даты
        for entry in calendar_data:
            if isinstance(entry.get("date"), datetime):
                entry["date"] = entry["date"].strftime("%Y-%m-%d")

        return JSONResponse(
            {"success": True, "calendar": calendar_data, "equipment": equipment}
        )
    except Exception as e:
        logger.error(f"Get equipment calendar error: {e}", exc_info=True)
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@router.get("/api/equipment-calendar/{equipment_id}")
async def get_equipment_calendar_for(
    request: Request,
    equipment_id: int,
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
):
    """Получить календарь конкретного оборудования"""
    user = get_user(request)
    if not user:
        return JSONResponse(
            {"success": False, "message": "Не авторизован"}, status_code=401
        )

    db = get_db()
    try:
        now = datetime.now()
        df = (
            datetime.strptime(date_from, "%Y-%m-%d")
            if date_from
            else datetime(now.year, now.month, 1)
        )
        if df.month == 12:
            dt = datetime(df.year + 1, 1, 1) - timedelta(days=1)
        else:
            dt = datetime(df.year, df.month + 1, 1) - timedelta(days=1)
        if date_to:
            dt = datetime.strptime(date_to, "%Y-%m-%d")

        calendar_data = db.get_equipment_calendar(equipment_id, df, dt)

        for entry in calendar_data:
            if isinstance(entry.get("date"), datetime):
                entry["date"] = entry["date"].strftime("%Y-%m-%d")

        return JSONResponse({"success": True, "calendar": calendar_data})
    except Exception as e:
        logger.error(f"Get equipment calendar error: {e}", exc_info=True)
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@router.post("/api/equipment-calendar/{equipment_id}/day")
async def set_equipment_day(request: Request, equipment_id: int):
    """Установить рабочий/нерабочий день для станка"""
    user = get_user(request)
    if not user:
        return JSONResponse(
            {"success": False, "message": "Не авторизован"}, status_code=401
        )

    db = get_db()
    try:
        body = await request.json()
        date = datetime.strptime(body["date"], "%Y-%m-%d")
        is_working = body.get("is_working", True)
        working_hours = body.get("working_hours", 8)

        result = db.set_equipment_calendar_day(
            equipment_id, date, is_working, working_hours
        )
        return JSONResponse({"success": result})
    except Exception as e:
        logger.error(f"Set equipment day error: {e}", exc_info=True)
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@router.put("/api/equipment/{equipment_id}/settings")
async def update_equipment_settings_api(request: Request, equipment_id: int):
    """Обновить настройки оборудования (активность, рабочие часы)"""
    user = get_user(request)
    if not user:
        return JSONResponse(
            {"success": False, "message": "Не авторизован"}, status_code=401
        )

    # Проверяем права (admin или chief_designer)
    user_role = (
        user.get("role", "") if isinstance(user, dict) else getattr(user, "role", "")
    )
    if user_role not in ("admin", "chief_designer"):
        return JSONResponse({"success": False, "message": "Нет прав"}, status_code=403)

    db = get_db()
    try:
        body = await request.json()
        is_active = body.get("is_active")
        default_working_hours = body.get("default_working_hours")

        result = db.update_equipment_settings(
            equipment_id,
            is_active=is_active,
            default_working_hours=default_working_hours,
        )

        if result:
            return JSONResponse({"success": True, "message": "Настройки сохранены"})
        else:
            return JSONResponse(
                {"success": False, "message": "Ошибка обновления"}, status_code=500
            )
    except Exception as e:
        logger.error(f"Update equipment settings API error: {e}", exc_info=True)
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@router.post("/api/equipment/bulk-update-settings")
async def bulk_update_equipment_settings(request: Request):
    """Массовое обновление настроек оборудования"""
    user = get_user(request)
    if not user:
        return JSONResponse(
            {"success": False, "message": "Не авторизован"}, status_code=401
        )

    # Проверяем права (admin или chief_designer)
    user_role = (
        user.get("role", "") if isinstance(user, dict) else getattr(user, "role", "")
    )
    if user_role not in ("admin", "chief_designer"):
        return JSONResponse({"success": False, "message": "Нет прав"}, status_code=403)

    db = get_db()
    try:
        body = await request.json()
        updates = body.get("updates", [])

        success_count = 0
        failed_count = 0

        for update in updates:
            eq_id = update.get("equipment_id")
            if not eq_id:
                failed_count += 1
                continue

            is_active = update.get("is_active")
            default_working_hours = update.get("default_working_hours")

            result = db.update_equipment_settings(
                eq_id, is_active=is_active, default_working_hours=default_working_hours
            )

            if result:
                success_count += 1
            else:
                failed_count += 1

        return JSONResponse(
            {
                "success": True,
                "message": f"Обновлено: {success_count}, Ошибок: {failed_count}",
                "success_count": success_count,
                "failed_count": failed_count,
            }
        )
    except Exception as e:
        logger.error(f"Bulk update equipment settings error: {e}", exc_info=True)
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


# ==================== EQUIPMENT LOAD API ====================


@router.get("/api/equipment-load")
async def get_equipment_load(
    request: Request,
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
):
    """Получить загрузку оборудования"""
    user = get_user(request)
    if not user:
        return JSONResponse(
            {"success": False, "message": "Не авторизован"}, status_code=401
        )

    db = get_db()
    try:
        now = datetime.now()
        df = (
            datetime.strptime(date_from, "%Y-%m-%d")
            if date_from
            else datetime(now.year, now.month, 1)
        )
        if df.month == 12:
            dt = datetime(df.year + 1, 1, 1) - timedelta(days=1)
        else:
            dt = datetime(df.year, df.month + 1, 1) - timedelta(days=1)
        if date_to:
            dt = datetime.strptime(date_to, "%Y-%m-%d")

        load = db.calculate_equipment_load(df, dt)
        return JSONResponse({"success": True, "load": load})
    except Exception as e:
        logger.error(f"Get equipment load error: {e}", exc_info=True)
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


# ==================== ORDERS API ====================


@router.get("/api/orders")
async def get_planning_orders(request: Request):
    """Получить все заказы с статусом планирования"""
    user = get_user(request)
    if not user:
        return JSONResponse(
            {"success": False, "message": "Не авторизован"}, status_code=401
        )

    db = get_db()
    try:
        orders = db.get_all_orders()
        for order in orders:
            schedule = db.get_production_schedule(order_id=order.get("id"))
            # Конвертируем datetime в строки для JSON
            for item in schedule:
                for key, val in item.items():
                    if isinstance(val, (datetime, date)):
                        item[key] = val.isoformat()

            order["schedule_items"] = schedule
            order["is_planned"] = len(schedule) > 0
            order["is_urgent"] = order.get("priority", 5) == 1

            # Конвертируем datetime в заказе
            for key, val in order.items():
                if isinstance(val, (datetime, date)):
                    order[key] = val.isoformat()

        return JSONResponse({"success": True, "orders": orders})
    except Exception as e:
        logger.error(f"Get orders error: {e}", exc_info=True)
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@router.get("/api/orders/{order_id}")
async def get_planning_order(request: Request, order_id: int):
    """Получить заказ с его расписанием"""
    user = get_user(request)
    if not user:
        return JSONResponse(
            {"success": False, "message": "Не авторизован"}, status_code=401
        )

    db = get_db()
    try:
        order = db.get_order(order_id)
        if not order:
            return JSONResponse(
                {"success": False, "message": "Заказ не найден"}, status_code=404
            )

        schedule = db.get_production_schedule(order_id=order_id)
        # Конвертируем datetime в строки
        for item in schedule:
            for key, val in item.items():
                if isinstance(val, (datetime, date)):
                    item[key] = val.isoformat()

        order["schedule_items"] = schedule

        # Конвертируем datetime в заказе
        for key, val in order.items():
            if isinstance(val, (datetime, date)):
                order[key] = val.isoformat()

        return JSONResponse({"success": True, "order": order})
    except Exception as e:
        logger.error(f"Get order error: {e}", exc_info=True)
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@router.put("/api/orders/{order_id}/priority")
async def update_order_priority(request: Request, order_id: int):
    """Обновить приоритет заказа"""
    user = get_user(request)
    if not user:
        return JSONResponse(
            {"success": False, "message": "Не авторизован"}, status_code=401
        )

    db = get_db()
    try:
        body = await request.json()
        priority = body.get("priority", 5)
        result = db.update_order_priority(order_id, priority)
        return JSONResponse({"success": result})
    except Exception as e:
        logger.error(f"Update order priority error: {e}", exc_info=True)
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@router.post("/api/orders/{order_id}/clear-schedule")
async def clear_order_schedule(request: Request, order_id: int):
    """Очистить расписание заказа"""
    user = get_user(request)
    if not user:
        return JSONResponse(
            {"success": False, "message": "Не авторизован"}, status_code=401
        )

    db = get_db()
    try:
        result = db.clear_order_schedule(order_id)
        return JSONResponse({"success": result})
    except Exception as e:
        logger.error(f"Clear order schedule error: {e}", exc_info=True)
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@router.delete("/api/orders/{order_id}")
async def delete_order_api(request: Request, order_id: int):
    """Удалить заказ"""
    user = get_user(request)
    if not user:
        return JSONResponse(
            {"success": False, "message": "Не авторизован"}, status_code=401
        )

    db = get_db()
    try:
        result = db.delete_order(order_id)
        if result:
            return JSONResponse({"success": True, "message": "Заказ удалён"})
        else:
            return JSONResponse(
                {"success": False, "message": "Заказ не найден"}, status_code=404
            )
    except Exception as e:
        logger.error(f"Delete order error: {e}", exc_info=True)
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


# ==================== CALENDAR EQUIPMENT ORDER API ====================


@router.get("/api/calendar-equipment-order")
async def get_calendar_equipment_order(request: Request):
    """Получить порядок оборудования календаря пользователя"""
    user = get_user(request)
    if not user:
        return JSONResponse(
            {"success": False, "message": "Не авторизован"}, status_code=401
        )

    db = get_db()
    try:
        import json

        user_id = (
            user.get("id") if isinstance(user, dict) else getattr(user, "id", None)
        )
        if not user_id:
            return JSONResponse({"success": True, "equipment_order": []})

        config = db.get_calendar_config(user_id)

        equipment_order = []
        if config and config.get("equipment_order"):
            try:
                equipment_order = (
                    json.loads(config.get("equipment_order", "[]"))
                    if isinstance(config.get("equipment_order"), str)
                    else config.get("equipment_order", [])
                )
            except:
                equipment_order = []

        return JSONResponse({"success": True, "equipment_order": equipment_order})
    except Exception as e:
        logger.error(f"Get equipment order error: {e}", exc_info=True)
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@router.put("/api/calendar-equipment-order")
async def save_calendar_equipment_order(request: Request):
    """Сохранить порядок оборудования календаря пользователя"""
    user = get_user(request)
    if not user:
        return JSONResponse(
            {"success": False, "message": "Не авторизован"}, status_code=401
        )

    db = get_db()
    try:
        import json

        body = await request.json()
        equipment_order = body.get("equipment_order", [])

        # Валидация: equipment_order должен быть списком целых чисел
        if not isinstance(equipment_order, list):
            return JSONResponse(
                {"success": False, "message": "equipment_order должен быть массивом"},
                status_code=400,
            )

        # user — это dict из сессии, используем .get()
        user_id = (
            user.get("id") if isinstance(user, dict) else getattr(user, "id", None)
        )
        if not user_id:
            return JSONResponse(
                {"success": False, "message": "Не удалось определить пользователя"},
                status_code=400,
            )

        # Получаем текущую конфигурацию для сохранения visible_equipment
        current_config = db.get_calendar_config(user_id)
        visible_equipment = []
        panel_visible = True
        if current_config:
            try:
                visible_equipment = (
                    json.loads(current_config.get("visible_equipment", "[]"))
                    if isinstance(current_config.get("visible_equipment"), str)
                    else current_config.get("visible_equipment", [])
                )
            except:
                visible_equipment = []
            panel_visible = current_config.get("panel_visible", True)

        # Сохраняем новый порядок
        result = db.save_calendar_config(
            user_id, visible_equipment, equipment_order, panel_visible
        )
        return JSONResponse({"success": result})
    except Exception as e:
        logger.error(f"Save equipment order error: {e}", exc_info=True)
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


# ==================== CALENDAR CONFIG API ====================


@router.get("/api/calendar-config")
async def get_calendar_config(request: Request):
    """Получить настройки календаря пользователя"""
    user = get_user(request)
    if not user:
        return JSONResponse(
            {"success": False, "message": "Не авторизован"}, status_code=401
        )

    db = get_db()
    try:
        import json

        user_id = (
            user.get("id") if isinstance(user, dict) else getattr(user, "id", None)
        )
        if not user_id:
            return JSONResponse({"success": True, "config": None})
        config = db.get_calendar_config(user_id)

        if config:
            return JSONResponse(
                {
                    "success": True,
                    "config": {
                        "visible_equipment": json.loads(
                            config.get("visible_equipment", "[]")
                        )
                        if isinstance(config.get("visible_equipment"), str)
                        else config.get("visible_equipment", []),
                        "equipment_order": json.loads(
                            config.get("equipment_order", "[]")
                        )
                        if isinstance(config.get("equipment_order"), str)
                        else config.get("equipment_order", []),
                        "panel_visible": config.get("panel_visible", True),
                    },
                }
            )
        else:
            return JSONResponse({"success": True, "config": None})
    except Exception as e:
        logger.error(f"Get calendar config error: {e}", exc_info=True)
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@router.post("/api/calendar-config")
async def save_calendar_config(request: Request):
    """Сохранить настройки календаря пользователя"""
    user = get_user(request)
    if not user:
        return JSONResponse(
            {"success": False, "message": "Не авторизован"}, status_code=401
        )

    db = get_db()
    try:
        body = await request.json()
        user_id = (
            user.get("id") if isinstance(user, dict) else getattr(user, "id", None)
        )
        if not user_id:
            return JSONResponse(
                {"success": False, "message": "Не удалось определить пользователя"},
                status_code=400,
            )
        visible_equipment = body.get("visible_equipment", [])
        equipment_order = body.get("equipment_order", [])
        panel_visible = body.get("panel_visible", True)

        result = db.save_calendar_config(
            user_id, visible_equipment, equipment_order, panel_visible
        )
        return JSONResponse({"success": result})
    except Exception as e:
        logger.error(f"Save calendar config error: {e}", exc_info=True)
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


# ==================== HELPER FUNCTIONS ====================


def _get_days_in_month(year: int, month: int) -> int:
    """Получить количество дней в месяце"""
    import calendar

    return calendar.monthrange(year, month)[1]


def _get_first_day_weekday(year: int, month: int) -> int:
    """Получить день недели первого числа месяца (0=понедельник, 6=воскресенье)"""
    import calendar

    weekday = calendar.monthrange(year, month)[0]
    return weekday  # 0=Monday in calendar.monthrange
