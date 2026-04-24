# qr_scanner_handler.py
"""
Обработчик QR-кодов для мобильного FastAPI приложения

QR-код содержит URL формата: sklad://order/{order_id}?route={route_id}

Использование:
1. При сканировании QR вызывается parse_qr_url(url)
2. Возвращает информацию о заказе и операциях
3. Для отметки используются take_order / complete_order
"""

from typing import Optional, Dict, List
from datetime import datetime
import logging
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger(__name__)


class QRScannerHandler:
    """Обработчик QR-кодов для производственного отслеживания"""

    def __init__(self, db_manager):
        self.db = db_manager

    def parse_qr_url(self, url: str) -> Optional[Dict]:
        """
        Парсит URL из QR-кода

        Args:
            url: URL вида sklad://order/42?route=15
                 или sklad://42?route=15

        Returns:
            dict с order_id и route_id или None если ошибка
        """
        try:
            url = url.strip()
            parsed = urlparse(url)

            if parsed.scheme != "sklad":
                logger.warning(f"Unknown URL scheme: {parsed.scheme}")
                return None

            # URLparse interprets 'order' as netloc for custom schemes
            # So we need to handle both cases:
            # 1. sklad://order/42?route=15 -> netloc='order', path='/42'
            # 2. sklad://42?route=15 -> netloc='42', no path

            order_id = None
            if parsed.netloc:
                # Case 1: sklad://order/42?route=15
                if parsed.netloc == 'order' and parsed.path:
                    order_id_str = parsed.path.strip('/').split('/')[-1]
                    order_id = int(order_id_str) if order_id_str else None
                else:
                    # Case 2: sklad://42?route=15 (shorthand)
                    order_id = int(parsed.netloc)
            elif parsed.path:
                # Fallback: sklad://42?route=15
                order_id_str = parsed.path.strip('/')
                order_id = int(order_id_str) if order_id_str else None

            if order_id is None:
                logger.warning(f"Could not extract order_id from URL: {url}")
                return None

            params = parse_qs(parsed.query)
            route_id = int(params.get("route", [0])[0]) if params.get("route") else None

            return {"order_id": order_id, "route_id": route_id, "raw_url": url}
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid QR URL format: {url} - {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing QR URL: {e}")
            return None

    def get_order_info(self, order_id: int) -> Optional[Dict]:
        """
        Получает информацию о заказе из базы данных

        Returns:
            dict с данными заказа или None
        """
        try:
            order = self.db.get_order(order_id)
            if not order:
                return None

            # Determine status display
            status = order.get("status", "")
            in_progress = order.get("in_progress", False)

            if in_progress:
                status_display = "В работе"
            elif status == "completed":
                status_display = "Завершён"
            elif status == "cancelled":
                status_display = "Отменён"
            else:
                status_display = "Запланирован"

            production_type = order.get("production_type", "piece")
            production_type_display = "Штучное" if production_type == "piece" else "Партийное"

            return {
                "id": order.get("id"),
                "designation": order.get("designation", ""),
                "detail_name": order.get("detail_name", ""),
                "quantity": order.get("quantity", 0),
                "batch_number": order.get("batch_number", ""),
                "production_type": production_type,
                "production_type_display": production_type_display,
                "status": status,
                "status_display": status_display,
                "in_progress": in_progress,
                "start_date": self._format_date(order.get("start_date")),
                "end_date": self._format_date(order.get("end_date")),
                "created_by": order.get("created_by", ""),
                "order_number": order.get("order_number", ""),
                "route_id": order.get("route_id"),
            }
        except Exception as e:
            logger.error(f"Error getting order info: {e}")
            return None

    def get_schedule_for_qr(self, order_id: int) -> List[Dict]:
        """
        Получает расписание для заказа (операции с датами)

        Returns:
            list операций с информацией о выполнении
        """
        try:
            schedule = self.db.get_production_schedule(order_id=order_id)

            result = []
            for item in schedule:
                tracking = self.db.get_schedule_tracking_stats(item.get("id"))

                taken_at = tracking.get("taken_at") if tracking else None
                completed_at = tracking.get("completed_at") if tracking else None

                result.append({
                    "id": item.get("id"),
                    "sequence_number": item.get("sequence_number", 0),
                    "operation_name": item.get("operation_name", ""),
                    "equipment_name": item.get("equipment_name", ""),
                    "planned_date": self._format_date(item.get("planned_date")),
                    "actual_date": self._format_date(item.get("actual_date")),
                    "quantity": item.get("quantity", 0),
                    "duration_minutes": item.get("duration_minutes", 0),
                    "status": item.get("status", "planned"),
                    "taken_at": self._format_datetime(taken_at),
                    "taken_by": tracking.get("taken_by") if tracking else None,
                    "completed_at": self._format_datetime(completed_at),
                    "completed_by": tracking.get("completed_by") if tracking else None,
                    "avg_time_per_unit": tracking.get("avg_time_per_unit") if tracking else None,
                    "is_taken": taken_at is not None,
                    "is_completed": completed_at is not None,
                })

            return result
        except Exception as e:
            logger.error(f"Error getting schedule: {e}")
            return []

    def take_order(self, order_id: int, user: str) -> Dict:
        """
        Отметить заказ как взятый в работу

        Args:
            order_id: ID заказа
            user: имя пользователя

        Returns:
            dict с результатом операции
        """
        try:
            order = self.db.get_order(order_id)
            if not order:
                return {"success": False, "error": "Заказ не найден"}

            if order.get("in_progress"):
                return {"success": False, "error": "Заказ уже взят в работу", "already_taken": True}

            if order.get("status") == "completed":
                return {"success": False, "error": "Заказ уже завершён", "already_completed": True}

            # Update order status
            with self.db.get_session() as session:
                from sqlalchemy import text
                session.execute(
                    text("UPDATE orders SET in_progress = true, status = 'in_progress' WHERE id = :id"),
                    {"id": order_id}
                )
                session.commit()

            # Mark all schedule items as taken
            schedule = self.db.get_production_schedule(order_id=order_id)
            taken_count = 0
            for item in schedule:
                schedule_id = item.get("id")
                if schedule_id:
                    self.db.mark_schedule_taken(schedule_id, user)
                    taken_count += 1

            logger.info(f"Order {order_id} taken by {user}, {taken_count} schedule items marked")

            return {
                "success": True,
                "message": f"Заказ #{order_id} взят в работу",
                "order_id": order_id,
                "schedule_items_count": taken_count,
                "taken_at": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.error(f"Error taking order: {e}")
            return {"success": False, "error": f"Ошибка: {str(e)}"}

    def complete_order(self, order_id: int, user: str) -> Dict:
        """
        Отметить заказ как завершённый

        Args:
            order_id: ID заказа
            user: имя пользователя

        Returns:
            dict с результатом операции и статистикой
        """
        try:
            order = self.db.get_order(order_id)
            if not order:
                return {"success": False, "error": "Заказ не найден"}

            if not order.get("in_progress"):
                return {"success": False, "error": "Заказ ещё не взят в работу"}

            if order.get("status") == "completed":
                return {"success": False, "error": "Заказ уже завершён", "already_completed": True}

            # Update order status
            with self.db.get_session() as session:
                from sqlalchemy import text
                session.execute(
                    text("UPDATE orders SET status = 'completed', in_progress = false WHERE id = :id"),
                    {"id": order_id}
                )
                session.commit()

            # Mark all schedule items as completed
            schedule = self.db.get_production_schedule(order_id=order_id)
            completed_count = 0
            total_time_seconds = 0
            total_quantity = 0

            for item in schedule:
                schedule_id = item.get("id")
                if schedule_id:
                    tracking = self.db.get_schedule_tracking_stats(schedule_id)
                    if tracking and tracking.get("taken_at") and not tracking.get("completed_at"):
                        self.db.mark_schedule_completed(schedule_id, user)
                        completed_count += 1

                        # Calculate time for this item
                        item_qty = item.get("quantity", 0) or 0
                        if tracking.get("taken_at"):
                            elapsed = (datetime.utcnow() - tracking["taken_at"]).total_seconds()
                            total_time_seconds += elapsed * item_qty if item_qty > 0 else elapsed
                            total_quantity += item_qty if item_qty > 0 else 1
                    elif tracking and tracking.get("completed_at"):
                        completed_count += 1

            # Calculate overall stats
            avg_time_per_unit = None
            if total_quantity > 0:
                avg_time_per_unit = total_time_seconds / total_quantity

            logger.info(f"Order {order_id} completed by {user}, {completed_count} items completed")

            return {
                "success": True,
                "message": f"Заказ #{order_id} завершён",
                "order_id": order_id,
                "completed_items_count": completed_count,
                "completed_at": datetime.utcnow().isoformat(),
                "avg_time_per_unit_seconds": avg_time_per_unit,
                "avg_time_per_unit_minutes": avg_time_per_unit / 60 if avg_time_per_unit else None,
            }
        except Exception as e:
            logger.error(f"Error completing order: {e}")
            return {"success": False, "error": f"Ошибка: {str(e)}"}

    def get_order_status(self, order_id: int) -> Dict:
        """
        Получить статус заказа и статистику

        Returns:
            dict с полной информацией о статусе
        """
        try:
            order = self.db.get_order(order_id)
            if not order:
                return {"success": False, "error": "Заказ не найден"}

            schedule = self.db.get_production_schedule(order_id=order_id)

            total_operations = len(schedule)
            completed_operations = 0
            taken_operations = 0
            total_time_seconds = 0
            total_quantity = 0

            for item in schedule:
                tracking = self.db.get_schedule_tracking_stats(item.get("id"))
                if tracking:
                    if tracking.get("taken_at"):
                        taken_operations += 1
                    if tracking.get("completed_at"):
                        completed_operations += 1

                    if tracking.get("taken_at") and tracking.get("completed_at"):
                        item_qty = item.get("quantity", 0) or 1
                        elapsed = (tracking["completed_at"] - tracking["taken_at"]).total_seconds()
                        total_time_seconds += elapsed * item_qty
                        total_quantity += item_qty

            progress_percent = 0
            if total_operations > 0:
                progress_percent = round(completed_operations / total_operations * 100, 1)

            avg_time_per_unit = None
            if total_quantity > 0:
                avg_time_per_unit = total_time_seconds / total_quantity

            in_progress = order.get("in_progress", False)
            status = order.get("status", "")

            if in_progress:
                status_display = "В работе"
            elif status == "completed":
                status_display = "Завершён"
            elif status == "cancelled":
                status_display = "Отменён"
            else:
                status_display = "Запланирован"

            return {
                "success": True,
                "order_id": order_id,
                "designation": order.get("designation", ""),
                "detail_name": order.get("detail_name", ""),
                "quantity": order.get("quantity", 0),
                "batch_number": order.get("batch_number", ""),
                "status": status,
                "status_display": status_display,
                "in_progress": in_progress,
                "total_operations": total_operations,
                "taken_operations": taken_operations,
                "completed_operations": completed_operations,
                "progress_percent": progress_percent,
                "total_time_seconds": total_time_seconds,
                "avg_time_per_unit_seconds": avg_time_per_unit,
                "avg_time_per_unit_minutes": avg_time_per_unit / 60 if avg_time_per_unit else None,
            }
        except Exception as e:
            logger.error(f"Error getting order status: {e}")
            return {"success": False, "error": f"Ошибка: {str(e)}"}

    def get_route_info(self, route_id: int) -> Dict:
        """
        Получить информацию о маршруте

        Returns:
            dict с информацией о маршруте
        """
        try:
            with self.db.get_session() as session:
                from sqlalchemy import text
                result = session.execute(
                    text("""
                        SELECT dr.id, dr.designation, dr.detail_name, dr.description,
                               mi.mark_name, mi.sortament_name,
                               (SELECT COUNT(*) FROM route_operations WHERE route_id = dr.id) as operations_count
                        FROM detail_routes dr
                        LEFT JOIN material_instances mi ON dr.material_instance_id = mi.id
                        WHERE dr.id = :route_id
                    """),
                    {"route_id": route_id}
                )
                row = result.fetchone()

                if not row:
                    return {"success": False, "error": "Маршрут не найден"}

                return {
                    "success": True,
                    "id": row[0],
                    "designation": row[1] or "",
                    "detail_name": row[2] or "",
                    "description": row[3] or "",
                    "mark_name": row[4] or "",
                    "sortament_name": row[5] or "",
                    "operations_count": row[6] or 0,
                }
        except Exception as e:
            logger.error(f"Error getting route info: {e}")
            return {"success": False, "error": f"Ошибка: {str(e)}"}

    def get_full_qr_result(self, order_id: int, route_id: int = None) -> Dict:
        """
        Получить полный результат сканирования QR-кода

        Returns:
            dict с полной информацией для отображения
        """
        order_info = self.get_order_info(order_id)
        if not order_info:
            return {"success": False, "error": "Заказ не найден"}

        schedule = self.get_schedule_for_qr(order_id)
        status = self.get_order_status(order_id)

        route_info = None
        if route_id:
            route_info = self.get_route_info(route_id)

        return {
            "success": True,
            "order": order_info,
            "schedule": schedule,
            "status": status,
            "route_info": route_info,
            "route_id": route_id,
        }

    @staticmethod
    def _format_date(val) -> str:
        if val is None:
            return ""
        if isinstance(val, datetime):
            return val.strftime("%d.%m.%Y")
        if hasattr(val, 'isoformat'):
            return val.isoformat()[:10]
        return str(val)

    @staticmethod
    def _format_datetime(val) -> str:
        if val is None:
            return ""
        if isinstance(val, datetime):
            return val.strftime("%d.%m.%Y %H:%M")
        if hasattr(val, 'isoformat'):
            return val.isoformat()[:19]
        return str(val)


def format_time(seconds: float) -> str:
    """Форматирует секунды в читаемый вид"""
    if seconds is None:
        return "—"

    seconds = abs(seconds)
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours}ч {minutes}м"
    elif minutes > 0:
        return f"{minutes}м {secs}с"
    else:
        return f"{secs}с"
