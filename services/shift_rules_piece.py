# services/shift_rules_piece.py
"""
Правила сдвига последующих операций для ШТУЧНОГО производства.

Логика:
- Операции выполняются последовательно по номеру операции (sequence_number)
- Для каждой операции учитывается календарь конкретного станка
- Каждая операция имеет количество деталей (quantity) и время на деталь (duration_minutes)
- Расчёт дней: days_needed = ceil(quantity / parts_per_day)
- part_per_day = max(1, int(420 / duration_minutes))
- Следующая операция начинается после окончания предыдущей + 1 рабочий день
"""

from datetime import datetime, timedelta
from typing import List, Dict


def build_equipment_calendars(
    calendar_data: List[Dict],
    date_from: datetime,
    date_to: datetime,
) -> Dict[int, Dict[str, Dict]]:
    """
    Построить словарь календарей для каждого станка.

    Returns:
        {equipment_id: {"YYYY-MM-DD": calendar_entry, ...}, ...}
    """
    calendars = {}
    for entry in calendar_data:
        eq_id = entry.get("equipment_id")
        if eq_id not in calendars:
            calendars[eq_id] = {}
        date_key = entry.get("date")
        if isinstance(date_key, datetime):
            date_key = date_key.strftime("%Y-%m-%d")
        elif hasattr(date_key, "date"):
            date_key = date_key.date().strftime("%Y-%m-%d")
        calendars[eq_id][date_key] = entry
    return calendars


def prepare_operations_list(schedule: List[Dict]) -> List[Dict]:
    """
    Преобразовать schedule из БД в список операций с нормализованными датами.

    Returns:
        [{id, planned_date, duration_minutes, quantity, equipment_id, sequence_number}, ...]
    """
    ops = []
    for s in schedule:
        planned = s.get("planned_date")
        if isinstance(planned, str):
            try:
                planned = datetime.strptime(planned, "%Y-%m-%d").date()
            except Exception:
                continue
        elif hasattr(planned, "date"):
            planned = planned.date()

        ops.append(
            {
                "id": s.get("id"),
                "planned_date": planned,
                "duration_minutes": s.get("duration_minutes", 60),
                "quantity": s.get("quantity", 1),
                "equipment_id": s.get("equipment_id"),
                "sequence_number": s.get("sequence_number", 0),
            }
        )

    ops.sort(key=lambda x: x.get("sequence_number", 0))
    return ops


def shift_piece_operations(
    db,
    order_id: int,
    changed_schedule_id: int,
    new_date,
    duration: int,
    qty: int,
    old_date=None,
) -> Dict:
    """
    Сдвинуть последующие операции после изменения даты в ШТУЧНОМ производстве.

    Args:
        db: Объект базы данных с методами:
            - get_production_schedule(order_id) -> List[Dict]
            - get_all_equipment(active_only) -> List[Dict]
            - get_all_equipment_calendar(date_from, date_to) -> List[Dict]
            - update_schedule_item(schedule_id, planned_date, is_manual_override) -> bool
            - get_order(order_id) -> Dict
        order_id: ID заказа
        changed_schedule_id: ID изменённой операции
        new_date: Новая дата (date или datetime)
        duration: Длительность на одну деталь в минутах
        qty: Количество деталей
        old_date: Старая дата (для определения диапазона загрузки календаря)

    Returns:
        {"success": bool, "updated_count": int, "operations": List[Dict]}
    """
    from services.planning_rules import (
        calculate_parts_per_day,
        calculate_days_needed,
        add_equipment_working_days,
        find_next_equipment_working_day,
    )

    result = {
        "success": False,
        "updated_count": 0,
        "operations": [],
    }

    try:
        if hasattr(db, "get_order"):
            order = db.get_order(order_id)
            production_type = (
                order.get("production_type", "piece") if order else "piece"
            )
        else:
            production_type = "piece"

        if production_type != "piece":
            print(
                f"DEBUG: shift_piece_operations called for non-piece production: {production_type}, skipping"
            )
            result["success"] = True
            return result

        schedule = db.get_production_schedule(order_id=order_id)
        if not schedule:
            result["success"] = True
            return result

        equipment = db.get_all_equipment(active_only=True)
        date_from = min(old_date, new_date) if old_date else new_date
        date_to = datetime.now() + timedelta(days=365)
        calendar_data = db.get_all_equipment_calendar(date_from, date_to)
        equipment_calendars = build_equipment_calendars(
            calendar_data, date_from, date_to
        )

        ops = prepare_operations_list(schedule)

        print(
            f"DEBUG shift_piece_operations: order_id={order_id}, changed_schedule_id={changed_schedule_id}, new_date={new_date}, duration={duration}, qty={qty}"
        )
        print(f"DEBUG: Total operations in schedule: {len(ops)}")
        for op in ops:
            print(
                f"DEBUG: op id={op['id']}, seq={op['sequence_number']}, date={op['planned_date']}, eq={op['equipment_id']}, duration={op['duration_minutes']}, qty={op['quantity']}"
            )

        changed_idx = None
        for i, op in enumerate(ops):
            if op["id"] == changed_schedule_id:
                changed_idx = i
                break

        if changed_idx is None:
            print(f"DEBUG: changed_schedule_id={changed_schedule_id} not found in ops!")
            return result

        print(
            f"DEBUG: changed_idx={changed_idx}, changed_op seq={ops[changed_idx].get('sequence_number')}"
        )

        changed_op = ops[changed_idx] if changed_idx < len(ops) else None
        actual_duration = (
            changed_op.get("duration_minutes", 60) if changed_op else duration
        )
        actual_qty = changed_op.get("quantity", 1) if changed_op else qty

        print(
            f"DEBUG: Actual values from DB - duration={actual_duration}, qty={actual_qty}"
        )

        current_date = new_date
        parts_per_day = calculate_parts_per_day(actual_duration)
        days_needed = calculate_days_needed(actual_qty, parts_per_day)

        print(
            f"DEBUG: First op - parts_per_day={parts_per_day}, days_needed={days_needed}"
        )

        eq_id = changed_op.get("equipment_id") if changed_op else None
        eq_calendar = equipment_calendars.get(eq_id, {}) if eq_id else {}

        print(f"DEBUG: Calendar has {len(eq_calendar)} entries for eq_id={eq_id}")
        eq_info = next((e for e in equipment if e.get("id") == eq_id), None)
        if eq_info:
            print(
                f"DEBUG: Equipment info - name={eq_info.get('name')}, default_hours={eq_info.get('default_working_hours')}"
            )

        print(
            f"DEBUG: First op - eq_id={eq_id}, new_date={new_date}, searching working days in calendar"
        )

        current_date = add_equipment_working_days(
            current_date, days_needed, eq_id, eq_calendar, equipment
        )

        updated_count = 0
        operations = []

        print(f"DEBUG: current_date after changed_op = {current_date}")

        for i in range(changed_idx + 1, len(ops)):
            op = ops[i]
            op_duration = op["duration_minutes"]
            op_qty = op["quantity"]
            op_parts_per_day = calculate_parts_per_day(op_duration)
            op_days_needed = calculate_days_needed(op_qty, op_parts_per_day)
            print(
                f"DEBUG: Second op from DB - duration={op_duration}, qty={op_qty}, parts_per_day={op_parts_per_day}, days_needed={op_days_needed}"
            )

            op_eq_id = op.get("equipment_id")
            op_calendar = equipment_calendars.get(op_eq_id, {}) if op_eq_id else {}

            search_start_date = current_date + timedelta(days=1)
            print(
                f"DEBUG: op id={op['id']}, seq={op.get('sequence_number')}, current_date={current_date}, search_start={search_start_date}, op_days_needed={op_days_needed}"
            )
            new_op_date = find_next_equipment_working_day(
                search_start_date, op_eq_id, op_calendar, equipment
            )
            print(f"DEBUG: new_op_date found = {new_op_date}")
            if new_op_date is None:
                continue

            if new_op_date < current_date:
                new_op_date = find_next_equipment_working_day(
                    current_date + timedelta(days=1),
                    op_eq_id,
                    op_calendar,
                    equipment,
                )

            print(f"DEBUG: Updating DB op id={op['id']}, new_date={new_op_date}")
            update_result = db.update_schedule_item(
                schedule_id=op["id"],
                planned_date=new_op_date,
                is_manual_override=True,
            )
            print(f"DEBUG: DB update result = {update_result}")

            current_date = add_equipment_working_days(
                new_op_date, op_days_needed, op_eq_id, op_calendar, equipment
            )
            print(f"DEBUG: End date for op {op['id']} = {current_date}")

            updated_count += 1
            operations.append(
                {
                    "id": op["id"],
                    "sequence_number": op.get("sequence_number", 0),
                    "old_date": op.get("planned_date"),
                    "new_date": new_op_date,
                }
            )

        result = {
            "success": True,
            "updated_count": updated_count,
            "operations": operations,
        }

    except Exception as e:
        result["error"] = str(e)

    return result
