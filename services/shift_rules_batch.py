# services/shift_rules_batch.py
"""
Правила сдвига последующих операций для ПАРТИОННОГО производства.

Логика:
- Операции выполняются последовательно по номеру операции (sequence_number)
- Учитывается только базовый календарь рабочих дней (пн-пт), БЕЗ учёта календаря конкретного станка
- Все операции сдвигаются на одинаковую разницу в днях (delta)
- Если меняется первая операция (sequence_number = минимальный) - сдвигаем ВСЁ
- Если меняется промежуточная операция - сдвигаем эту и последующие
- Если меняется последняя операция - сдвигаем только эту
"""

from datetime import datetime, timedelta
from typing import List, Dict


def normalize_date(value) -> datetime:
    """
    Нормализовать значение даты в datetime.

    Args:
        value: Строка, datetime, date или None

    Returns:
        datetime или None
    """
    if value is None:
        return None
    if isinstance(value, str):
        return datetime.strptime(value, "%Y-%m-%d")
    elif hasattr(value, "date"):
        return value.date()
    return value


def calculate_delta(old_date, new_date) -> int:
    """
    Рассчитать разницу в днях между старой и новой датой.

    Returns:
        Количество дней (new_date - old_date)
    """
    old = normalize_date(old_date)
    new = normalize_date(new_date)
    if old is None or new is None:
        return 0
    return (new - old).days


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

    ops.sort(
        key=lambda x: (
            x.get("sequence_number", 0),
            x.get("planned_date") or datetime.min,
        )
    )
    return ops


def determine_shift_scope(ops: List[Dict], changed_schedule_id: int) -> Dict:
    """
    Определить, какие операции нужно сдвинуть.

    Args:
        ops: Список операций
        changed_schedule_id: ID изменённой операции

    Returns:
        {
            "changed_op": Dict,
            "changed_idx": int,
            "changed_seq": int,
            "first_seq": int,
            "last_seq": int,
            "shift_subsequent": bool
        }
    """
    changed_op = None
    changed_idx = None
    for i, op in enumerate(ops):
        if op["id"] == changed_schedule_id:
            changed_op = op
            changed_idx = i
            break

    if changed_op is None:
        return {"changed_op": None}

    changed_seq = changed_op.get("sequence_number", 0)

    first_seq = min(
        op.get("sequence_number", 0) for op in ops if op.get("sequence_number")
    )
    last_seq = max(
        op.get("sequence_number", 0) for op in ops if op.get("sequence_number")
    )

    if changed_seq == first_seq:
        shift_subsequent = True
    elif changed_seq == last_seq:
        shift_subsequent = False
    else:
        shift_subsequent = True

    return {
        "changed_op": changed_op,
        "changed_idx": changed_idx,
        "changed_seq": changed_seq,
        "first_seq": first_seq,
        "last_seq": last_seq,
        "shift_subsequent": shift_subsequent,
    }


def shift_batch_operations(
    db,
    order_id: int,
    changed_schedule_id: int,
    old_date,
    new_date,
) -> Dict:
    """
    Сдвинуть последующие операции после изменения даты в ПАРТИОННОМ производстве.

    Args:
        db: Объект базы данных с методами:
            - get_production_schedule(order_id) -> List[Dict]
            - update_schedule_item(schedule_id, planned_date, is_manual_override) -> bool
        order_id: ID заказа
        changed_schedule_id: ID изменённой операции
        old_date: Старая дата
        new_date: Новая дата

    Returns:
        {"success": bool, "updated_count": int, "operations": List[Dict]}
    """

    result = {
        "success": False,
        "updated_count": 0,
        "operations": [],
    }

    try:
        delta = calculate_delta(old_date, new_date)
        if delta == 0:
            result["success"] = True
            return result

        schedule = db.get_production_schedule(order_id=order_id)
        if not schedule:
            result["success"] = True
            return result

        ops = prepare_operations_list(schedule)

        scope = determine_shift_scope(ops, changed_schedule_id)
        if scope.get("changed_op") is None:
            return result

        shift_subsequent = scope["shift_subsequent"]
        updated_count = 0
        operations = []

        for op in ops:
            op_seq = op.get("sequence_number", 0)
            op_id = op["id"]
            old_op_date = op["planned_date"]

            should_update = False
            if op["id"] == changed_schedule_id:
                should_update = True
            elif shift_subsequent and op_seq > scope["changed_seq"]:
                should_update = True

            if should_update:
                new_op_date = old_op_date + timedelta(days=delta)

                db.update_schedule_item(
                    schedule_id=op_id,
                    planned_date=new_op_date,
                    is_manual_override=True,
                )

                updated_count += 1
                operations.append(
                    {
                        "id": op_id,
                        "sequence_number": op_seq,
                        "old_date": old_op_date,
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
