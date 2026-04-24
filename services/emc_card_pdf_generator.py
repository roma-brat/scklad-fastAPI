"""PDF генератор ЭМК (электронных маршрутных карт) для FastAPI приложения.

Генерирует PDF с одной маршрутной картой на странице A4 (портретная ориентация).
Использует reportlab с поддержкой кириллицы (шрифт DejaVu Sans).
Вид ЭМК соответствует PDF маршрутов, но с заполненными данными планирования.
"""

from __future__ import annotations

import os
import qrcode
from io import BytesIO
from datetime import datetime
from typing import Dict, Any, Optional, Union, List
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    Image,
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


# ---------------------------------------------------------------------------
# Регистрация шрифта с поддержкой кириллицы
# ---------------------------------------------------------------------------


def _register_cyrillic_font() -> str:
    """Пытается зарегистрировать TT-шрифт с кириллицей. Возвращает имя шрифта."""
    candidate_paths = [
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "C:/Windows/Fonts/arial.ttf",
        os.path.join(
            os.path.dirname(__file__), "..", "static", "fonts", "DejaVuSans.ttf"
        ),
    ]

    for path in candidate_paths:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont("EMCFont", path))
                return "EMCFont"
            except Exception:
                continue

    return "Helvetica"


DEFAULT_FONT = _register_cyrillic_font()


# ---------------------------------------------------------------------------
# Утилиты
# ---------------------------------------------------------------------------


def safe_text(value) -> str:
    """Безопасное преобразование значения в строку."""
    return str(value) if value is not None else ""


def _get_workshop_code(workshop_name: str) -> str:
    """Получить код цеха/участка."""
    ws = safe_text(workshop_name)
    if ws == "Механический":
        return "6"
    elif ws == "Заготовительный":
        return "9"
    elif ws == "Малярный":
        return "5"
    return ws


def generate_qr_code(data: str) -> BytesIO:
    """Генерация QR-кода и возврат в виде BytesIO (PNG)."""
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


# ---------------------------------------------------------------------------
# Создание элементов ЭМК (в стиле маршрутной карты)
# ---------------------------------------------------------------------------


def _make_qr_image(order_data: dict) -> Image:
    """Создание QR-кода для заказа."""
    order_id = order_data.get("id", order_data.get("order_id", ""))
    route_id = order_data.get("route_id", "")
    qr_data = f"sklad://order/{order_id}?route={route_id}"
    qr_buf = generate_qr_code(qr_data)
    return Image(qr_buf, width=16 * mm, height=16 * mm)


def _build_emc_header(order_data: dict) -> Table:
    """Таблица заголовка ЭМК (в стиле маршрутной карты)."""
    qr_img = _make_qr_image(order_data)

    title_style = ParagraphStyle(
        "Title", fontName=DEFAULT_FONT, fontSize=8, alignment=1, leading=10
    )
    norm_style = ParagraphStyle("Norm", fontName=DEFAULT_FONT, fontSize=8, leading=10)
    small_style = ParagraphStyle("Small", fontName=DEFAULT_FONT, fontSize=7, leading=9)

    # Номер заказа
    order_num = order_data.get("order_number")
    order_id = order_data.get("id", order_data.get("order_id", ""))
    if order_num:
        order_display = f"ШТ-{order_num}"
    elif order_id:
        order_display = f"ШТ-{order_id}"
    else:
        order_display = safe_text(order_id)

    # Основная информация
    designation = safe_text(order_data.get("designation"))
    detail_name = safe_text(order_data.get("detail_name"))
    quantity = order_data.get("quantity", 1)
    blanks_needed = order_data.get("blanks_needed", quantity)
    mark_name = safe_text(order_data.get("mark_name"))
    sortament_name = safe_text(order_data.get("sortament_name"))
    dimensions = safe_text(order_data.get("dimensions"))

    # Статус из schedule_items
    status = "Запланировано"
    if order_data.get("is_planned"):
        status = "В работе" if order_data.get("in_progress") else "Запланировано"

    material = f"{mark_name}"
    if sortament_name:
        material += f" {sortament_name}"

    header_data = [
        [
            qr_img,
            Paragraph("<b>МАРШРУТНАЯ КАРТА (ЭМК)</b>", title_style),
            "",
            "",
            "",
        ],
        ["", "№ заказа", safe_text(order_display), "Размер партии", str(quantity), ""],
        [
            "",
            " Изделие",
            Paragraph(f"<b>{designation}</b> - {detail_name}", norm_style),
            "",
            "",
            "",
        ],
        [
            "",
            "Материал",
            Paragraph(f"<b>{material}</b>", norm_style),
            "",
            "",
            "",
        ],
        [
            "",
            "Сортамент",
            Paragraph(f"<b>{sortament_name}</b>", norm_style),
            "Габариты",
            Paragraph(f"<b>{dimensions}</b>", norm_style),
            "",
        ],
        [
            "Кол-во заготовок",
            "Кол-во заготовок",
            str(blanks_needed),
            "Статус",
            Paragraph(f"<b>{status}</b>", norm_style),
            "",
        ],
    ]

    table = Table(
        header_data,
        colWidths=[16 * mm, 20 * mm, 41 * mm, 26 * mm, 42 * mm, 25 * mm],
        rowHeights=[7 * mm, 5 * mm, 6 * mm, 6 * mm, 6 * mm, 6 * mm],
    )
    table.setStyle(
        TableStyle([
            ("SPAN", (0, 0), (0, 4)),
            ("SPAN", (5, 0), (5, 5)),
            ("SPAN", (1, 0), (4, 0)),
            ("SPAN", (2, 2), (4, 2)),
            ("SPAN", (2, 3), (4, 3)),
            ("SPAN", (2, 4), (4, 4)),
            ("SPAN", (0, 5), (1, 5)),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ("ALIGN", (5, 0), (5, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, -1), DEFAULT_FONT),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
        ])
    )
    return table


def _build_emc_operations(operations: list, schedule_items: list = None, order_data: dict = None, route_card_data: dict = None) -> Table:
    """Таблица операций ЭМК (в стиле маршрутной карты)."""
    import logging
    logger = logging.getLogger(__name__)

    # DEBUG: log incoming data
    logger.info(f"[_build_emc_operations] route_card_data type: {type(route_card_data)}")
    if route_card_data:
        logger.info(f"[_build_emc_operations] route_card_data keys: {route_card_data.keys() if isinstance(route_card_data, dict) else 'not a dict'}")
        ops_in_card = route_card_data.get("operations", []) if isinstance(route_card_data, dict) else []
        logger.info(f"[_build_emc_operations] operations in route_card_data: {len(ops_in_card)}")
        for i, co in enumerate(ops_in_card[:3]):
            logger.info(f"  card_op[{i}]: operation_id={co.get('operation_id')}, operator_fio={co.get('operator_fio')}, quantity_plan={co.get('quantity_plan')}")

    logger.info(f"[_build_emc_operations] operations count: {len(operations)}")
    for i, op in enumerate(operations[:3]):
        logger.info(f"  op[{i}]: id={op.get('id')}, sequence_number={op.get('sequence_number')}, operation_name={op.get('operation_name')}")

    small_style = ParagraphStyle("Small", fontName=DEFAULT_FONT, fontSize=7, leading=9)
    empty_style = ParagraphStyle(
        "Empty", fontName=DEFAULT_FONT, fontSize=7, leading=9, textColor=colors.gray
    )

    ops_data = [
        [
            "№\nопер.",
            "Цех/\nУчасток",
            "Операция, оборудование",
            "ФИО\nоператора",
            "Дата",
            "Количество",
            "",
            "",
            "Отметка\nОТК",
        ],
        ["", "", "", "", "", "План", "Факт", "Брак", ""],
    ]

    # Создаём карту расписания по sequence_number для быстрого доступа
    schedule_map = {}
    if schedule_items:
        for item in schedule_items:
            seq = item.get("sequence_number")
            if seq:
                schedule_map[seq] = item

    # Создаём карту данных ЭМК по operation_id для быстрого доступа
    card_ops_map = {}
    if route_card_data and isinstance(route_card_data, dict):
        for card_op in route_card_data.get("operations", []):
            op_id = card_op.get("operation_id")
            if op_id:
                card_ops_map[str(op_id)] = card_op

    # Общее количество деталей по плану (из заказа)
    order_quantity = order_data.get("quantity", 1) if order_data else 1

    for op in operations:
        ws = safe_text(op.get("workshop_name", ""))
        if ws == "Механический":
            workshop = "6"
        elif ws == "Заготовительный":
            workshop = "9"
        elif ws == "Малярный":
            workshop = "5"
        elif op.get("is_cooperation"):
            workshop = f"К.{ws}"
        else:
            workshop = ws

        equip = safe_text(op.get("equipment_name"))
        op_text = f"{safe_text(op.get('operation_name'))}"
        if op.get("is_cooperation") and op.get("coop_company_name"):
            op_text += f" [{op['coop_company_name']}]"
        if equip and equip != "—":
            op_text += f", {equip}"
        notes = safe_text(op.get("notes"))
        if notes:
            op_text += f" ({notes})"

        seq = op.get("sequence_number", op.get("seq", 0))
        op_id = str(op.get("id"))

        # Получаем данные из карты ЭМК (оператор, количество)
        card_op = card_ops_map.get(op_id, {})
        logger.info(f"  lookup op_id={op_id}, found={bool(card_op)}, operator_fio={card_op.get('operator_fio', 'NOT FOUND')}")
        operator_fio = card_op.get("operator_fio", "")
        quantity_plan = card_op.get("quantity_plan") or order_quantity

        # Получаем данные из расписания
        sched_item = schedule_map.get(seq, {})
        planned_date = sched_item.get("planned_date") or ""
        if hasattr(planned_date, 'strftime'):
            planned_date = planned_date.strftime("%d.%m.%Y")

        status = sched_item.get("status", "")
        status_text = ""
        if status == "completed":
            status_text = "✓ Готово"
        elif status == "in_progress":
            status_text = "✓ В работе"
        elif status == "delayed":
            status_text = "⚠ Задержка"

        if operator_fio:
            fio_style = small_style
        else:
            fio_style = empty_style
            operator_fio = "_______________"

        ops_data.append([
            f"{seq:02d}" if seq else "??",
            workshop,
            Paragraph(op_text, small_style),
            Paragraph(operator_fio, fio_style),
            planned_date or "",
            str(quantity_plan),
            status_text,
            "",
            "",
        ])

    # Строка ОТК
    ops_data.append(["", "ОТК", "контрольная", "", "", "", "", "", ""])

    col_widths = [
        8 * mm,     # №
        10 * mm,    # Цех
        70 * mm,    # Операция (расширено для примечаний)
        20 * mm,    # ФИО
        18 * mm,    # Дата
        10 * mm,    # План
        10 * mm,    # Факт
        10 * mm,    # Брак
        18 * mm,    # ОТК
    ]
    n_ops = len(operations)
    row_heights = [5 * mm, 4 * mm] + [5 * mm] * n_ops + [5 * mm]

    table = Table(ops_data, colWidths=col_widths, repeatRows=2, rowHeights=row_heights)
    table.setStyle(
        TableStyle([
            ("SPAN", (0, 0), (0, 1)),
            ("SPAN", (1, 0), (1, 1)),
            ("SPAN", (2, 0), (2, 1)),
            ("SPAN", (3, 0), (3, 1)),
            ("SPAN", (4, 0), (4, 1)),
            ("SPAN", (5, 0), (7, 0)),
            ("SPAN", (8, 0), (8, 1)),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("ALIGN", (2, 2), (2, -2), "LEFT"),
            ("FONTNAME", (0, 0), (-1, -1), DEFAULT_FONT),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
        ])
    )
    return table


def _build_emc_signatures() -> Table:
    """Таблица подписей ЭМК."""
    sign_data = [
        [
            "Изделия сдал _______________ /_______________________/",
            "Изделия принял _______________ /_______________________/",
        ],
    ]
    table = Table(sign_data, colWidths=[85 * mm, 85 * mm])
    table.setStyle(
        TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), DEFAULT_FONT),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ALIGN", (0, 0), (0, 0), "LEFT"),
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ])
    )
    return table


def _create_emc_elements(
    order_data: dict, operations: list, schedule_items: list = None, route_card_data: dict = None
) -> list:
    """Создаёт все элементы (Flowables) для ЭМК в стиле маршрутной карты."""
    elements = []
    elements.append(_build_emc_header(order_data))
    elements.append(Spacer(1, 3 * mm))
    elements.append(_build_emc_operations(operations, schedule_items, order_data, route_card_data))
    elements.append(Spacer(1, 2 * mm))
    elements.append(_build_emc_signatures())
    return elements


# ---------------------------------------------------------------------------
# Основной класс генератора
# ---------------------------------------------------------------------------


class EMCCardPDFGenerator:
    """Генератор PDF ЭМК (1 карта на странице A4, портрет)."""

    def __init__(self, output_dir: str | None = None):
        """
        Args:
            output_dir: Директория для сохранения PDF. По умолчанию — /tmp/emc_pdf.
        """
        self.output_dir = output_dir or "/tmp/emc_pdf"

    def generate(
        self, order_data: dict, operations: list, schedule_items: list = None, route_card_data: dict = None
    ) -> bytes:
        """Генерирует PDF и возвращает как bytes.

        Args:
            order_data: Словарь с данными заказа.
            operations: Список словарей с операциями.
            schedule_items: Список элементов расписания с датами и статусами.
            route_card_data: Данные ЭМК (операторы, количества и т.д.)

        Returns:
            bytes: Содержимое PDF-файла.
        """
        os.makedirs(self.output_dir, exist_ok=True)

        buffer = BytesIO()
        # Портретная ориентация (как у маршрута)
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=15 * mm,
            rightMargin=15 * mm,
            topMargin=10 * mm,
            bottomMargin=10 * mm,
        )

        story: list = []
        story.extend(_create_emc_elements(order_data, operations, schedule_items, route_card_data))

        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()

    def generate_and_save(
        self,
        order_data: dict,
        operations: list,
        filename: str | None = None,
        schedule_items: list = None,
        route_card_data: dict = None,
    ) -> str:
        """Генерирует PDF и сохраняет на диск.

        Args:
            order_data: Словарь с данными заказа.
            operations: Список словарей с операциями.
            filename: Имя файла. По умолчанию — emc_{order_id}_{timestamp}.pdf.
            schedule_items: Список элементов расписания.
            route_card_data: Данные ЭМК (операторы, количества и т.д.)

        Returns:
            str: Полный путь к сохранённому файлу.
        """
        os.makedirs(self.output_dir, exist_ok=True)

        if filename is None:
            order_id = order_data.get("id", order_data.get("order_id", "unknown"))
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"emc_{order_id}_{timestamp}.pdf"

        filepath = os.path.join(self.output_dir, filename)
        pdf_bytes = self.generate(order_data, operations, schedule_items, route_card_data)

        with open(filepath, "wb") as f:
            f.write(pdf_bytes)

        return filepath