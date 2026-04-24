# services/production_planner.py
"""
Сервис планирования производства

Правила планирования вынесены в services/planning_rules.py
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

from services.planning_rules import (
    WORKING_HOURS_PER_DAY,
    calculate_duration_days,
    calculate_parts_per_day,
    calculate_days_needed,
    is_working_day,
    calculate_total_minutes,
    get_equipment_working_hours_from_settings,
    calculate_utilization_percent,
    validate_schedule_data,
    DEFAULT_PRIORITY,
    MAX_SEARCH_DAYS,
    is_equipment_working_day,
    add_equipment_working_days,
    find_next_equipment_working_day,
    get_equipment_hours_for_day,
    calculate_available_minutes_for_day,
    calculate_parts_for_day,
    is_day_fully_available,
    add_working_days,
)

URGENT_PRIORITY = 1
NORMAL_PRIORITY = 5

logger = logging.getLogger(__name__)


class ProductionPlanner:
    def __init__(self, db_manager):
        self.db = db_manager

    def _find_orders_using_equipment(
        self,
        equipment_ids: List[int],
        all_scheduled_items: List[Dict],
    ) -> Dict[int, List[Dict]]:
        """Найти все не срочные заказы, которые имеют операции на указанных станках.

        Возвращает dict: {order_id: [schedule_items]}
        """
        equipment_ids_set = set(equipment_ids)
        orders_to_reschedule = {}

        for item in all_scheduled_items:
            item_eq_id = item.get("equipment_id")
            item_order_id = item.get("order_id")

            if item_eq_id in equipment_ids_set and item_order_id:
                if item_order_id not in orders_to_reschedule:
                    orders_to_reschedule[item_order_id] = []
                orders_to_reschedule[item_order_id].append(item)

        return orders_to_reschedule

    def _find_orders_from_db_using_equipment(
        self,
        equipment_ids: List[int],
        start_date: datetime,
        date_to: datetime,
    ) -> Dict[int, Dict]:
        """Найти все не срочные заказы из БД, которые имеют операции на указанных станках.

        Returns: {order_id: {"order": order_data, "items": [schedule_items]}}
        """
        orders_found = {}

        for eq_id in equipment_ids:
            schedule_items = self.db.get_production_schedule(
                date_from=start_date,
                date_to=date_to,
                equipment_id=eq_id,
            )

            for item in schedule_items:
                order_id = item.get("order_id")
                if not order_id:
                    continue

                priority = item.get("priority", DEFAULT_PRIORITY)
                if priority <= URGENT_PRIORITY:
                    continue

                if order_id not in orders_found:
                    order_data = self.db.get_order(order_id)
                    if order_data:
                        orders_found[order_id] = {
                            "order": order_data,
                            "items": [],
                            "priority": priority,
                        }

                if order_id in orders_found:
                    orders_found[order_id]["items"].append(item)

        return orders_found

    def _collect_and_remove_non_urgent_after_date(
        self,
        urgent_start_date: datetime,
        urgent_equipment_ids: List[int],
    ) -> Dict[int, Dict]:
        """Найти и удалить не срочные операции после даты планирования.

        Находит все не срочные операции на указанных станках,
        которые запланированы на urgent_start_date или позже.
        Удаляет их из БД и возвращает данные для перепланирования.

        Returns: {order_id: {"order": order_data, "priority": int, "created_at": datetime}}
        """
        print(
            f"DEBUG _collect_remove: urgent_start_date={urgent_start_date}, equipment={urgent_equipment_ids}"
        )

        removed_orders = {}

        for eq_id in urgent_equipment_ids:
            schedule_items = self.db.get_production_schedule(
                date_from=urgent_start_date,
                date_to=urgent_start_date + timedelta(days=365),
                equipment_id=eq_id,
            )

            for item in schedule_items:
                order_id = item.get("order_id")
                if not order_id:
                    continue

                priority = item.get("priority", DEFAULT_PRIORITY)
                if priority <= URGENT_PRIORITY:
                    continue

                if order_id not in removed_orders:
                    order_data = self.db.get_order(order_id)
                    if order_data:
                        created_at = order_data.get("created_at")
                        if hasattr(created_at, "date"):
                            created_at = created_at.replace(
                                hour=0, minute=0, second=0, microsecond=0
                            )
                        removed_orders[order_id] = {
                            "order": order_data,
                            "priority": priority,
                            "created_at": created_at or datetime.min,
                        }
                        print(
                            f"DEBUG _collect_remove: Found non-urgent order {order_id}, created_at={created_at}"
                        )

        if not removed_orders:
            print("DEBUG _collect_remove: No non-urgent orders to remove")
            return {}

        print(f"DEBUG _collect_remove: Removing {len(removed_orders)} orders from DB")
        for order_id in removed_orders.keys():
            self.db.clear_order_schedule(order_id)
            print(f"DEBUG _collect_remove: Cleared schedule for order {order_id}")

        return removed_orders

    def _reschedule_removed_orders(
        self,
        removed_orders: Dict[int, Dict],
        urgent_end_dates: Dict[int, Dict],
        equipment_calendars: Dict,
        equipment: List[Dict],
    ) -> int:
        """Перепланировать удалённые ранее не срочные заказы.

        Каждая операция планируется отдельно, учитывая когда конкретное
        оборудование освободится от срочной детали.

        Returns: количество перепланированных заказов
        """
        from services.planning_rules import find_next_equipment_working_day
        from services.planning_rules import calculate_available_minutes_for_day
        from services.planning_rules import get_equipment_hours_for_day
        from services.planning_rules import is_equipment_working_day

        if not removed_orders:
            print("DEBUG _reschedule: No removed orders to reschedule")
            return 0

        print(f"DEBUG _reschedule: urgent_end_dates input = {urgent_end_dates}")

        if not urgent_end_dates:
            print(
                "WARNING: urgent_end_dates is EMPTY! Will use datetime.now() for all equipment"
            )
            urgent_end_dates_normalized = {}
        else:
            urgent_end_dates_normalized = {}
            for eq_id, end_info in urgent_end_dates.items():
                date = end_info.get("date")
                eq_name = end_info.get("name", "")
                if date:
                    if hasattr(date, "date"):
                        urgent_end_dates_normalized[eq_id] = {
                            "date": date.date(),
                            "name": eq_name,
                        }
                    else:
                        urgent_end_dates_normalized[eq_id] = {
                            "date": date,
                            "name": eq_name,
                        }

        print(
            f"DEBUG _reschedule: urgent_end_dates_normalized={urgent_end_dates_normalized}"
        )

        sorted_orders = sorted(
            removed_orders.items(), key=lambda x: x[1].get("created_at", datetime.min)
        )

        print(
            f"DEBUG _reschedule: Processing {len(sorted_orders)} orders to reschedule"
        )

        total_rescheduled = 0

        all_items = []

        for order_id, order_info in sorted_orders:
            target_order = order_info["order"]
            original_priority = order_info["priority"]

            if not target_order:
                continue

            route_id = target_order.get("route_id")
            if not route_id:
                print(f"DEBUG _reschedule: Order {order_id} has no route")
                continue

            operations = self._get_route_operations(route_id)
            if not operations:
                print(f"DEBUG _reschedule: Order {order_id} has no operations")
                continue

            quantity = target_order.get("quantity", 1)
            print(
                f"DEBUG _reschedule: Rescheduling order {order_id}, qty={quantity}, ops={len(operations)}"
            )

            for op in operations:
                eq_id = op.get("equipment_id")
                if not eq_id:
                    continue

                # Для расчётов используем total_time, duration_minutes оставляем для UI
                total_time = op.get("total_time", 60)
                duration_minutes = op.get("duration_minutes", 60)  # Для UI
                eq_calendar = equipment_calendars.get(eq_id, {})

                if eq_id in urgent_end_dates_normalized:
                    urgent_eq_end_date = urgent_end_dates_normalized[eq_id].get("date")
                    urgent_eq_name = urgent_end_dates_normalized[eq_id].get("name", "")
                    if urgent_eq_end_date:
                        search_from_date = datetime.combine(
                            urgent_eq_end_date + timedelta(days=1), datetime.min.time()
                        )
                        print(
                            f"DEBUG _reschedule: Op {op['sequence_number']} eq {eq_id} ({urgent_eq_name}) - URGENT, waiting until {urgent_eq_end_date + timedelta(days=1)}"
                        )
                    else:
                        search_from_date = datetime.now()
                        print(
                            f"DEBUG _reschedule: Op {op['sequence_number']} eq {eq_id} - no date in urgent_end_dates, using now"
                        )
                else:
                    search_from_date = datetime.now()
                    print(
                        f"DEBUG _reschedule: Op {op['sequence_number']} eq {eq_id} - NOT urgent (not in urgent_end_dates), starting from now"
                    )

                next_day = find_next_equipment_working_day(
                    search_from_date,
                    eq_id,
                    eq_calendar,
                    equipment,
                )
                if next_day is None:
                    next_day = search_from_date

                print(
                    f"DEBUG _reschedule: Op {op['sequence_number']} eq {eq_id} - first available: {next_day}"
                )

                remaining_qty = quantity

                while remaining_qty > 0:
                    if not is_equipment_working_day(
                        next_day, eq_id, eq_calendar, equipment
                    ):
                        next_day = find_next_equipment_working_day(
                            next_day + timedelta(days=1),
                            eq_id,
                            eq_calendar,
                            equipment,
                        )
                        if next_day is None:
                            break
                        continue

                    db_schedule = self.db.get_production_schedule(
                        date_from=next_day,
                        date_to=next_day,
                        equipment_id=eq_id,
                    )
                    combined_schedule = all_items + db_schedule

                    available_minutes = calculate_available_minutes_for_day(
                        next_day,
                        eq_id,
                        eq_calendar,
                        equipment,
                        combined_schedule,
                    )

                    if available_minutes <= 0:
                        next_day = find_next_equipment_working_day(
                            next_day + timedelta(days=1),
                            eq_id,
                            eq_calendar,
                            equipment,
                        )
                        if next_day is None:
                            break
                        continue

                    total_working_minutes = (
                        get_equipment_hours_for_day(
                            next_day, eq_id, eq_calendar, equipment
                        )
                        * 60
                    )

                    parts_can_do = available_minutes // total_time
                    parts_to_schedule = min(parts_can_do, remaining_qty)

                    if parts_to_schedule > 0:
                        result = self.db.add_to_production_schedule(
                            order_id=order_id,
                            route_operation_id=op.get("route_operation_id"),
                            equipment_id=eq_id,
                            planned_date=next_day,
                            quantity=parts_to_schedule,
                            priority=original_priority,
                            duration_minutes=duration_minutes,
                            status="planned",
                        )

                        if result:
                            scheduled_item = {
                                "planned_date": next_day,
                                "equipment_id": eq_id,
                                "quantity": parts_to_schedule,
                                "duration_minutes": duration_minutes,
                                "priority": original_priority,
                                "order_id": order_id,
                            }
                            all_items.append(scheduled_item)
                            remaining_qty -= parts_to_schedule
                            print(
                                f"DEBUG _reschedule: Scheduled {parts_to_schedule} parts on {next_day}, remaining={remaining_qty}"
                            )

                            if remaining_qty > 0:
                                next_day = find_next_equipment_working_day(
                                    next_day + timedelta(days=1),
                                    eq_id,
                                    eq_calendar,
                                    equipment,
                                )
                                if next_day is None:
                                    break
                    else:
                        next_day = find_next_equipment_working_day(
                            next_day + timedelta(days=1),
                            eq_id,
                            eq_calendar,
                            equipment,
                        )
                        if next_day is None:
                            break

            if all_items:
                first_date = min(item["planned_date"] for item in all_items)
                last_date = max(item["planned_date"] for item in all_items)
                if hasattr(first_date, "strftime"):
                    start_str = first_date.strftime("%d.%m.%Y")
                    end_str = last_date.strftime("%d.%m.%Y")
                else:
                    start_str = str(first_date)[:10]
                    end_str = str(last_date)[:10]
                self.db.update_order_dates(order_id, start_str, end_str)

                print(f"DEBUG _reschedule: Order {order_id} scheduled items:")
                for item in all_items:
                    eq_id = item.get("equipment_id")
                    qty = item.get("quantity")
                    date = item.get("planned_date")
                    date_str = (
                        date.strftime("%Y-%m-%d")
                        if hasattr(date, "strftime")
                        else str(date)
                    )
                    print(f"  - Eq {eq_id}: {qty} pcs on {date_str}")

                print(
                    f"DEBUG _reschedule: Order {order_id} rescheduled from {start_str} to {end_str}"
                )
            else:
                print(f"DEBUG _reschedule: Order {order_id} - NO items scheduled!")

            total_rescheduled += 1

        print(f"DEBUG _reschedule: Total rescheduled: {total_rescheduled}")
        return total_rescheduled

    def _shift_lower_priority_operations(
        self,
        order_id: int,
        urgent_end_dates: Dict[int, Dict],
        urgent_order_days: Dict[int, List[Dict]],
        all_scheduled_items: List[Dict],
        equipment_calendars: Dict,
        equipment: List[Dict],
    ) -> int:
        """Перепланировать не срочные заказы, использующие станки срочного заказа.

        Алгоритм:
        1. Определить глобальную дату окончания срочного заказа (max по всем станкам)
        2. Получить список станков из маршрута срочного заказа
        3. Найти ВСЕ не срочные заказы, которые имеют операции на этих станках
        4. Для каждого такого заказа:
           - Удалить ВСЕ его операции из БД
           - Перепланировать полностью с даты после окончания срочного
        """
        from services.planning_rules import find_next_equipment_working_day

        total_shifted = 0

        print(f"DEBUG _shift: Processing urgent order {order_id}")
        print(f"DEBUG _shift: urgent_end_dates={urgent_end_dates}")

        if not urgent_end_dates:
            print("DEBUG _shift: No urgent_end_dates, nothing to shift")
            return 0

        urgent_equipment_ids = list(urgent_end_dates.keys())
        print(f"DEBUG _shift: Urgent equipment IDs: {urgent_equipment_ids}")

        urgent_max_global = None
        for eq_id, end_info in urgent_end_dates.items():
            date = end_info.get("date")
            if hasattr(date, "date"):
                date = date.date()
            if urgent_max_global is None or date > urgent_max_global:
                urgent_max_global = date

        if urgent_max_global is None:
            print("DEBUG _shift: No urgent_max_global date found")
            return 0

        print(f"DEBUG _shift: urgent_max_global={urgent_max_global}")

        start_date = datetime.now()
        date_to = urgent_max_global + timedelta(days=365)

        orders_to_reschedule = self._find_orders_from_db_using_equipment(
            urgent_equipment_ids,
            start_date,
            date_to,
        )

        if not orders_to_reschedule:
            print("DEBUG _shift: No non-urgent orders found on urgent equipment")
            return 0

        print(
            f"DEBUG _shift: Found {len(orders_to_reschedule)} non-urgent orders to reschedule: {list(orders_to_reschedule.keys())}"
        )

        orders_to_shift_ids = set(orders_to_reschedule.keys())
        urgent_order_ids_set = {order_id}

        urgent_items = [
            item
            for item in all_scheduled_items
            if item.get("is_urgent") or item.get("order_id") in urgent_order_ids_set
        ]
        other_items = [
            item
            for item in all_scheduled_items
            if item.get("order_id") not in orders_to_shift_ids
            and not item.get("is_urgent")
        ]
        filtered_scheduled_items = urgent_items + other_items

        print(
            f"DEBUG _shift: Filtered items: urgent={len(urgent_items)}, other={len(other_items)}, total={len(filtered_scheduled_items)}"
        )

        self._try_insert_non_urgent_in_urgent_gaps(
            orders_to_reschedule,
            urgent_end_dates,
            urgent_order_days,
            filtered_scheduled_items,
            equipment_calendars,
            equipment,
        )

        for target_order_id, order_info in orders_to_reschedule.items():
            target_order = order_info["order"]
            original_priority = order_info["priority"]
            original_items = order_info["items"]

            if not target_order:
                print(f"DEBUG _shift: Order {target_order_id} not found in DB")
                continue

            original_start = None
            for item in original_items:
                d = item.get("planned_date")
                if d:
                    if hasattr(d, "date"):
                        d = d.date()
                    if original_start is None or d < original_start:
                        original_start = d

            print(
                f"DEBUG _shift: Rescheduling order {target_order_id} (priority={original_priority}) from {original_start}"
            )

            self.db.clear_order_schedule(target_order_id)
            print(f"DEBUG _shift: Cleared schedule for order {target_order_id}")

            current_order_items = [
                item
                for item in filtered_scheduled_items
                if item.get("order_id") != target_order_id
            ]

            target_route_id = target_order.get("route_id")
            if not target_route_id:
                print(f"DEBUG _shift: Order {target_order_id} has no route")
                continue

            target_equipment_ids = self._get_route_equipment_ids(target_route_id)
            print(
                f"DEBUG _shift: Order {target_order_id} uses equipment: {target_equipment_ids}"
            )

            urgent_equipment_ids_set = set(urgent_equipment_ids)

            new_start = None
            search_date_urgent = urgent_max_global + timedelta(days=1)
            search_date_now = datetime.now()

            for eq_id in target_equipment_ids:
                eq_calendar = equipment_calendars.get(eq_id, {})

                if eq_id in urgent_equipment_ids_set:
                    search_from = search_date_urgent
                else:
                    search_from = search_date_now

                candidate_start = find_next_equipment_working_day(
                    search_from,
                    eq_id,
                    eq_calendar,
                    equipment,
                )

                if candidate_start:
                    if new_start is None or candidate_start < new_start:
                        new_start = candidate_start
                        print(
                            f"DEBUG _shift: Eq {eq_id} - first available: {candidate_start} (search from {search_from})"
                        )

            if new_start is None:
                first_eq_id = (
                    target_equipment_ids[0]
                    if target_equipment_ids
                    else urgent_equipment_ids[0]
                )
                eq_calendar = equipment_calendars.get(first_eq_id, {})
                new_start = find_next_equipment_working_day(
                    search_date_urgent,
                    first_eq_id,
                    eq_calendar,
                    equipment,
                )

            if new_start is None:
                print(f"DEBUG _shift: No working day found for order {target_order_id}")
                continue

            print(
                f"DEBUG _shift: Replanning order {target_order_id} from {original_start} to {new_start}"
            )

            production_type = target_order.get("production_type", "piece")
            if production_type == "batch":
                self.calculate_batch_schedule_with_items(
                    target_order,
                    new_start,
                    original_priority,
                    current_order_items,
                    equipment_calendars,
                    equipment,
                )
            else:
                self._calculate_piece_schedule_with_items(
                    target_order,
                    new_start,
                    original_priority,
                    current_order_items,
                    equipment_calendars,
                    equipment,
                )

            total_shifted += 1
            print(
                f"DEBUG _shift: Replanned order {target_order_id} from {original_start} to {new_start}"
            )

        return total_shifted

    def _try_insert_non_urgent_in_urgent_gaps(
        self,
        orders_to_reschedule: Dict[int, Dict],
        urgent_end_dates: Dict[int, Dict],
        urgent_order_days: Dict[int, List[Dict]],
        all_scheduled_items: List[Dict],
        equipment_calendars: Dict,
        equipment: List[Dict],
    ) -> None:
        """Попытка вставить операции не срочных заказов в свободное время срочной детали.

        Для каждого станка срочной детали:
        1. Найти последний день срочной детали на этом станке
        2. Проверить свободное время в этот день
        3. Если есть свободное время - вставить операции не срочных заказов
        """

        print("DEBUG _try_insert_gaps: Checking gaps in urgent order")

        for eq_id, end_info in urgent_end_dates.items():
            end_date = end_info.get("date")
            if not end_date:
                continue

            eq_calendar = equipment_calendars.get(eq_id, {})

            available_minutes = calculate_available_minutes_for_day(
                end_date,
                eq_id,
                eq_calendar,
                equipment,
                all_scheduled_items,
            )

            if available_minutes <= 0:
                print(
                    f"DEBUG _try_insert_gaps: Eq {eq_id} - no free time on {end_date}"
                )
                continue

            print(
                f"DEBUG _try_insert_gaps: Eq {eq_id} - {available_minutes} min free on {end_date}"
            )

            total_inserted = 0
            for order_id, order_info in orders_to_reschedule.items():
                target_order = order_info["order"]
                original_priority = order_info["priority"]

                if not target_order:
                    continue

                route_id = target_order.get("route_id")
                if not route_id:
                    continue

                ops = self._get_route_operations(route_id)
                if not ops:
                    continue

                for op in ops:
                    op_eq_id = op.get("equipment_id")
                    if op_eq_id != eq_id:
                        continue

                    # Для расчётов используем total_time, duration_minutes для UI
                    total_time = op.get("total_time", 60)
                    duration_minutes = op.get("duration_minutes", 60)  # Для UI
                    quantity = target_order.get("quantity", 1)

                    if available_minutes < total_time:
                        break

                    parts_to_insert = min(available_minutes // total_time, quantity)

                    if parts_to_insert > 0:
                        result = self.db.add_to_production_schedule(
                            order_id=order_id,
                            route_operation_id=op.get("route_operation_id"),
                            equipment_id=eq_id,
                            planned_date=end_date,
                            quantity=parts_to_insert,
                            priority=original_priority,
                            duration_minutes=duration_minutes,
                            status="planned",
                        )

                        if result:
                            all_scheduled_items.append(
                                {
                                    "planned_date": end_date,
                                    "equipment_id": eq_id,
                                    "quantity": parts_to_insert,
                                    "duration_minutes": duration_minutes,
                                    "priority": original_priority,
                                    "order_id": order_id,
                                }
                            )
                            total_inserted += parts_to_insert
                            available_minutes -= parts_to_insert * total_time
                            print(
                                f"DEBUG _try_insert_gaps: Inserted {parts_to_insert} parts for order {order_id} on {end_date}"
                            )

                            target_order["quantity"] = quantity - parts_to_insert

                            if available_minutes < total_time:
                                break

                if total_inserted > 0:
                    break

    def _get_route_operations(self, route_id: int) -> List[Dict]:
        """Получить операции маршрута."""
        from sqlalchemy import text
        from config import DATABASE_URL
        from sqlalchemy import create_engine

        operations = []

        try:
            engine = create_engine(DATABASE_URL)
            with engine.connect() as conn:
                result = conn.execute(
                    text("""
                        SELECT
                            ro.id as route_operation_id,
                            ro.sequence_number,
                            ro.duration_minutes,
                            ro.prep_time,
                            ro.control_time,
                            ro.total_time,
                            ro.parts_count,
                            ro.equipment_id as default_equipment_id,
                            ro.operation_type_id,
                            ot.name as operation_name,
                            e.name as equipment_name,
                            e.id as equipment_id
                        FROM route_operations ro
                        LEFT JOIN operation_types ot ON ro.operation_type_id = ot.id
                        LEFT JOIN equipment e ON ro.equipment_id = e.id
                        WHERE ro.route_id = :route_id
                        ORDER BY ro.sequence_number
                    """),
                    {"route_id": route_id},
                )
                for row in result:
                    operations.append(
                        {
                            "route_operation_id": row.route_operation_id,
                            "sequence_number": row.sequence_number,
                            "duration_minutes": row.duration_minutes or 60,
                            "prep_time": row.prep_time or 0,
                            "control_time": row.control_time or 0,
                            "total_time": row.total_time or 60,
                            "parts_count": row.parts_count or 1,
                            "operation_name": row.operation_name or "",
                            "equipment_id": row.equipment_id
                            or row.default_equipment_id,
                            "equipment_name": row.equipment_name or "",
                            "operation_type_id": row.operation_type_id,
                        }
                    )
        except Exception as e:
            print(f"DEBUG _get_route_operations error: {e}")

        return operations

    def _get_route_equipment_ids(self, route_id: int) -> List[int]:
        """Получить список ID оборудования из маршрута."""
        from sqlalchemy import text
        from config import DATABASE_URL
        from sqlalchemy import create_engine

        equipment_ids = []

        try:
            engine = create_engine(DATABASE_URL)
            with engine.connect() as conn:
                result = conn.execute(
                    text("""
                        SELECT DISTINCT COALESCE(ro.equipment_id, e.id) as equipment_id
                        FROM route_operations ro
                        LEFT JOIN equipment e ON ro.equipment_id = e.id
                        WHERE ro.route_id = :route_id
                        AND COALESCE(ro.equipment_id, e.id) IS NOT NULL
                    """),
                    {"route_id": route_id},
                )
                for row in result:
                    if row.equipment_id:
                        equipment_ids.append(row.equipment_id)
        except Exception as e:
            print(f"DEBUG _get_route_equipment_ids error: {e}")

        return equipment_ids

    def _find_shift_date(
        self,
        equipment_id: int,
        after_date,
        total_duration_minutes: int,
        equipment_calendar: dict,
        equipment: List[Dict],
        all_scheduled_items: List[Dict],
    ) -> Optional[datetime]:
        """Найти ближайшую подходящую дату для сдвига операции.

        Пытается сначала разместить операцию в последний день срочного заказа
        (если хватает места), иначе ищет следующий рабочий день.
        """
        if hasattr(after_date, "date"):
            start_search = after_date + timedelta(days=1)
        else:
            start_search = after_date + timedelta(days=1)

        first_working_day = find_next_equipment_working_day(
            start_search,
            equipment_id,
            equipment_calendar,
            equipment,
        )

        if first_working_day is None:
            return None

        available = calculate_available_minutes_for_day(
            first_working_day,
            equipment_id,
            equipment_calendar,
            equipment,
            all_scheduled_items,
        )

        if available >= total_duration_minutes:
            return first_working_day

        search_date = find_next_equipment_working_day(
            first_working_day + timedelta(days=1),
            equipment_id,
            equipment_calendar,
            equipment,
        )

        for _ in range(365):
            if search_date is None:
                break

            available = calculate_available_minutes_for_day(
                search_date,
                equipment_id,
                equipment_calendar,
                equipment,
                all_scheduled_items,
            )

            if available >= total_duration_minutes:
                return search_date

            search_date = find_next_equipment_working_day(
                search_date + timedelta(days=1),
                equipment_id,
                equipment_calendar,
                equipment,
            )

        return None

    def get_equipment_working_hours(self, equipment_id: int, date: datetime) -> int:
        """Получить количество рабочих часов для станка на конкретную дату"""
        try:
            calendar = self.db.get_equipment_calendar(equipment_id, date, date)
            calendar_entry = calendar[0] if calendar else None
            equipment = self.db.get_all_equipment()
            return get_equipment_working_hours_from_settings(
                equipment, equipment_id, calendar_entry
            )
        except Exception as e:
            logger.error(f"Error getting working hours: {e}")
            return WORKING_HOURS_PER_DAY

    def calculate_operation_duration_days(
        self, duration_minutes: int, equipment_id: int, start_date: datetime
    ) -> int:
        """Рассчитать сколько дней нужно для операции"""
        hours_per_day = self.get_equipment_working_hours(equipment_id, start_date)
        if hours_per_day == 0:
            return 1
        return calculate_duration_days(duration_minutes, hours_per_day)

    def find_available_date(
        self,
        equipment_id: int,
        start_date: datetime,
        duration_days: int,
        max_days_search: int = MAX_SEARCH_DAYS,
    ) -> Optional[datetime]:
        """Найти ближайшую доступную дату для станка (только рабочие дни)"""
        if start_date is None:
            return None
        equipment = self.db.get_all_equipment(active_only=True)
        date_to = start_date + timedelta(days=max_days_search)
        calendar_data = self.db.get_all_equipment_calendar(start_date, date_to)

        eq_calendar = {}
        for entry in calendar_data:
            if entry.get("equipment_id") == equipment_id:
                date_key = entry.get("date")
                if isinstance(date_key, datetime):
                    date_key = date_key.strftime("%Y-%m-%d")
                eq_calendar[date_key] = entry

        current_date = start_date

        for _ in range(max_days_search):
            if not is_equipment_working_day(
                current_date, equipment_id, eq_calendar, equipment
            ):
                current_date += timedelta(days=1)
                continue

            hours = get_equipment_hours_for_day(
                current_date, equipment_id, eq_calendar, equipment
            )
            if hours > 0:
                duration_days -= 1
                if duration_days <= 0:
                    return current_date
            current_date += timedelta(days=1)

        return None

    def get_equipment_load(
        self, equipment_id: int, date_from: datetime, date_to: datetime
    ) -> Dict:
        """Получить загрузку станка за период"""
        schedule = self.db.get_production_schedule(
            date_from=date_from, date_to=date_to, equipment_id=equipment_id
        )

        total_minutes = 0
        scheduled_days = set()

        for item in schedule:
            if item.get("planned_date"):
                planned_date = item["planned_date"]
                if isinstance(planned_date, str):
                    planned_date = datetime.strptime(planned_date, "%Y-%m-%d")
                scheduled_days.add(planned_date.date())

            duration = item.get("duration_minutes", 60)
            qty = item.get("quantity", 1)
            total_minutes += calculate_total_minutes(duration, qty)

        equipment = self.db.get_all_equipment(active_only=True)
        calendar_data = self.db.get_all_equipment_calendar(date_from, date_to)

        eq_calendar = {}
        for entry in calendar_data:
            if entry.get("equipment_id") == equipment_id:
                date_key = entry.get("date")
                if isinstance(date_key, datetime):
                    date_key = date_key.strftime("%Y-%m-%d")
                eq_calendar[date_key] = entry

        working_hours_total = 0
        current = date_from
        while current <= date_to:
            hours = get_equipment_hours_for_day(
                current, equipment_id, eq_calendar, equipment
            )
            working_hours_total += hours
            current += timedelta(days=1)

        return {
            "equipment_id": equipment_id,
            "total_scheduled_minutes": total_minutes,
            "total_available_minutes": working_hours_total * 60,
            "utilization_percent": calculate_utilization_percent(
                total_minutes, working_hours_total * 60
            ),
            "scheduled_days": len(scheduled_days),
            "working_days": working_hours_total,
        }

    def calculate_schedule(
        self,
        order_id: int,
        start_date: datetime = None,
        priority: int = 3,
        equipment_overrides: List[Dict] = None,
    ) -> Dict:
        """Автоматический расчёт расписания для заказа

        Проверяет тип производства:
        - 'piece' (штучное): обычное последовательное планирование
        - 'batch' (партийное): планирование с перекрытием операций

        При добавлении срочного заказа (priority=1):
        1. Находит все не срочные операции на станках срочного заказа после даты планирования
        2. Удаляет их из БД
        3. Планирует срочный заказ
        4. Перепланирует удалённые не срочные заказы

        Args:
            order_id: ID заказа
            start_date: Дата начала планирования
            priority: Приоритет (1-5, где 1 = самый срочный)
            equipment_overrides: Список замен станков [{operation_seq, new_equipment_id, ...}]
        """
        if start_date is None:
            start_date = datetime.now()

        if equipment_overrides:
            logger.info(f"Equipment overrides: {len(equipment_overrides)} operations")

        try:
            orders = self.db.get_all_orders()
            order = None
            for o in orders:
                if o.get("id") == order_id:
                    order = o
                    break

            if not order:
                return {"success": False, "message": "Заказ не найден"}

            production_type = order.get("production_type", "piece")

            if production_type == "batch":
                return self.calculate_batch_schedule(order, start_date, priority)
            else:
                if priority == URGENT_PRIORITY:
                    return self._calculate_piece_schedule_urgent(
                        order, start_date, priority, equipment_overrides
                    )
                else:
                    return self._calculate_piece_schedule(
                        order, start_date, priority, equipment_overrides
                    )

        except Exception as e:
            logger.error(f"Calculate schedule error: {e}")
            import traceback

            traceback.print_exc()
            return {"success": False, "message": str(e)}

    def _calculate_piece_schedule(
        self,
        order,
        start_date: datetime,
        priority: int = 3,
        equipment_overrides: List[Dict] = None,
    ) -> Dict:
        """Последовательное планирование для штучного производства

        Особенности:
        - Рабочий день = 7 часов (420 минут)
        - Учитывает уже запланированные операции на каждый день
        - Если есть свободное время - вставляет сколько деталей поместится
        - Если деталь не помещается - переносит на следующий день

        При приоритетном планировании:
        - Если на дату есть операция с более низким приоритетом (число больше)
        - То сдвигаем её и вставляем новую операцию вперед
        """
        try:
            order_id = order.get("id")
            route_id = order.get("route_id")
            quantity = order.get("quantity", 1)

            from sqlalchemy import text
            from config import DATABASE_URL
            from sqlalchemy import create_engine

            engine = create_engine(DATABASE_URL)

            with engine.connect() as conn:
                ops_result = conn.execute(
                    text("""
                    SELECT
                        ro.id as route_operation_id,
                        ro.sequence_number,
                        ro.duration_minutes,
                        ro.prep_time,
                        ro.control_time,
                        ro.total_time,
                        ro.parts_count,
                        ro.notes,
                        ro.equipment_id as default_equipment_id,
                        ro.operation_type_id,
                        ro.is_cooperation,
                        ro.coop_duration_days,
                        ro.coop_position,
                        ro.coop_company_id,
                        ot.name as operation_name,
                        e.name as equipment_name,
                        e.id as equipment_id,
                        c.name as coop_company_name
                    FROM route_operations ro
                    LEFT JOIN operation_types ot ON ro.operation_type_id = ot.id
                    LEFT JOIN equipment e ON ro.equipment_id = e.id
                    LEFT JOIN cooperatives c ON ro.coop_company_id = c.id
                    WHERE ro.route_id = :route_id
                    ORDER BY ro.sequence_number
                """),
                    {"route_id": route_id},
                )
                ops = ops_result.fetchall()

            if not ops:
                return {"success": False, "message": "Нет операций в маршруте"}

            coop_start_days = 0
            coop_end_days = 0

            coop_sequences = []
            for op in ops:
                is_coop = bool(getattr(op, "is_cooperation", False))
                if is_coop:
                    coop_sequences.append(op.sequence_number)

            coop_min_seq = min(coop_sequences) if coop_sequences else None
            coop_max_seq = max(coop_sequences) if coop_sequences else None

            operations = []
            for op in ops:
                is_coop = bool(getattr(op, "is_cooperation", False))
                coop_duration = getattr(op, "coop_duration_days", 0) or 0

                if is_coop and coop_duration > 0:
                    if op.sequence_number == coop_min_seq:
                        coop_start_days += coop_duration
                    if op.sequence_number == coop_max_seq:
                        coop_end_days += coop_duration

                operations.append(
                    {
                        "route_operation_id": op.route_operation_id,
                        "sequence_number": op.sequence_number,
                        "duration_minutes": op.duration_minutes or 60,
                        "prep_time": op.prep_time or 0,
                        "control_time": op.control_time or 0,
                        "total_time": op.total_time or 60,
                        "parts_count": op.parts_count or 1,
                        "operation_name": op.operation_name or "",
                        "equipment_id": op.equipment_id or op.default_equipment_id,
                        "equipment_name": op.equipment_name or "",
                        "notes": op.notes or "",
                        "operation_type_id": op.operation_type_id,
                        "is_cooperation": is_coop,
                        "coop_duration_days": coop_duration,
                        "coop_company_id": getattr(op, "coop_company_id", None),
                        "coop_company_name": getattr(op, "coop_company_name", "") or "",
                    }
                )

            # Coop_start_days используется только для расчёта сдвига итоговой даты окончания
            # start_date НЕ сдвигаем - кооперация начинается с указанной пользователем даты

            is_valid, error_msg = validate_schedule_data({"id": order_id}, operations)
            if not is_valid:
                return {"success": False, "message": error_msg}

            existing_schedule_from_db = self.db.get_production_schedule(
                date_from=start_date, date_to=start_date + timedelta(days=365)
            )

            # Очищаем старый план и route_card_data
            self.db.clear_order_schedule(order_id)

            # Удаляем из all_scheduled_items записи текущего заказа
            all_scheduled_items = [
                item
                for item in existing_schedule_from_db
                if item.get("order_id") != order_id
            ]
            all_scheduled_items_backup = list(
                all_scheduled_items
            )  # Сохраняем для реального планирования

            equipment = self.db.get_all_equipment(active_only=True)
            date_to = start_date + timedelta(days=365)
            calendar_data = self.db.get_all_equipment_calendar(start_date, date_to)

            equipment_calendars = {}
            for entry in calendar_data:
                eq_id = entry.get("equipment_id")
                if eq_id not in equipment_calendars:
                    equipment_calendars[eq_id] = {}
                date_key = entry.get("date")
                if isinstance(date_key, datetime):
                    date_key = date_key.strftime("%Y-%m-%d")
                equipment_calendars[eq_id][date_key] = entry

            equipment_ids_for_order = list(
                set(op["equipment_id"] for op in operations if op.get("equipment_id"))
            )

            urgent_end_dates = {}
            urgent_order_days = {}

            sim_current_date = start_date
            sim_remaining = quantity

            for sim_op_idx, op in enumerate(operations):
                # Кооперативные операции не планируются на оборудовании
                # Они просто добавляют задержку (время на выполнение на стороне)
                if op.get("is_cooperation"):
                    coop_duration = op.get("coop_duration_days", 0) or 0
                    if coop_duration > 0:
                        sim_current_date = add_working_days(
                            sim_current_date, coop_duration
                        )
                    continue

                equipment_id = op["equipment_id"]
                if not equipment_id:
                    continue

                # Для расчётов используем total_time, duration_minutes для UI
                total_time = op["total_time"]
                duration_minutes = op["duration_minutes"]  # Для UI
                operation_type_id = op.get("operation_type_id")
                eq_calendar = equipment_calendars.get(equipment_id, {})

                last_sim_day = None
                parts_on_last_day = 0
                sim_remaining = quantity

                while sim_remaining > 0:
                    if sim_current_date == start_date and is_equipment_working_day(
                        start_date, equipment_id, eq_calendar, equipment
                    ):
                        sim_day = start_date
                    else:
                        sim_day = find_next_equipment_working_day(
                            sim_current_date,
                            equipment_id,
                            eq_calendar,
                            equipment,
                            max_days=365,
                        )
                    if sim_day is None:
                        break

                    available = calculate_available_minutes_for_day(
                        sim_day,
                        equipment_id,
                        eq_calendar,
                        equipment,
                        all_scheduled_items,
                        operation_type_id=operation_type_id,
                    )
                    parts_can = calculate_parts_for_day(total_time, available)

                    if parts_can > 0:
                        if last_sim_day is None:
                            last_sim_day = sim_day
                        parts_today = min(parts_can, sim_remaining)
                        parts_on_last_day = parts_today
                        sim_remaining -= parts_today

                        occupied_minutes = parts_today * total_time

                        all_scheduled_items.append(
                            {
                                "planned_date": sim_day,
                                "equipment_id": equipment_id,
                                "quantity": parts_today,
                                "duration_minutes": duration_minutes,
                                "operation_type_id": operation_type_id,
                                "is_simulated": True,
                                "is_urgent": True,
                            }
                        )

                        if equipment_id not in urgent_order_days:
                            urgent_order_days[equipment_id] = []
                        urgent_order_days[equipment_id].append(
                            {
                                "date": sim_day,
                                "occupied_minutes": occupied_minutes,
                                "operation_type_id": operation_type_id,
                            }
                        )

                    if sim_remaining > 0:
                        # Текущая операция не закончена, переходим на следующий день
                        sim_current_date = sim_day + timedelta(days=1)
                    else:
                        # Текущая операция закончена, проверяем следующий станок
                        is_last_sim_op = sim_op_idx == len(operations) - 1
                        if is_last_sim_op:
                            sim_current_date = sim_day + timedelta(days=1)
                        else:
                            next_op = operations[sim_op_idx + 1]
                            next_eq_id = next_op["equipment_id"]
                            if next_eq_id:
                                next_eq_calendar = equipment_calendars.get(
                                    next_eq_id, {}
                                )
                                avail_for_next = calculate_available_minutes_for_day(
                                    sim_day,
                                    next_eq_id,
                                    next_eq_calendar,
                                    equipment,
                                    all_scheduled_items,
                                    operation_type_id=next_op.get("operation_type_id"),
                                )
                                if avail_for_next > 0:
                                    sim_current_date = sim_day
                                else:
                                    sim_current_date = sim_day + timedelta(days=1)
                            else:
                                sim_current_date = sim_day + timedelta(days=1)

                if last_sim_day is not None:
                    end_time_minutes = parts_on_last_day * total_time
                    urgent_end_dates[equipment_id] = {
                        "date": last_sim_day,
                        "end_time_minutes": end_time_minutes,
                        "operation_type_id": operation_type_id,
                    }
                    # Проверяем, можно ли начать следующую операцию в тот же день
                    is_last_sim_op = sim_op_idx == len(operations) - 1
                    if is_last_sim_op:
                        sim_current_date = last_sim_day + timedelta(days=1)
                    else:
                        next_op = operations[sim_op_idx + 1]
                        next_eq_id = next_op["equipment_id"]
                        if next_eq_id:
                            next_eq_calendar = equipment_calendars.get(next_eq_id, {})
                            avail_for_next = calculate_available_minutes_for_day(
                                last_sim_day,
                                next_eq_id,
                                next_eq_calendar,
                                equipment,
                                all_scheduled_items,
                                operation_type_id=next_op.get("operation_type_id"),
                            )
                            if avail_for_next > 0:
                                sim_current_date = last_sim_day
                            else:
                                sim_current_date = last_sim_day + timedelta(days=1)
                        else:
                            sim_current_date = last_sim_day + timedelta(days=1)

            print("DEBUG _calculate_piece_schedule ENTRY:")
            print(
                f"  order_id={order_id}, start_date={start_date}, priority={priority}, quantity={quantity}"
            )
            print(f"  operations count={len(operations)}")
            for i, op in enumerate(operations):
                print(
                    f"    op[{i}]: seq={op['sequence_number']}, name={op['operation_name']}, eq_id={op['equipment_id']}, eq_name={op['equipment_name']}, duration={op['duration_minutes']}min"
                )

            # Восстанавливаем расписание ДО симуляции и ДО shift операций
            # Это критически важно для URGENT заказов - shift мог добавить записи других заказов
            all_scheduled_items = list(all_scheduled_items_backup)

            print(
                f"  After restore from backup: {len(all_scheduled_items)} items in all_scheduled_items"
            )
            # Показать записи на start_date после восстановления
            start_date_str = start_date.strftime("%Y-%m-%d")
            for eq_id in equipment_ids_for_order:
                eq_entries = [
                    item
                    for item in all_scheduled_items
                    if item.get("equipment_id") == eq_id
                    and (
                        str(item.get("planned_date"))[:10] == start_date_str
                        if item.get("planned_date")
                        else False
                    )
                ]
                if eq_entries:
                    eq_name = next(
                        (
                            op.get("equipment_name")
                            for op in operations
                            if op.get("equipment_id") == eq_id
                        ),
                        f"eq_{eq_id}",
                    )
                    total_minutes = sum(
                        item.get("quantity", 0) * item.get("duration_minutes", 0)
                        for item in eq_entries
                    )
                    print(
                        f"    DB entries on {start_date_str} for eq {eq_id} ({eq_name}): {len(eq_entries)} items, total {total_minutes} min"
                    )
                    for item in eq_entries:
                        print(
                            f"      order_id={item.get('order_id')}, qty={item.get('quantity')}, duration={item.get('duration_minutes')}min"
                        )

            # Запускаем shift операции ПОСЛЕ восстановления из backup
            shifted_orders_count = 0
            if priority == URGENT_PRIORITY and (urgent_end_dates or urgent_order_days):
                # Временно восстанавливаем из backup для shift
                all_scheduled_items_before_shift = list(all_scheduled_items_backup)
                shifted_orders_count = self._shift_lower_priority_operations(
                    order_id,
                    urgent_end_dates,
                    urgent_order_days,
                    all_scheduled_items_before_shift,
                    equipment_calendars,
                    equipment,
                )
                # После shift восстанавливаем оригинальный backup
                # Shift мог добавить записи других заказов, они нам не нужны здесь
                all_scheduled_items = list(all_scheduled_items_backup)
                print(f"DEBUG: Urgent ends per equipment: {urgent_end_dates}")
                print(
                    f"DEBUG: Shifted {shifted_orders_count} operations for urgent order {order_id}"
                )

            schedule_items = []
            current_date = start_date
            remaining_quantity = quantity

            # Только для URGENT заказов добавляем симулированные items обратно
            # Для обычных заказов симуляция не требуется и вызывала смещение на 1 день
            if priority == URGENT_PRIORITY:
                simulated_urgent_items = [
                    item for item in all_scheduled_items if item.get("is_simulated")
                ]
                all_scheduled_items.extend(simulated_urgent_items)
                print(
                    f"DEBUG: Restored {len(simulated_urgent_items)} simulated urgent items"
                )

                # Для URGENT заказов игнорируем записи других заказов
                # URGENT заказ имеет приоритет и должен вытеснять другие заказы
                # Оставляем только записи текущего заказа (для корректного exclude) и симулированные
                items_before_filter = len(all_scheduled_items)
                all_scheduled_items = [
                    item
                    for item in all_scheduled_items
                    if item.get("order_id") == order_id or item.get("is_simulated")
                ]
                print(
                    f"DEBUG: URGENT - filtered from {items_before_filter} to {len(all_scheduled_items)} items (ignoring other orders)"
                )

            for op_idx, op in enumerate(operations):
                # Кооперативные операции - добавляем в schedule_items и сохраняем в БД
                if op.get("is_cooperation"):
                    coop_duration = op.get("coop_duration_days", 0) or 0
                    coop_start_date = current_date
                    # Если coop_duration = 0, используем 1 рабочий день по умолчанию
                    if coop_duration <= 0:
                        coop_duration = 1
                    coop_end_date = add_working_days(current_date, coop_duration)
                    # Сохраняем в БД
                    self.db.add_to_production_schedule(
                        order_id=order_id,
                        route_operation_id=op["route_operation_id"],
                        equipment_id=None,
                        planned_date=coop_start_date,
                        quantity=quantity,
                        priority=priority,
                        status="planned",
                        is_cooperation=True,
                        coop_company_name=op.get("coop_company_name") or "",
                        coop_duration_days=coop_duration,
                    )
                    schedule_items.append(
                        {
                            "date": coop_start_date.strftime("%Y-%m-%d")
                            if isinstance(coop_start_date, datetime)
                            else coop_start_date,
                            "datetime": coop_start_date,
                            "planned_date": coop_start_date.strftime("%d.%m.%Y")
                            if isinstance(coop_start_date, datetime)
                            else coop_start_date,
                            "end_date": coop_end_date.strftime("%d.%m.%Y")
                            if isinstance(coop_end_date, datetime)
                            else coop_end_date,
                            "equipment_name": op.get("coop_company_name")
                            or "Кооперация",
                            "equipment_id": None,
                            "operation_name": op["operation_name"],
                            "operation_type_id": op.get("operation_type_id"),
                            "sequence_number": op["sequence_number"],
                            "duration_minutes": 0,
                            "is_cooperation": True,
                            "coop_company_name": op.get("coop_company_name") or "",
                            "coop_duration_days": coop_duration,
                            "status": "planned",
                        }
                    )
                    current_date = coop_end_date
                    sim_current_date = coop_end_date
                    print(
                        f"  COOP DEBUG: after coop op, current_date={current_date}, sim_current_date={sim_current_date}"
                    )
                    continue

                equipment_id = op["equipment_id"]

                # Применяем equipment_overrides если пользователь выбрал альтернативный станок
                if equipment_overrides:
                    for override in equipment_overrides:
                        op_seq = override.get("operation_seq") or override.get(
                            "operationSeq"
                        )
                        new_eq_id = override.get("new_equipment_id") or override.get(
                            "newEquipmentId"
                        )
                        if op_seq == op["sequence_number"] and new_eq_id:
                            equipment_id = new_eq_id
                            logger.info(
                                f"Override: operation {op['sequence_number']} "
                                f"equipment -> {new_eq_id}"
                            )
                            break

                if not equipment_id:
                    logger.warning(
                        f"No equipment for operation {op['sequence_number']}"
                    )
                    continue

                # Для расчётов используем total_time, duration_minutes оставляем для UI
                total_time = op["total_time"]
                duration_minutes = op["duration_minutes"]  # Для UI
                eq_calendar = equipment_calendars.get(equipment_id, {})

                operation_start_date = None
                operation_end_date = None
                last_worked_day = None
                remaining_quantity = quantity

                while remaining_quantity > 0:
                    # Важно: start_date - это пожелание, а не аксиома.
                    # Всегда проверяем реальную доступность станка.
                    current_day = find_next_equipment_working_day(
                        current_date,
                        equipment_id,
                        eq_calendar,
                        equipment,
                        max_days=365,
                    )
                    if current_day is None:
                        logger.warning(
                            f"No available working day for equipment {equipment_id}"
                        )
                        break

                    available_minutes = calculate_available_minutes_for_day(
                        current_day,
                        equipment_id,
                        eq_calendar,
                        equipment,
                        all_scheduled_items,
                        exclude_order_id=order_id,
                    )

                    # Если день полностью занят - ищем следующий свободный
                    while available_minutes <= 0 and current_day is not None:
                        current_day = find_next_equipment_working_day(
                            current_day + timedelta(days=1),
                            equipment_id,
                            eq_calendar,
                            equipment,
                            max_days=365,
                        )
                        if current_day is None:
                            break
                        available_minutes = calculate_available_minutes_for_day(
                            current_day,
                            equipment_id,
                            eq_calendar,
                            equipment,
                            all_scheduled_items,
                            exclude_order_id=order_id,
                        )

                    if current_day is None:
                        logger.warning(
                            f"No available day found for equipment {equipment_id}"
                        )
                        break

                    total_working_minutes = (
                        get_equipment_hours_for_day(
                            current_day, equipment_id, eq_calendar, equipment
                        )
                        * 60
                    )

                    # Проверяем сколько минут УЖЕ занято на этот день
                    occupied_by_others = total_working_minutes - available_minutes
                    occupancy_percent = (
                        (occupied_by_others / total_working_minutes * 100)
                        if total_working_minutes > 0
                        else 0
                    )

                    # Если день занят больше чем на 50% другими заказами - ищем свободный день
                    # Это предотвращает фрагментацию и накладывание заказов на один день
                    if occupancy_percent > 50:
                        current_date = current_day + timedelta(days=1)
                        continue  # Переходим к следующей итерации while

                    # Всегда используем реальные доступные минуты, а не оптимизацию
                    parts_can_do = calculate_parts_for_day(
                        total_time, available_minutes
                    )
                    parts_to_schedule = min(parts_can_do, remaining_quantity)

                    if parts_to_schedule > 0:
                        result = self.db.add_to_production_schedule(
                            order_id=order_id,
                            route_operation_id=op["route_operation_id"],
                            equipment_id=equipment_id,
                            planned_date=current_day,
                            quantity=parts_to_schedule,
                            priority=priority,
                            duration_minutes=duration_minutes,
                            status="planned",
                        )

                        if result:
                            scheduled_item = {
                                "planned_date": current_day,
                                "equipment_id": equipment_id,
                                "quantity": parts_to_schedule,
                                "duration_minutes": duration_minutes,
                                "priority": priority,
                                "is_urgent": priority == URGENT_PRIORITY,
                                "order_id": order_id,
                            }
                            all_scheduled_items.append(scheduled_item)

                            if operation_start_date is None:
                                operation_start_date = current_day
                            operation_end_date = current_day
                            last_worked_day = current_day

                            schedule_items.append(
                                {
                                    "date": current_day.strftime("%Y-%m-%d"),
                                    "datetime": current_day,
                                    "equipment_id": equipment_id,
                                    "equipment_name": op["equipment_name"],
                                    "operation_name": op["operation_name"],
                                    "parts": parts_to_schedule,
                                    "duration_minutes": duration_minutes,
                                    "operation_seq": op["sequence_number"],
                                    "sequence_number": op["sequence_number"],
                                    "start_date": current_day.strftime("%d.%m.%Y"),
                                    "end_date": current_day.strftime("%d.%m.%Y"),
                                    "days_count": 1,
                                    "parts_per_day": parts_can_do,
                                }
                            )

                            remaining_quantity -= parts_to_schedule

                        if remaining_quantity > 0:
                            current_date = current_day + timedelta(days=1)
                        else:
                            is_last_op = op_idx == len(operations) - 1
                            if is_last_op:
                                current_date = current_day + timedelta(days=1)
                            else:
                                next_op = operations[op_idx + 1]
                                next_eq_id = next_op["equipment_id"]
                                if next_eq_id:
                                    next_eq_calendar = equipment_calendars.get(
                                        next_eq_id, {}
                                    )
                                    avail_for_next = (
                                        calculate_available_minutes_for_day(
                                            current_day,
                                            next_eq_id,
                                            next_eq_calendar,
                                            equipment,
                                            all_scheduled_items,
                                            exclude_order_id=order_id,
                                        )
                                    )
                                    next_day = current_day + timedelta(days=1)
                                    current_date = find_next_equipment_working_day(
                                        next_day,
                                        next_eq_id,
                                        next_eq_calendar,
                                        equipment,
                                        max_days=365,
                                    )
                                    if current_date is None:
                                        current_date = next_day
                                    print(
                                        f"    -> Op waits for prev to finish, next available: {current_date}"
                                    )
                                else:
                                    current_date = current_day + timedelta(days=1)
                                    print(
                                        f"    -> no next_eq_id, moving to next day: {current_date}"
                                    )
                    else:
                        if priority == URGENT_PRIORITY:
                            current_date = current_day + timedelta(days=1)
                        else:
                            search_date = find_next_equipment_working_day(
                                current_day + timedelta(days=1),
                                equipment_id,
                                eq_calendar,
                                equipment,
                                max_days=365,
                            )
                            found_day_with_space = False
                            while search_date is not None:
                                avail = calculate_available_minutes_for_day(
                                    search_date,
                                    equipment_id,
                                    eq_calendar,
                                    equipment,
                                    all_scheduled_items,
                                    exclude_order_id=order_id,
                                )
                                if avail > 0:
                                    found_day_with_space = True
                                    break
                                search_date = find_next_equipment_working_day(
                                    search_date + timedelta(days=1),
                                    equipment_id,
                                    eq_calendar,
                                    equipment,
                                    max_days=365,
                                )

                            if found_day_with_space:
                                current_date = search_date
                            else:
                                current_date = current_day + timedelta(days=1)

                if last_worked_day is not None:
                    current_date = last_worked_day + timedelta(days=1)

            start_str = ""
            end_str = ""
            if schedule_items:
                first_item = schedule_items[0]
                start_str = (
                    first_item.get("start_date") or first_item.get("planned_date") or ""
                )
                end_str = schedule_items[-1].get("end_date") or ""

            if coop_end_days > 0 and end_str:
                end_dt = datetime.strptime(end_str, "%d.%m.%Y")
                end_dt = end_dt + timedelta(days=coop_end_days)
                end_str = end_dt.strftime("%d.%m.%Y")

            print("DEBUG _calculate_piece_schedule EXIT:")
            print(f"  schedule_items count: {len(schedule_items)}")
            for i, item in enumerate(schedule_items):
                print(
                    f"  item[{i}]: date={item.get('date')}, op={item.get('operation_name')}, eq={item.get('equipment_name')}, parts={item.get('parts', 'N/A')}"
                )
            print(f"  RESULT: start_date={start_str}, end_date={end_str}")

            self.db.update_order_dates(order_id, start_str, end_str)

            result = {
                "success": True,
                "schedule": schedule_items,
                "start_date": start_str,
                "end_date": end_str,
                "message": f"Запланировано {len(schedule_items)} операций",
                "shifted_orders": shifted_orders_count,
            }

            if shifted_orders_count > 0:
                result["message"] += f" (сдвинуто {shifted_orders_count} операций)"

            return result

        except Exception as e:
            logger.error(f"Piece schedule error: {e}")
            import traceback

            traceback.print_exc()
            return {"success": False, "message": str(e)}

    def _calculate_piece_schedule_urgent(
        self,
        order,
        start_date: datetime,
        priority: int = 1,
        equipment_overrides: List[Dict] = None,
    ) -> Dict:
        """Планирование срочного заказа с переносом не срочных.

        Алгоритм:
        1. Получить equipment_ids из маршрута срочного заказа
        2. Найти и удалить все не срочные операции на этих станках после start_date
        3. Запланировать срочный заказ
        4. Перепланировать удалённые не срочные заказы
        """
        try:
            order_id = order.get("id")
            route_id = order.get("route_id")

            print(
                f"DEBUG _calculate_piece_schedule_urgent: order_id={order_id}, start_date={start_date}"
            )

            urgent_equipment_ids = self._get_route_equipment_ids(route_id)
            print(
                f"DEBUG _calculate_piece_schedule_urgent: equipment_ids={urgent_equipment_ids}"
            )

            removed_orders = self._collect_and_remove_non_urgent_after_date(
                start_date,
                urgent_equipment_ids,
            )

            equipment = self.db.get_all_equipment(active_only=True)
            date_to = start_date + timedelta(days=365)
            calendar_data = self.db.get_all_equipment_calendar(start_date, date_to)

            equipment_calendars = {}
            for entry in calendar_data:
                eq_id = entry.get("equipment_id")
                if eq_id not in equipment_calendars:
                    equipment_calendars[eq_id] = {}
                date_key = entry.get("date")
                if isinstance(date_key, datetime):
                    date_key = date_key.strftime("%Y-%m-%d")
                equipment_calendars[eq_id][date_key] = entry

            existing_schedule = self.db.get_production_schedule(
                date_from=start_date - timedelta(days=30),
                date_to=date_to,
            )
            all_scheduled_items = [
                item for item in existing_schedule if item.get("order_id") != order_id
            ]

            self.db.clear_order_schedule(order_id)

            result = self._calculate_piece_schedule_with_items(
                order,
                start_date,
                priority,
                all_scheduled_items,
                equipment_calendars,
                equipment,
            )

            print(f"DEBUG _calculate_piece_schedule_urgent: schedule result = {result}")

            if result.get("success"):
                schedule_items = result.get("schedule", [])
                print(
                    f"DEBUG _calculate_piece_schedule_urgent: schedule_items count = {len(schedule_items)}"
                )

                urgent_end_dates = {}
                for item in schedule_items:
                    eq_id = item.get("equipment_id")
                    planned_date = item.get("datetime")
                    eq_name = item.get("equipment_name", "")
                    if eq_id and planned_date:
                        if (
                            eq_id not in urgent_end_dates
                            or planned_date > urgent_end_dates[eq_id]["date"]
                        ):
                            urgent_end_dates[eq_id] = {
                                "date": planned_date,
                                "name": eq_name,
                            }

                print(
                    f"DEBUG _calculate_piece_schedule_urgent: urgent_end_dates={urgent_end_dates}"
                )

                rescheduled_count = self._reschedule_removed_orders(
                    removed_orders,
                    urgent_end_dates,
                    equipment_calendars,
                    equipment,
                )

                result["shifted_orders"] = rescheduled_count
                if rescheduled_count > 0:
                    result["message"] += f" (перенесено {rescheduled_count} заказов)"
            else:
                print(
                    f"DEBUG _calculate_piece_schedule_urgent: scheduling FAILED - {result.get('message')}"
                )

            return result

        except Exception as e:
            logger.error(f"Piece schedule urgent error: {e}")
            import traceback

            traceback.print_exc()
            return {"success": False, "message": str(e)}

    def _calculate_piece_schedule_with_items(
        self,
        order,
        start_date: datetime,
        priority: int,
        all_scheduled_items: List[Dict],
        equipment_calendars: Dict,
        equipment: List[Dict],
    ) -> Dict:
        """Планирование для штучного производства с предварительно подготовленным расписанием.

        Отличается от _calculate_piece_schedule тем, что:
        - Принимает all_scheduled_items как параметр (не получает из БД)
        - Не выполняет симуляцию
        - Не вызывает _shift_lower_priority_operations
        """
        try:
            order_id = order.get("id")
            route_id = order.get("route_id")
            quantity = order.get("quantity", 1)

            from sqlalchemy import text
            from config import DATABASE_URL
            from sqlalchemy import create_engine

            engine = create_engine(DATABASE_URL)

            with engine.connect() as conn:
                ops_result = conn.execute(
                    text("""
                    SELECT
                        ro.id as route_operation_id,
                        ro.sequence_number,
                        ro.duration_minutes,
                        ro.prep_time,
                        ro.control_time,
                        ro.total_time,
                        ro.parts_count,
                        ro.notes,
                        ro.equipment_id as default_equipment_id,
                        ro.operation_type_id,
                        ro.is_cooperation,
                        ro.coop_duration_days,
                        ro.coop_position,
                        ro.coop_company_id,
                        ot.name as operation_name,
                        e.name as equipment_name,
                        e.id as equipment_id,
                        c.name as coop_company_name
                    FROM route_operations ro
                    LEFT JOIN operation_types ot ON ro.operation_type_id = ot.id
                    LEFT JOIN equipment e ON ro.equipment_id = e.id
                    LEFT JOIN cooperatives c ON ro.coop_company_id = c.id
                    WHERE ro.route_id = :route_id
                    ORDER BY ro.sequence_number
                """),
                    {"route_id": route_id},
                )
                ops = ops_result.fetchall()

            if not ops:
                return {"success": False, "message": "Нет операций в маршруте"}

            coop_start_days = 0
            coop_end_days = 0

            coop_sequences = []
            for op in ops:
                is_coop = bool(getattr(op, "is_cooperation", False))
                if is_coop:
                    coop_sequences.append(op.sequence_number)

            coop_min_seq = min(coop_sequences) if coop_sequences else None
            coop_max_seq = max(coop_sequences) if coop_sequences else None

            operations = []
            for op in ops:
                is_coop = bool(getattr(op, "is_cooperation", False))
                coop_duration = getattr(op, "coop_duration_days", 0) or 0

                if is_coop and coop_duration > 0:
                    if op.sequence_number == coop_min_seq:
                        coop_start_days += coop_duration
                    if op.sequence_number == coop_max_seq:
                        coop_end_days += coop_duration

                operations.append(
                    {
                        "route_operation_id": op.route_operation_id,
                        "sequence_number": op.sequence_number,
                        "duration_minutes": op.duration_minutes or 60,
                        "prep_time": op.prep_time or 0,
                        "control_time": op.control_time or 0,
                        "total_time": op.total_time or 60,
                        "parts_count": op.parts_count or 1,
                        "operation_name": op.operation_name or "",
                        "equipment_id": op.equipment_id or op.default_equipment_id,
                        "equipment_name": op.equipment_name or "",
                        "notes": op.notes or "",
                        "operation_type_id": op.operation_type_id,
                        "is_cooperation": is_coop,
                        "coop_duration_days": coop_duration,
                        "coop_company_id": getattr(op, "coop_company_id", None),
                        "coop_company_name": getattr(op, "coop_company_name", "") or "",
                    }
                )

            # Coop_start_days используется только для расчёта сдвига итоговой даты окончания
            # start_date НЕ сдвигаем - кооперация начинается с указанной пользователем даты

            is_valid, error_msg = validate_schedule_data({"id": order_id}, operations)
            if not is_valid:
                return {"success": False, "message": error_msg}

            print(
                f"DEBUG _calculate_piece_schedule_with_items: order_id={order_id}, start_date={start_date}, priority={priority}"
            )

            schedule_items = []
            current_date = start_date
            remaining_quantity = quantity

            for op_idx, op in enumerate(operations):
                # Пропускаем кооперативные операции (у них нет оборудования)
                if op.get("is_cooperation"):
                    continue

                equipment_id = op["equipment_id"]

                # Применяем equipment_overrides
                if equipment_overrides:
                    for override in equipment_overrides:
                        op_seq = override.get("operation_seq") or override.get(
                            "operationSeq"
                        )
                        new_eq_id = override.get("new_equipment_id") or override.get(
                            "newEquipmentId"
                        )
                        if op_seq == op["sequence_number"] and new_eq_id:
                            old_eq_id = equipment_id
                            equipment_id = new_eq_id
                            logger.info(
                                f"[URGENT] Override: operation {op['sequence_number']} "
                                f"eq {old_eq_id} -> {new_eq_id}"
                            )
                            break

                if not equipment_id:
                    logger.warning(
                        f"No equipment for operation {op['sequence_number']}"
                    )
                    continue

                # Для расчётов используем total_time, duration_minutes для UI
                total_time = op["total_time"]
                duration_minutes = op["duration_minutes"]  # Для UI
                eq_calendar = equipment_calendars.get(equipment_id, {})

                operation_start_date = None
                operation_end_date = None
                last_worked_day = None
                remaining_quantity = quantity

                while remaining_quantity > 0:
                    if current_date == start_date and is_equipment_working_day(
                        start_date, equipment_id, eq_calendar, equipment
                    ):
                        current_day = start_date
                    else:
                        current_day = find_next_equipment_working_day(
                            current_date,
                            equipment_id,
                            eq_calendar,
                            equipment,
                            max_days=365,
                        )
                    if current_day is None:
                        logger.warning(
                            f"No available working day for equipment {equipment_id}"
                        )
                        break

                    available_minutes = calculate_available_minutes_for_day(
                        current_day,
                        equipment_id,
                        eq_calendar,
                        equipment,
                        all_scheduled_items,
                        exclude_order_id=order_id,
                    )

                    total_working_minutes = (
                        get_equipment_hours_for_day(
                            current_day, equipment_id, eq_calendar, equipment
                        )
                        * 60
                    )

                    is_fully_available = is_day_fully_available(
                        current_day,
                        equipment_id,
                        eq_calendar,
                        equipment,
                        all_scheduled_items,
                        threshold=0.9,
                    )

                    if is_fully_available and total_working_minutes > 0:
                        max_parts_for_day = total_working_minutes // total_time
                        parts_to_schedule = min(max_parts_for_day, remaining_quantity)
                        parts_can_do = max_parts_for_day
                    else:
                        parts_can_do = calculate_parts_for_day(
                            total_time, available_minutes
                        )
                        parts_to_schedule = min(parts_can_do, remaining_quantity)

                    if parts_to_schedule > 0:
                        result = self.db.add_to_production_schedule(
                            order_id=order_id,
                            route_operation_id=op["route_operation_id"],
                            equipment_id=equipment_id,
                            planned_date=current_day,
                            quantity=parts_to_schedule,
                            priority=priority,
                            duration_minutes=duration_minutes,
                            status="planned",
                        )

                        if result:
                            scheduled_item = {
                                "planned_date": current_day,
                                "equipment_id": equipment_id,
                                "quantity": parts_to_schedule,
                                "duration_minutes": duration_minutes,
                                "priority": priority,
                                "is_urgent": priority == URGENT_PRIORITY,
                                "order_id": order_id,
                            }
                            all_scheduled_items.append(scheduled_item)

                            if operation_start_date is None:
                                operation_start_date = current_day
                            operation_end_date = current_day
                            last_worked_day = current_day

                            schedule_items.append(
                                {
                                    "date": current_day.strftime("%Y-%m-%d"),
                                    "datetime": current_day,
                                    "equipment_id": equipment_id,
                                    "equipment_name": op["equipment_name"],
                                    "operation_name": op["operation_name"],
                                    "parts": parts_to_schedule,
                                    "duration_minutes": duration_minutes,
                                    "operation_seq": op["sequence_number"],
                                    "sequence_number": op["sequence_number"],
                                    "start_date": current_day.strftime("%d.%m.%Y"),
                                    "end_date": current_day.strftime("%d.%m.%Y"),
                                    "days_count": 1,
                                    "parts_per_day": parts_can_do,
                                }
                            )

                            remaining_quantity -= parts_to_schedule

                        if remaining_quantity > 0:
                            current_date = current_day + timedelta(days=1)
                        else:
                            is_last_op = op_idx == len(operations) - 1
                            if is_last_op:
                                current_date = current_day + timedelta(days=1)
                            else:
                                next_op = operations[op_idx + 1]
                                next_eq_id = next_op["equipment_id"]
                                if next_eq_id:
                                    next_eq_calendar = equipment_calendars.get(
                                        next_eq_id, {}
                                    )
                                    next_day = current_day + timedelta(days=1)
                                    current_date = find_next_equipment_working_day(
                                        next_day,
                                        next_eq_id,
                                        next_eq_calendar,
                                        equipment,
                                        max_days=365,
                                    )
                                    if current_date is None:
                                        current_date = next_day
                                else:
                                    current_date = current_day + timedelta(days=1)
                    else:
                        search_date = find_next_equipment_working_day(
                            current_day + timedelta(days=1),
                            equipment_id,
                            eq_calendar,
                            equipment,
                            max_days=365,
                        )
                        found_day_with_space = False
                        while search_date is not None:
                            avail = calculate_available_minutes_for_day(
                                search_date,
                                equipment_id,
                                eq_calendar,
                                equipment,
                                all_scheduled_items,
                                exclude_order_id=order_id,
                            )
                            if avail > 0:
                                found_day_with_space = True
                                break
                            search_date = find_next_equipment_working_day(
                                search_date + timedelta(days=1),
                                equipment_id,
                                eq_calendar,
                                equipment,
                                max_days=365,
                            )

                        if found_day_with_space:
                            current_date = search_date
                        else:
                            current_date = current_day + timedelta(days=1)

                if last_worked_day is not None:
                    current_date = last_worked_day + timedelta(days=1)

            # Coop_start_days используется только для расчёта сдвига итоговой даты окончания

            start_str = ""
            end_str = ""
            if schedule_items:
                first_item = schedule_items[0]
                start_str = (
                    first_item.get("start_date") or first_item.get("planned_date") or ""
                )
                end_str = schedule_items[-1].get("end_date") or ""

            if coop_end_days > 0 and end_str:
                end_dt = datetime.strptime(end_str, "%d.%m.%Y")
                end_dt = end_dt + timedelta(days=coop_end_days)
                end_str = end_dt.strftime("%d.%m.%Y")

            self.db.update_order_dates(order_id, start_str, end_str)

            result = {
                "success": True,
                "schedule": schedule_items,
                "start_date": start_str,
                "end_date": end_str,
                "message": f"Запланировано {len(schedule_items)} операций",
            }

            return result

        except Exception as e:
            logger.error(f"Piece schedule with items error: {e}")
            import traceback

            traceback.print_exc()
            return {"success": False, "message": str(e)}

    def check_priority_conflicts(
        self, operations: List[Dict], start_date: datetime, priority: int
    ) -> Dict[int, Dict]:
        """Проверить конфликты приоритетов для оборудования

        Returns:
            Dict[equipment_id, {
                "has_conflict": bool,
                "conflict_schedule_id": int,  # ID операции которую нужно сдвинуть
                "conflict_priority": int,      # Приоритет конфликтующей операции
                "days_needed_for_new": int,   # Сколько дней нужно для новой операции
            }]
        """
        conflicts = {}

        for op in operations:
            equipment_id = op.get("equipment_id")
            if not equipment_id or equipment_id in conflicts:
                continue

            # Для расчётов используем total_time, duration_minutes для UI
            total_time = op.get("total_time", 60)
            duration_minutes = op.get("duration_minutes", 60)  # Для UI
            quantity = op.get("quantity", 1)
            parts_per_day = calculate_parts_per_day(total_time)
            days_needed = calculate_days_needed(quantity, parts_per_day)

            date_from = start_date
            date_to = start_date + timedelta(days=days_needed + 30)

            existing_schedule = self.db.get_production_schedule(
                date_from=date_from, date_to=date_to, equipment_id=equipment_id
            )

            if not existing_schedule:
                conflicts[equipment_id] = {
                    "has_conflict": False,
                    "days_needed_for_new": days_needed,
                }
                continue

            start_date_str = (
                start_date.strftime("%Y-%m-%d")
                if isinstance(start_date, datetime)
                else str(start_date)
            )
            if hasattr(start_date, "strftime"):
                start_date_str = start_date.strftime("%Y-%m-%d")
            else:
                start_date_str = str(start_date)

            conflicting_items = []
            for item in existing_schedule:
                item_date = item.get("planned_date")
                if item_date:
                    if isinstance(item_date, str):
                        item_date_str = item_date[:10]
                    elif hasattr(item_date, "strftime"):
                        item_date_str = item_date.strftime("%Y-%m-%d")
                    else:
                        item_date_str = str(item_date)

                    if item_date_str == start_date_str:
                        item_priority = item.get("priority", DEFAULT_PRIORITY)
                        conflicting_items.append(
                            {
                                "id": item.get("id"),
                                "priority": item_priority,
                                "planned_date": item.get("planned_date"),
                                "quantity": item.get("quantity", 1),
                                "duration_minutes": item.get("duration_minutes", 60),
                            }
                        )

            if not conflicting_items:
                conflicts[equipment_id] = {
                    "has_conflict": False,
                    "days_needed_for_new": days_needed,
                }
                continue

            conflicting_items.sort(key=lambda x: x["priority"], reverse=True)
            lowest_priority_item = conflicting_items[-1]

            if priority < lowest_priority_item["priority"]:
                conflicts[equipment_id] = {
                    "has_conflict": True,
                    "conflict_schedule_id": lowest_priority_item["id"],
                    "conflict_priority": lowest_priority_item["priority"],
                    "conflict_item": lowest_priority_item,
                    "days_needed_for_new": days_needed,
                }
            else:
                conflicts[equipment_id] = {
                    "has_conflict": False,
                    "days_needed_for_new": days_needed,
                }

        return conflicts

    def shift_operations_for_priority_insert(
        self,
        schedule_id: int,
        days_to_shift: int,
        equipment_id: int,
        start_date: datetime,
    ) -> Dict:
        """Сдвинуть операцию и все последующие для освобождения места"""
        try:
            date_from = start_date
            date_to = start_date + timedelta(days=365)

            all_schedule = self.db.get_production_schedule(
                date_from=date_from, date_to=date_to, equipment_id=equipment_id
            )

            equipment = self.db.get_all_equipment(active_only=True)
            calendar_data = self.db.get_all_equipment_calendar(date_from, date_to)

            eq_calendar = {}
            for entry in calendar_data:
                if entry.get("equipment_id") == equipment_id:
                    date_key = entry.get("date")
                    if isinstance(date_key, datetime):
                        date_key = date_key.strftime("%Y-%m-%d")
                    eq_calendar[date_key] = entry

            current_date = start_date
            for _ in range(days_to_shift):
                current_date = find_next_equipment_working_day(
                    current_date, equipment_id, eq_calendar, equipment
                )
                if current_date is None:
                    break
                current_date += timedelta(days=1)

            shifted_count = 0
            for item in all_schedule:
                item_date = item.get("planned_date")
                if item_date:
                    if hasattr(item_date, "date"):
                        item_date_only = item_date.date()
                    else:
                        item_date_only = item_date

                    start_date_only = (
                        start_date.date() if hasattr(start_date, "date") else start_date
                    )

                    if item_date_only >= start_date_only:
                        # Для расчётов используем total_time если доступно, иначе duration_minutes
                        item_duration = item.get("total_time") or item.get(
                            "duration_minutes", 60
                        )
                        item_qty = item.get("quantity", 1)
                        item_parts_per_day = calculate_parts_per_day(item_duration)
                        item_days_needed = calculate_days_needed(
                            item_qty, item_parts_per_day
                        )

                        new_date = find_next_equipment_working_day(
                            current_date, equipment_id, eq_calendar, equipment
                        )

                        if new_date:
                            self.db.update_schedule_item(
                                schedule_id=item["id"],
                                planned_date=new_date,
                                is_manual_override=True,
                            )

                            new_end_date = add_equipment_working_days(
                                new_date,
                                item_days_needed,
                                equipment_id,
                                eq_calendar,
                                equipment,
                            )
                            current_date = new_end_date + timedelta(days=1)
                            shifted_count += 1

            return {"success": True, "shifted_count": shifted_count}

        except Exception as e:
            logger.error(f"Shift operations error: {e}")
            return {"success": False, "error": str(e)}

    def calculate_batch_schedule(
        self, order, start_date: datetime, priority: int = 3
    ) -> Dict:
        """Планирование с перекрытием для партийного производства

        Особенности:
        - Каждая операция работает со своим оборудованием
        - Вторая операция начинается когда первая сделает дневную норму
        - Операции перекрываются во времени, но детали идут последовательно

        Пример: 10 деталей, Op1=5 дет/день, Op2=5 дет/день
        День 1: Op1 делает 5
        День 2: Op1 делает 5, Op2 начинает делать 5 (из первых 5)
        День 3: Op2 заканчивает 5
        """
        if priority == URGENT_PRIORITY:
            return self._calculate_batch_schedule_urgent(order, start_date, priority)

        try:
            order_id = order.get("id")
            route_id = order.get("route_id")
            quantity = order.get("quantity", 1)

            from sqlalchemy import text
            from config import DATABASE_URL
            from sqlalchemy import create_engine

            engine = create_engine(DATABASE_URL)

            with engine.connect() as conn:
                ops_result = conn.execute(
                    text("""
                    SELECT
                        ro.id as route_operation_id,
                        ro.sequence_number,
                        ro.duration_minutes,
                        ro.prep_time,
                        ro.control_time,
                        ro.total_time,
                        ro.parts_count,
                        ro.notes,
                        ro.equipment_id as default_equipment_id,
                        ro.operation_type_id,
                        ro.is_cooperation,
                        ro.coop_duration_days,
                        ro.coop_position,
                        ro.coop_company_id,
                        ot.name as operation_name,
                        e.name as equipment_name,
                        e.id as equipment_id,
                        c.name as coop_company_name
                    FROM route_operations ro
                    LEFT JOIN operation_types ot ON ro.operation_type_id = ot.id
                    LEFT JOIN equipment e ON ro.equipment_id = e.id
                    LEFT JOIN cooperatives c ON ro.coop_company_id = c.id
                    WHERE ro.route_id = :route_id
                    ORDER BY ro.sequence_number
                """),
                    {"route_id": route_id},
                )
                ops = ops_result.fetchall()

            if not ops:
                return {"success": False, "message": "Нет операций в маршруте"}

            coop_start_days = 0
            coop_end_days = 0

            coop_sequences = []
            for op in ops:
                is_coop = bool(getattr(op, "is_cooperation", False))
                if is_coop:
                    coop_sequences.append(op.sequence_number)

            coop_min_seq = min(coop_sequences) if coop_sequences else None
            coop_max_seq = max(coop_sequences) if coop_sequences else None

            operations = []
            for op in ops:
                is_coop = bool(getattr(op, "is_cooperation", False))
                coop_duration = getattr(op, "coop_duration_days", 0) or 0

                if is_coop and coop_duration > 0:
                    if op.sequence_number == coop_min_seq:
                        coop_start_days += coop_duration
                    if op.sequence_number == coop_max_seq:
                        coop_end_days += coop_duration

                duration_min = op.duration_minutes or 60
                total_time = op.total_time or 60
                parts_count = op.parts_count or 1
                operations.append(
                    {
                        "route_operation_id": op.route_operation_id,
                        "sequence_number": op.sequence_number,
                        "duration_minutes": duration_min,
                        "prep_time": op.prep_time or 0,
                        "control_time": op.control_time or 0,
                        "total_time": total_time,
                        "parts_count": parts_count,
                        "operation_name": op.operation_name or "",
                        "equipment_id": op.equipment_id or op.default_equipment_id,
                        "equipment_name": op.equipment_name or "",
                        "notes": op.notes or "",
                        "parts_per_day": calculate_parts_per_day(total_time),
                        "operation_type_id": op.operation_type_id,
                        "is_cooperation": is_coop,
                        "coop_duration_days": coop_duration,
                        "coop_company_id": getattr(op, "coop_company_id", None),
                        "coop_company_name": getattr(op, "coop_company_name", "") or "",
                    }
                )

            # Coop_start_days используется только для расчёта сдвига итоговой даты окончания

            is_valid, error_msg = validate_schedule_data({"id": order_id}, operations)
            if not is_valid:
                return {"success": False, "message": error_msg}

            equipment = self.db.get_all_equipment(active_only=True)
            date_to = start_date + timedelta(days=365)
            calendar_data = self.db.get_all_equipment_calendar(start_date, date_to)

            equipment_calendars = {}
            for entry in calendar_data:
                eq_id = entry.get("equipment_id")
                if eq_id not in equipment_calendars:
                    equipment_calendars[eq_id] = {}
                date_key = entry.get("date")
                if isinstance(date_key, datetime):
                    date_key = date_key.strftime("%Y-%m-%d")
                equipment_calendars[eq_id][date_key] = entry

            # Предварительно рассчитываем даты окончания для срочных заказов
            urgent_end_dates = {}
            urgent_order_days = {}
            for op in operations:
                eq_id = op["equipment_id"]
                if not eq_id:
                    continue
                parts_per_day = op["parts_per_day"]
                total_time = op["total_time"]  # Для расчётов
                duration = op["duration_minutes"]  # Для UI
                days_needed = max(1, (quantity + parts_per_day - 1) // parts_per_day)
                parts_last_day = quantity - parts_per_day * (days_needed - 1)
                end_time_minutes = min(parts_last_day, parts_per_day) * total_time
                end_date = start_date + timedelta(days=days_needed - 1)
                urgent_end_dates[eq_id] = {
                    "date": end_date,
                    "end_time_minutes": end_time_minutes,
                    "operation_type_id": op.get("operation_type_id"),
                }

                urgent_order_days[eq_id] = []
                remaining = quantity
                current = start_date
                for d in range(days_needed):
                    parts_today = min(parts_per_day, remaining)
                    urgent_order_days[eq_id].append(
                        {
                            "date": current,
                            "occupied_minutes": parts_today * total_time,
                            "operation_type_id": op.get("operation_type_id"),
                        }
                    )
                    remaining -= parts_today
                    current = find_next_equipment_working_day(
                        current + timedelta(days=1),
                        eq_id,
                        equipment_calendars.get(eq_id, {}),
                        equipment,
                    )
                    if current is None:
                        break

            existing_schedule = self.db.get_production_schedule(
                date_from=start_date, date_to=date_to
            )
            all_scheduled_items = list(existing_schedule)

            schedule_items = []
            created_schedules = 0

            # Сколько деталей произвела каждая операция
            produced_by_op = [0] * len(operations)
            # Сколько деталей доступно для следующей операции (буфер)
            buffer_for_next_op = [0] * len(operations)
            # Дата когда каждая операция начала работать
            op_start_dates = [None] * len(operations)
            # Дата когда каждая операция может начаться (минимум следующий рабочий день после старта предыдущей)
            op_can_start_dates = [None] * len(operations)

            total_produced = 0
            current_date = start_date
            max_days = 365
            day_count = 0

            # Для проверки завершения - последняя операция должна обработать все детали
            last_op_idx = len(operations) - 1

            def get_next_working_day(
                from_date, equipment_id, eq_calendar, equipment_list
            ):
                """Найти следующий рабочий день для оборудования"""
                check_date = from_date
                for _ in range(365):
                    if is_working_day(check_date) and is_equipment_working_day(
                        check_date, equipment_id, eq_calendar, equipment_list
                    ):
                        return check_date
                    check_date += timedelta(days=1)
                return None

            # Сдвигаем операции с более низким приоритетом для срочного заказа
            shifted_count = 0
            if priority == URGENT_PRIORITY and (urgent_end_dates or urgent_order_days):
                shifted_count = self._shift_lower_priority_operations(
                    order_id,
                    urgent_end_dates,
                    urgent_order_days,
                    all_scheduled_items,
                    equipment_calendars,
                    equipment,
                )
                print(
                    f"DEBUG: Batch - shifted {shifted_count} operations for urgent order {order_id}"
                )
                print(f"DEBUG: Urgent ends: {urgent_end_dates}")

            # Цикл работает пока последняя операция не обработает все quantity деталей
            while produced_by_op[last_op_idx] < quantity and day_count < max_days:
                day_count += 1

                if not is_working_day(current_date):
                    current_date += timedelta(days=1)
                    continue

                scheduled_today = False

                # Обрабатываем операции по порядку
                for op_idx, op in enumerate(operations):
                    # Пропускаем кооперативные операции (у них нет оборудования)
                    if op.get("is_cooperation"):
                        continue

                    equipment_id = op["equipment_id"]
                    if not equipment_id:
                        continue

                    eq_calendar = equipment_calendars.get(equipment_id, {})

                    if not is_equipment_working_day(
                        current_date, equipment_id, eq_calendar, equipment
                    ):
                        continue

                    # Проверяем может ли операция начать работать
                    # Для первой операции - может работать сразу
                    # Для последующих - только если прошло минимум 1 рабочий день после начала предыдущей
                    if op_idx > 0:
                        # Вычисляем когда операция может начаться (следующий рабочий день после старта предыдущей)
                        if (
                            op_can_start_dates[op_idx] is None
                            and op_start_dates[op_idx - 1] is not None
                        ):
                            # Нашли когда предыдущая начала - считаем следующий рабочий день
                            next_day = op_start_dates[op_idx - 1] + timedelta(days=1)
                            op_can_start_dates[op_idx] = get_next_working_day(
                                next_day, equipment_id, eq_calendar, equipment
                            )

                        # Если ещё не можем начать - пропускаем этот день
                        if (
                            op_can_start_dates[op_idx]
                            and current_date < op_can_start_dates[op_idx]
                        ):
                            continue

                    parts_per_day = op["parts_per_day"]

                    if op_idx == 0:
                        # Первая операция: производит детали
                        can_produce = min(parts_per_day, quantity - total_produced)
                        if can_produce > 0:
                            # Запоминаем когда начали работать
                            if op_start_dates[op_idx] is None:
                                op_start_dates[op_idx] = current_date

                            # Производим детали
                            result = self.db.add_to_production_schedule(
                                order_id=order_id,
                                route_operation_id=op["route_operation_id"],
                                equipment_id=equipment_id,
                                planned_date=current_date,
                                quantity=can_produce,
                                priority=priority,
                                duration_minutes=op["duration_minutes"],
                                status="planned",
                            )

                            if result:
                                created_schedules += 1
                                produced_by_op[op_idx] += can_produce
                                buffer_for_next_op[op_idx] += can_produce
                                total_produced += can_produce
                                scheduled_today = True

                                schedule_items.append(
                                    {
                                        "date": current_date.strftime("%Y-%m-%d"),
                                        "datetime": current_date,
                                        "equipment_id": equipment_id,
                                        "equipment_name": op["equipment_name"],
                                        "operation_name": op["operation_name"],
                                        "operation_seq": op["sequence_number"],
                                        "parts": can_produce,
                                        "parts_per_day": parts_per_day,
                                        "is_batch": True,
                                        "is_production": True,
                                    }
                                )
                    else:
                        # Последующие операции: обрабатывают детали из буфера предыдущей
                        available = buffer_for_next_op[op_idx - 1]

                        # Запоминаем когда начали работать
                        if op_start_dates[op_idx] is None and available > 0:
                            op_start_dates[op_idx] = current_date

                        can_process = min(
                            parts_per_day, available, quantity - produced_by_op[op_idx]
                        )

                        if can_process > 0:
                            result = self.db.add_to_production_schedule(
                                order_id=order_id,
                                route_operation_id=op["route_operation_id"],
                                equipment_id=equipment_id,
                                planned_date=current_date,
                                quantity=can_process,
                                priority=priority,
                                duration_minutes=op["duration_minutes"],
                                status="planned",
                            )

                            if result:
                                created_schedules += 1
                                produced_by_op[op_idx] += can_process
                                buffer_for_next_op[op_idx] += can_process
                                buffer_for_next_op[op_idx - 1] -= can_process
                                scheduled_today = True

                                schedule_items.append(
                                    {
                                        "date": current_date.strftime("%Y-%m-%d"),
                                        "datetime": current_date,
                                        "equipment_id": equipment_id,
                                        "equipment_name": op["equipment_name"],
                                        "operation_name": op["operation_name"],
                                        "operation_seq": op["sequence_number"],
                                        "parts": can_process,
                                        "parts_per_day": parts_per_day,
                                        "is_batch": True,
                                        "is_production": False,
                                    }
                                )

                # Если ничего не запланировали и ещё не всё произведено
                if not scheduled_today and total_produced < quantity:
                    current_date += timedelta(days=1)
                    continue

                current_date += timedelta(days=1)

            if schedule_items:
                first_item = schedule_items[0]
                start_str = (
                    first_item.get("datetime").strftime("%d.%m.%Y")
                    if first_item.get("datetime")
                    else (first_item.get("planned_date") or "")
                )
                end_str = (
                    schedule_items[-1].get("datetime").strftime("%d.%m.%Y")
                    if schedule_items[-1].get("datetime")
                    else (schedule_items[-1].get("end_date") or "")
                )
            else:
                start_str = ""
                end_str = ""

            if coop_end_days > 0 and end_str:
                end_dt = datetime.strptime(end_str, "%d.%m.%Y")
                end_dt = end_dt + timedelta(days=coop_end_days)
                end_str = end_dt.strftime("%d.%m.%Y")

            self.db.update_order_dates(order_id, start_str, end_str)

            shifted_msg = (
                f", сдвинуто {shifted_count} операций" if shifted_count > 0 else ""
            )
            return {
                "success": True,
                "schedule": schedule_items,
                "start_date": start_str,
                "end_date": end_str,
                "message": f"Запланировано {created_schedules} записей (партийное){shifted_msg}",
            }

        except Exception as e:
            logger.error(f"Batch schedule error: {e}")
            import traceback

            traceback.print_exc()
            return {"success": False, "message": str(e)}

    def _calculate_batch_schedule_urgent(
        self, order, start_date: datetime, priority: int = 1
    ) -> Dict:
        """Планирование срочного заказа (партийное) с переносом не срочных.

        Алгоритм:
        1. Получить equipment_ids из маршрута срочного заказа
        2. Найти и удалить все не срочные операции на этих станках после start_date
        3. Запланировать срочный заказ
        4. Перепланировать удалённые не срочные заказы
        """
        try:
            order_id = order.get("id")
            route_id = order.get("route_id")

            print(
                f"DEBUG _calculate_batch_schedule_urgent: order_id={order_id}, start_date={start_date}"
            )

            urgent_equipment_ids = self._get_route_equipment_ids(route_id)
            print(
                f"DEBUG _calculate_batch_schedule_urgent: equipment_ids={urgent_equipment_ids}"
            )

            removed_orders = self._collect_and_remove_non_urgent_after_date(
                start_date,
                urgent_equipment_ids,
            )

            equipment = self.db.get_all_equipment(active_only=True)
            date_to = start_date + timedelta(days=365)
            calendar_data = self.db.get_all_equipment_calendar(start_date, date_to)

            equipment_calendars = {}
            for entry in calendar_data:
                eq_id = entry.get("equipment_id")
                if eq_id not in equipment_calendars:
                    equipment_calendars[eq_id] = {}
                date_key = entry.get("date")
                if isinstance(date_key, datetime):
                    date_key = date_key.strftime("%Y-%m-%d")
                equipment_calendars[eq_id][date_key] = entry

            existing_schedule = self.db.get_production_schedule(
                date_from=start_date - timedelta(days=30),
                date_to=date_to,
            )
            all_scheduled_items = [
                item for item in existing_schedule if item.get("order_id") != order_id
            ]

            self.db.clear_order_schedule(order_id)

            result = self.calculate_batch_schedule_with_items(
                order,
                start_date,
                priority,
                all_scheduled_items,
                equipment_calendars,
                equipment,
            )

            print(f"DEBUG _calculate_batch_schedule_urgent: schedule result = {result}")

            if result.get("success"):
                schedule_items = result.get("schedule", [])
                print(
                    f"DEBUG _calculate_batch_schedule_urgent: schedule_items count = {len(schedule_items)}"
                )

                urgent_end_dates = {}
                for item in schedule_items:
                    eq_id = item.get("equipment_id")
                    planned_date = item.get("datetime")
                    eq_name = item.get("equipment_name", "")
                    if eq_id and planned_date:
                        if (
                            eq_id not in urgent_end_dates
                            or planned_date > urgent_end_dates[eq_id]["date"]
                        ):
                            urgent_end_dates[eq_id] = {
                                "date": planned_date,
                                "name": eq_name,
                            }

                print(
                    f"DEBUG _calculate_batch_schedule_urgent: urgent_end_dates={urgent_end_dates}"
                )

                rescheduled_count = self._reschedule_removed_orders(
                    removed_orders,
                    urgent_end_dates,
                    equipment_calendars,
                    equipment,
                )

                result["shifted_orders"] = rescheduled_count
                if rescheduled_count > 0:
                    result["message"] += f" (перенесено {rescheduled_count} заказов)"
            else:
                print(
                    f"DEBUG _calculate_batch_schedule_urgent: scheduling FAILED - {result.get('message')}"
                )

            return result

        except Exception as e:
            logger.error(f"Batch schedule urgent error: {e}")
            import traceback

            traceback.print_exc()
            return {"success": False, "message": str(e)}

    def calculate_batch_schedule_with_items(
        self,
        order,
        start_date: datetime,
        priority: int,
        all_scheduled_items: List[Dict],
        equipment_calendars: Dict,
        equipment: List[Dict],
    ) -> Dict:
        """Партийное планирование с предварительно подготовленным расписанием.

        Отличается от calculate_batch_schedule тем, что:
        - Принимает all_scheduled_items как параметр (не получает из БД)
        - Не вызывает _shift_lower_priority_operations
        """
        try:
            order_id = order.get("id")
            route_id = order.get("route_id")
            quantity = order.get("quantity", 1)

            from sqlalchemy import text
            from config import DATABASE_URL
            from sqlalchemy import create_engine

            engine = create_engine(DATABASE_URL)

            with engine.connect() as conn:
                ops_result = conn.execute(
                    text("""
                    SELECT 
                        ro.id as route_operation_id,
                        ro.sequence_number, 
                        ro.duration_minutes, 
                        ro.notes,
                        ro.equipment_id as default_equipment_id,
                        ro.operation_type_id,
                        ro.is_cooperation,
                        ro.coop_duration_days,
                        ro.coop_position,
                        ro.coop_company_id,
                        ot.name as operation_name,
                        e.name as equipment_name,
                        e.id as equipment_id,
                        c.name as coop_company_name
                    FROM route_operations ro
                    LEFT JOIN operation_types ot ON ro.operation_type_id = ot.id
                    LEFT JOIN equipment e ON ro.equipment_id = e.id
                    LEFT JOIN cooperatives c ON ro.coop_company_id = c.id
                    WHERE ro.route_id = :route_id
                    ORDER BY ro.sequence_number
                """),
                    {"route_id": route_id},
                )
                ops = ops_result.fetchall()

            if not ops:
                return {"success": False, "message": "Нет операций в маршруте"}

            coop_start_days = 0
            coop_end_days = 0

            coop_sequences = []
            for op in ops:
                is_coop = bool(getattr(op, "is_cooperation", False))
                if is_coop:
                    coop_sequences.append(op.sequence_number)

            coop_min_seq = min(coop_sequences) if coop_sequences else None
            coop_max_seq = max(coop_sequences) if coop_sequences else None

            operations = []
            for op in ops:
                is_coop = bool(getattr(op, "is_cooperation", False))
                coop_duration = getattr(op, "coop_duration_days", 0) or 0

                if is_coop and coop_duration > 0:
                    if op.sequence_number == coop_min_seq:
                        coop_start_days += coop_duration
                    if op.sequence_number == coop_max_seq:
                        coop_end_days += coop_duration

                duration_min = op.duration_minutes or 60
                total_time = op.total_time or 60
                parts_count = op.parts_count or 1
                is_coop = bool(getattr(op, "is_cooperation", False))
                operations.append(
                    {
                        "route_operation_id": op.route_operation_id,
                        "sequence_number": op.sequence_number,
                        "duration_minutes": duration_min,
                        "prep_time": op.prep_time or 0,
                        "control_time": op.control_time or 0,
                        "total_time": total_time,
                        "parts_count": parts_count,
                        "operation_name": op.operation_name or "",
                        "equipment_id": op.equipment_id or op.default_equipment_id,
                        "equipment_name": op.equipment_name or "",
                        "notes": op.notes or "",
                        "parts_per_day": calculate_parts_per_day(total_time),
                        "operation_type_id": op.operation_type_id,
                        "is_cooperation": is_coop,
                        "coop_duration_days": coop_duration,
                        "coop_company_id": getattr(op, "coop_company_id", None),
                        "coop_company_name": getattr(op, "coop_company_name", "") or "",
                    }
                )

            # Coop_start_days используется только для расчёта сдвига итоговой даты окончания

            is_valid, error_msg = validate_schedule_data({"id": order_id}, operations)
            if not is_valid:
                return {"success": False, "message": error_msg}

            print(
                f"DEBUG calculate_batch_schedule_with_items: order_id={order_id}, start_date={start_date}, priority={priority}"
            )

            schedule_items = []
            created_schedules = 0

            produced_by_op = [0] * len(operations)
            buffer_for_next_op = [0] * len(operations)
            op_start_dates = [None] * len(operations)
            op_can_start_dates = [None] * len(operations)

            total_produced = 0
            current_date = start_date
            max_days = 365
            day_count = 0

            last_op_idx = len(operations) - 1

            def get_next_working_day(
                from_date, equipment_id, eq_calendar, equipment_list
            ):
                check_date = from_date
                for _ in range(365):
                    if is_working_day(check_date) and is_equipment_working_day(
                        check_date, equipment_id, eq_calendar, equipment_list
                    ):
                        return check_date
                    check_date += timedelta(days=1)
                return None

            while produced_by_op[last_op_idx] < quantity and day_count < max_days:
                day_count += 1

                if not is_working_day(current_date):
                    current_date += timedelta(days=1)
                    continue

                scheduled_today = False

                for op_idx, op in enumerate(operations):
                    # Пропускаем кооперативные операции (у них нет оборудования)
                    if op.get("is_cooperation"):
                        continue

                    equipment_id = op["equipment_id"]
                    if not equipment_id:
                        continue

                    eq_calendar = equipment_calendars.get(equipment_id, {})

                    if not is_equipment_working_day(
                        current_date, equipment_id, eq_calendar, equipment
                    ):
                        continue

                    if op_idx > 0:
                        if (
                            op_can_start_dates[op_idx] is None
                            and op_start_dates[op_idx - 1] is not None
                        ):
                            next_day = op_start_dates[op_idx - 1] + timedelta(days=1)
                            op_can_start_dates[op_idx] = get_next_working_day(
                                next_day, equipment_id, eq_calendar, equipment
                            )

                        if (
                            op_can_start_dates[op_idx]
                            and current_date < op_can_start_dates[op_idx]
                        ):
                            continue

                    parts_per_day = op["parts_per_day"]

                    if op_idx == 0:
                        can_produce = min(parts_per_day, quantity - total_produced)
                        if can_produce > 0:
                            if op_start_dates[op_idx] is None:
                                op_start_dates[op_idx] = current_date

                            result = self.db.add_to_production_schedule(
                                order_id=order_id,
                                route_operation_id=op["route_operation_id"],
                                equipment_id=equipment_id,
                                planned_date=current_date,
                                quantity=can_produce,
                                priority=priority,
                                duration_minutes=op["duration_minutes"],
                                status="planned",
                            )

                            if result:
                                created_schedules += 1
                                total_produced += can_produce
                                produced_by_op[op_idx] += can_produce
                                buffer_for_next_op[op_idx] += can_produce
                                scheduled_today = True

                                schedule_items.append(
                                    {
                                        "date": current_date.strftime("%Y-%m-%d"),
                                        "datetime": current_date,
                                        "equipment_id": equipment_id,
                                        "equipment_name": op["equipment_name"],
                                        "operation_name": op["operation_name"],
                                        "operation_seq": op["sequence_number"],
                                        "parts": can_produce,
                                        "parts_per_day": parts_per_day,
                                        "is_batch": True,
                                        "is_production": True,
                                    }
                                )

                                new_item = {
                                    "planned_date": current_date,
                                    "equipment_id": equipment_id,
                                    "quantity": can_produce,
                                    "duration_minutes": op["duration_minutes"],
                                    "priority": priority,
                                    "order_id": order_id,
                                }
                                all_scheduled_items.append(new_item)

                    else:
                        available_buffer = buffer_for_next_op[op_idx]
                        can_process = min(parts_per_day, available_buffer)

                        if can_process > 0:
                            result = self.db.add_to_production_schedule(
                                order_id=order_id,
                                route_operation_id=op["route_operation_id"],
                                equipment_id=equipment_id,
                                planned_date=current_date,
                                quantity=can_process,
                                priority=priority,
                                duration_minutes=op["duration_minutes"],
                                status="planned",
                            )

                            if result:
                                created_schedules += 1
                                produced_by_op[op_idx] += can_process
                                buffer_for_next_op[op_idx] += can_process
                                buffer_for_next_op[op_idx - 1] -= can_process
                                scheduled_today = True

                                schedule_items.append(
                                    {
                                        "date": current_date.strftime("%Y-%m-%d"),
                                        "datetime": current_date,
                                        "equipment_id": equipment_id,
                                        "equipment_name": op["equipment_name"],
                                        "operation_name": op["operation_name"],
                                        "operation_seq": op["sequence_number"],
                                        "parts": can_process,
                                        "parts_per_day": parts_per_day,
                                        "is_batch": True,
                                        "is_production": False,
                                    }
                                )

                                new_item = {
                                    "planned_date": current_date,
                                    "equipment_id": equipment_id,
                                    "quantity": can_process,
                                    "duration_minutes": op["duration_minutes"],
                                    "priority": priority,
                                    "order_id": order_id,
                                }
                                all_scheduled_items.append(new_item)

                if not scheduled_today and total_produced < quantity:
                    current_date += timedelta(days=1)
                    continue

                current_date += timedelta(days=1)

            # Coop_start_days используется только для расчёта сдвига итоговой даты окончания

            if schedule_items:
                first_item = schedule_items[0]
                start_str = (
                    first_item.get("datetime").strftime("%d.%m.%Y")
                    if first_item.get("datetime")
                    else (first_item.get("planned_date") or "")
                )
                end_str = (
                    schedule_items[-1].get("datetime").strftime("%d.%m.%Y")
                    if schedule_items[-1].get("datetime")
                    else (schedule_items[-1].get("end_date") or "")
                )
            else:
                start_str = ""
                end_str = ""

            if coop_end_days > 0 and end_str:
                end_dt = datetime.strptime(end_str, "%d.%m.%Y")
                end_dt = end_dt + timedelta(days=coop_end_days)
                end_str = end_dt.strftime("%d.%m.%Y")

            self.db.update_order_dates(order_id, start_str, end_str)

            return {
                "success": True,
                "schedule": schedule_items,
                "start_date": start_str,
                "end_date": end_str,
                "message": f"Запланировано {created_schedules} записей (партийное)",
            }

        except Exception as e:
            logger.error(f"Batch schedule with items error: {e}")
            import traceback

            traceback.print_exc()
            return {"success": False, "message": str(e)}

    def reschedule_operation(self, schedule_id: int, new_date: datetime) -> bool:
        """Перенести операцию на другую дату"""
        try:
            self.db.update_schedule_item(
                schedule_id=schedule_id, planned_date=new_date, is_manual_override=True
            )
            return True
        except Exception as e:
            logger.error(f"Reschedule operation error: {e}")
            return False

    def get_gantt_data(self, date_from: datetime, date_to: datetime) -> List[Dict]:
        """Получить данные для диаграммы Ганта"""
        try:
            schedule = self.db.get_production_schedule(
                date_from=date_from, date_to=date_to
            )

            equipment = self.db.get_all_equipment(active_only=False)
            equipment_map = {eq["id"]: eq["name"] for eq in equipment}

            gantt_data = []

            for item in schedule:
                planned_date = item.get("planned_date")
                if isinstance(planned_date, str):
                    planned_date = datetime.strptime(planned_date, "%Y-%m-%d")

                # Для расчётов используем total_time если доступно, иначе duration_minutes
                duration = item.get("total_time") or item.get("duration_minutes", 60)
                qty = item.get("quantity", 1)

                hours_per_day = WORKING_HOURS_PER_DAY
                eq_id = item.get("equipment_id")
                if eq_id:
                    hours_per_day = (
                        self.get_equipment_working_hours(eq_id, planned_date)
                        if planned_date
                        else WORKING_HOURS_PER_DAY
                    )

                minutes_needed = calculate_total_minutes(duration, qty)
                days_needed = calculate_duration_days(minutes_needed, hours_per_day)

                equipment_name = equipment_map.get(
                    eq_id, item.get("equipment_name", "Unknown")
                )

                parts_per_day = calculate_parts_per_day(duration)
                days_count = calculate_days_needed(qty, parts_per_day)

                gantt_data.append(
                    {
                        "id": item["id"],
                        "order_id": item["order_id"],
                        "designation": item.get("designation", ""),
                        "detail_name": item.get("detail_name", ""),
                        "operation_name": item.get("operation_name", ""),
                        "equipment_id": eq_id,
                        "equipment_name": equipment_name,
                        "planned_date": planned_date.strftime("%Y-%m-%d")
                        if planned_date
                        else None,
                        "duration_days": days_count,
                        "quantity": qty,
                        "parts_per_day": parts_per_day,
                        "status": item.get("status", "planned"),
                        "priority": item.get("priority", DEFAULT_PRIORITY),
                    }
                )

            return gantt_data

        except Exception as e:
            logger.error(f"Get gantt data error: {e}")
            return []

    def get_calendar_data(self, date_from: datetime, date_to: datetime) -> List[Dict]:
        """Получить данные для календаря с разбивкой по дням

        Возвращает записи для каждого рабочего дня с количеством деталей.
        """
        try:
            schedule = self.db.get_production_schedule(
                date_from=date_from, date_to=date_to
            )

            equipment = self.db.get_all_equipment(active_only=False)
            equipment_map = {eq["id"]: eq["name"] for eq in equipment}

            calendar_data = []

            for item in schedule:
                planned_date = item.get("planned_date")
                if isinstance(planned_date, str):
                    planned_date = datetime.strptime(planned_date, "%Y-%m-%d")

                if not planned_date:
                    continue

                # Для расчётов используем total_time если доступно, иначе duration_minutes
                duration = item.get("total_time") or item.get("duration_minutes", 60)
                qty = item.get("quantity", 1)
                eq_id = item.get("equipment_id")
                equipment_name = equipment_map.get(
                    eq_id, item.get("equipment_name", "Unknown")
                )

                parts_per_day = calculate_parts_per_day(duration)
                days_count = calculate_days_needed(qty, parts_per_day)

                current_date = planned_date
                parts_remaining = qty

                while parts_remaining > 0:
                    if not is_working_day(current_date):
                        current_date += timedelta(days=1)
                        continue

                    if current_date > date_to:
                        break

                    parts_today = min(parts_remaining, parts_per_day)

                    calendar_data.append(
                        {
                            "schedule_id": item["id"],
                            "order_id": item["order_id"],
                            "designation": item.get("designation", ""),
                            "detail_name": item.get("detail_name", ""),
                            "operation_name": item.get("operation_name", ""),
                            "batch_number": item.get("batch_number", ""),
                            "production_type": item.get("production_type", ""),
                            "equipment_id": eq_id,
                            "equipment_name": equipment_name,
                            "planned_date": current_date.strftime("%Y-%m-%d"),
                            "quantity": parts_today,
                            "total_quantity": qty,
                            "parts_per_day": parts_per_day,
                            "duration_minutes": duration,
                            "status": item.get("status", "planned"),
                            "priority": item.get("priority", DEFAULT_PRIORITY),
                        }
                    )

                    parts_remaining -= parts_today
                    current_date += timedelta(days=1)

            return calendar_data

        except Exception as e:
            logger.error(f"Get calendar data error: {e}")
            import traceback

            traceback.print_exc()
            return []

    def get_equipment_timeline(
        self, equipment_id: int, date_from: datetime, date_to: datetime
    ) -> List[Dict]:
        """Получить timeline для конкретного станка"""
        try:
            schedule = self.db.get_production_schedule(
                date_from=date_from, date_to=date_to, equipment_id=equipment_id
            )

            timeline = []
            current_date = date_from

            while current_date <= date_to:
                day_schedule = []
                hours_available = self.get_equipment_working_hours(
                    equipment_id, current_date
                )

                for item in schedule:
                    planned_date = item.get("planned_date")
                    if isinstance(planned_date, str):
                        planned_date = datetime.strptime(planned_date, "%Y-%m-%d")

                    if planned_date and planned_date.date() == current_date.date():
                        day_schedule.append(item)

                timeline.append(
                    {
                        "date": current_date.strftime("%Y-%m-%d"),
                        "is_working": hours_available > 0,
                        "working_hours": hours_available,
                        "schedule": day_schedule,
                    }
                )

                current_date += timedelta(days=1)

            return timeline

        except Exception as e:
            logger.error(f"Get equipment timeline error: {e}")
            return []

    def check_conflicts(self, date_from: datetime, date_to: datetime) -> List[Dict]:
        """Проверить конфликты (перегрузка станков)"""
        try:
            equipment = self.db.get_all_equipment(active_only=False)
            conflicts = []

            for eq in equipment:
                eq_id = eq["id"]
                load = self.get_equipment_load(eq_id, date_from, date_to)

                if load["utilization_percent"] > 100:
                    conflicts.append(
                        {
                            "equipment_id": eq_id,
                            "equipment_name": eq["name"],
                            "utilization_percent": load["utilization_percent"],
                            "overload_minutes": load["total_scheduled_minutes"]
                            - load["total_available_minutes"],
                        }
                    )

            return conflicts

        except Exception as e:
            logger.error(f"Check conflicts error: {e}")
            return []

    def auto_rebalance(self, date: datetime = None) -> Dict:
        """Автоматическое перепланирование при конфликтах"""
        if date is None:
            date = datetime.now()

        date_from = date
        date_to = date + timedelta(days=30)

        conflicts = self.check_conflicts(date_from, date_to)

        if not conflicts:
            return {"success": True, "message": "Конфликтов нет"}

        rebalanced = 0
        for conflict in conflicts:
            logger.info(
                f"Conflict on {conflict['equipment_name']}: {conflict['utilization_percent']}%"
            )

        return {
            "success": True,
            "conflicts": conflicts,
            "message": f"Найдено {len(conflicts)} конфликтов. Требуется ручное перепланирование.",
        }

    def update_schedule_status(self, schedule_id: int, status: str) -> bool:
        """Обновить статус операции"""
        try:
            self.db.update_schedule_item(schedule_id=schedule_id, status=status)
            return True
        except Exception as e:
            logger.error(f"Update schedule status error: {e}")
            return False
