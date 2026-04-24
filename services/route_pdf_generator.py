"""PDF генератор маршрутных карт для FastAPI приложения.

Генерирует PDF с двумя маршрутными картами на одной странице A4 (портрет).
Использует reportlab с поддержкой кириллицы (шрифт DejaVu Sans).
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
    # Список путей к распространённым кириллическим шрифтам
    candidate_paths = [
        # macOS
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
        # Linux (DejaVu)
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        # Windows
        "C:/Windows/Fonts/arial.ttf",
        # Проектный шрифт (если пользователь положит)
        os.path.join(
            os.path.dirname(__file__), "..", "static", "fonts", "DejaVuSans.ttf"
        ),
    ]

    for path in candidate_paths:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont("RouteFont", path))
                return "RouteFont"
            except Exception:
                continue

    # Fallback — встроенный Helvetica (поддерживает только латиницу, но PDF сгенерируется)
    return "Helvetica"


DEFAULT_FONT = _register_cyrillic_font()


# ---------------------------------------------------------------------------
# Утилиты
# ---------------------------------------------------------------------------


def safe_text(value) -> str:
    """Безопасное преобразование значения в строку."""
    return str(value) if value is not None else ""


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
# Создание элементов одной маршрутной карты
# ---------------------------------------------------------------------------


def _make_qr_image(route_data: dict) -> Image:
    order_id = route_data.get("order_id", route_data.get("id", ""))
    route_id = route_data.get("id", "")
    qr_data = f"sklad://order/{order_id}?route={route_id}"
    qr_buf = generate_qr_code(qr_data)
    return Image(qr_buf, width=16 * mm, height=16 * mm)


def _make_sketch_image(route_data: dict) -> Union[Image, str]:
    """Возвращает Image или пустую строку."""
    form_type = route_data.get("form_type")
    if not form_type:
        return ""

    form_files = {
        "Параллелепипед": "Параллелепипед.png",
        "Цилиндр": "Цилиндр.png",
        "Цилиндр с отверстием": "ЦилиндрОтверстие.png",
        "Техпроцесс": "Техпроцесс.png",
    }
    fname = form_files.get(form_type)
    if not fname:
        return ""

    # Ищем папку forms в корне проекта (sklad_instrumenta/forms)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    project_root = os.path.dirname(base_dir)  # Поднимаемся на уровень выше fastapi_app
    img_path = os.path.join(project_root, "forms", fname)
    if os.path.exists(img_path):
        return Image(img_path, width=16 * mm, height=16 * mm)
    return ""


def _build_header_table(route_data: dict) -> Table:
    """Таблица шапки маршрутной карты (6 колонок × 6 строк)."""
    qr_img = _make_qr_image(route_data)
    sketch_img = _make_sketch_image(route_data)

    title_style = ParagraphStyle(
        "Title", fontName=DEFAULT_FONT, fontSize=8, alignment=1, leading=10
    )
    norm_style = ParagraphStyle("Norm", fontName=DEFAULT_FONT, fontSize=8, leading=10)
    small_style = ParagraphStyle("Small", fontName=DEFAULT_FONT, fontSize=7, leading=9)

    order_qty = route_data.get("order_quantity", route_data.get("quantity", ""))
    blanks_qty = route_data.get("blanks_needed", route_data.get("quantity", ""))

    # Формируем номер заказа
    order_num = route_data.get("order_number")
    order_id = route_data.get("order_id", route_data.get("id", ""))

    if order_num:
        # order_num может быть int (70) или строкой ("70")
        order_display = f"ШТ-{order_num}"
    elif order_id:
        # Fallback: используем order_id
        order_display = f"ШТ-{order_id}"
    else:
        order_display = safe_text(order_id)

    # Предварительная обработка
    preprocess_text = ""
    form_type = route_data.get("form_type")
    if route_data.get("preprocessing"):
        preprocess_text = "Да"
        params = []
        if form_type == "Параллелепипед":
            if route_data.get("param_l"):
                params.append(f"L={route_data.get('param_l')}")
            if route_data.get("param_w"):
                params.append(f"W={route_data.get('param_w')}")
            if route_data.get("param_s"):
                params.append(f"S={route_data.get('param_s')}")
        elif form_type == "Цилиндр":
            if route_data.get("param_l"):
                params.append(f"L={route_data.get('param_l')}")
            if route_data.get("param_d"):
                params.append(f"Ø={route_data.get('param_d')}")
        elif form_type == "Цилиндр с отверстием":
            if route_data.get("param_l"):
                params.append(f"L={route_data.get('param_l')}")
            if route_data.get("param_d"):
                params.append(f"Ø={route_data.get('param_d')}")
            if route_data.get("param_d1"):
                params.append(f"d1={route_data.get('param_d1')}")
        if params:
            preprocess_text += f". {form_type}: " + ", ".join(params)

    header_data = [
        [
            qr_img,
            Paragraph("<b>МАРШРУТНАЯ КАРТА</b>", title_style),
            "",
            "",
            "",
            sketch_img,
        ],
        ["", "№ заказа", safe_text(order_display), "Размер партии", str(order_qty), ""],
        [
            "",
            " Изделие",
            Paragraph(
                f"<b>{safe_text(route_data.get('designation'))}</b> - {safe_text(route_data.get('detail_name'))}",
                norm_style,
            ),
            "",
            "",
            "",
        ],
        [
            "",
            "Материал",
            Paragraph(f"<b>{safe_text(route_data.get('mark_name'))}</b>", norm_style),
            "",
            "",
            "",
        ],
        [
            "",
            "Сортамент",
            Paragraph(
                f"<b>{safe_text(route_data.get('sortament_name'))}</b>", norm_style
            ),
            "Габариты загот.",
            Paragraph(f"<b>{safe_text(route_data.get('dimensions'))}</b>", norm_style),
            "",
        ],
        [
            "Кол-во заготовок",
            "Кол-во заготовок",
            str(blanks_qty),
            "Предв. обраб.",
            Paragraph(preprocess_text, small_style),
            "",
        ],
    ]

    table = Table(
        header_data,
        colWidths=[16 * mm, 20 * mm, 41 * mm, 26 * mm, 42 * mm, 25 * mm],
        rowHeights=[7 * mm, 5 * mm, 6 * mm, 6 * mm, 6 * mm, 6 * mm],
    )
    table.setStyle(
        TableStyle(
            [
                ("SPAN", (0, 0), (0, 4)),
                ("SPAN", (5, 0), (5, 5)),
                ("SPAN", (1, 0), (4, 0)),
                ("SPAN", (2, 2), (4, 2)),
                ("SPAN", (2, 3), (4, 3)),
                ("SPAN", (0, 5), (1, 5)),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (0, -1), "CENTER"),
                ("ALIGN", (5, 0), (5, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, -1), DEFAULT_FONT),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return table


def _build_operations_table(operations: list, route_card_data: dict = None) -> Table:
    """Таблица операций маршрутной карты."""
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

    card_operations = {}
    if route_card_data and isinstance(route_card_data, dict):
        for op in route_card_data.get("operations", []):
            card_operations[op.get("operation_id")] = op

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
        op_id = op.get("id")

        card_op = card_operations.get(op_id, {})
        operator_fio = card_op.get("operator_fio", "")
        operation_date = card_op.get("operation_date", "")
        quantity_plan = card_op.get("quantity_plan", "")
        quantity_fact = card_op.get("quantity_fact", "")
        defects = card_op.get("defects", "")
        otk_approved = card_op.get("otk_approved", False)

        if operator_fio:
            fio_style = small_style
        else:
            fio_style = empty_style
            operator_fio = "_______________"

        ops_data.append(
            [
                f"{seq:02d}",
                workshop,
                Paragraph(op_text, small_style),
                Paragraph(operator_fio, fio_style),
                operation_date or "",
                str(quantity_plan) if quantity_plan else "",
                str(quantity_fact) if quantity_fact else "",
                str(defects) if defects else "",
                "✓" if otk_approved else "",
            ]
        )

    # Строка ОТК
    ops_data.append(["", "ОТК", "контрольная", "", "", "", "", "", ""])

    col_widths = [
        8 * mm,     # №
        10 * mm,    # Цех/Участок
        70 * mm,    # Операция, оборудование (расширено для примечаний)
        20 * mm,    # ФИО
        18 * mm,    # Дата
        10 * mm,   # План
        10 * mm,   # Факт
        10 * mm,   # Брак
        18 * mm,   # ОТК
    ]
    n_ops = len(operations)
    row_heights = [5 * mm, 4 * mm] + [5 * mm] * n_ops + [5 * mm]

    table = Table(ops_data, colWidths=col_widths, repeatRows=2, rowHeights=row_heights)
    table.setStyle(
        TableStyle(
            [
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
            ]
        )
    )
    return table


def _build_signatures_table() -> Table:
    """Таблица подписей под маршрутной картой."""
    sign_data = [
        [
            "Изделия сдал _______________ /_______________________/",
            "Изделия принял _______________ /_______________________/",
        ],
    ]
    table = Table(sign_data, colWidths=[85 * mm, 85 * mm])
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), DEFAULT_FONT),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ALIGN", (0, 0), (0, 0), "LEFT"),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
            ]
        )
    )
    return table


def _create_card_elements(
    route_data: dict, operations: list, route_card_data: dict = None
) -> list:
    """Создаёт все элементы (Flowables) для одной маршрутной карты."""
    elements = []
    elements.append(_build_header_table(route_data))
    elements.append(Spacer(1, 3 * mm))
    elements.append(_build_operations_table(operations, route_card_data))
    elements.append(Spacer(1, 2 * mm))
    elements.append(_build_signatures_table())
    return elements


# ---------------------------------------------------------------------------
# Основной класс генератора
# ---------------------------------------------------------------------------


class RoutePDFGenerator:
    """Генератор PDF маршрутных карт (1 карта на странице A4, портрет)."""

    def __init__(self, output_dir: str | None = None):
        """
        Args:
            output_dir: Директория для сохранения PDF. По умолчанию — /tmp/routes_pdf.
        """
        self.output_dir = output_dir or "/tmp/routes_pdf"

    def generate(
        self, route_data: dict, operations: list, route_card_data: dict = None
    ) -> bytes:
        """Генерирует PDF и возвращает как bytes.

        Args:
            route_data: Словарь с данными маршрута (detail_name, designation, mark_name, …).
            operations: Список словарей с операциями маршрута.
            route_card_data: Данные ЭМК (операторы, даты, количества и т.д.)

        Returns:
            bytes: Содержимое PDF-файла.
        """
        os.makedirs(self.output_dir, exist_ok=True)

        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=15 * mm,
            rightMargin=15 * mm,
            topMargin=10 * mm,
            bottomMargin=10 * mm,
        )

        story: list = []

        # Одна карта на странице
        story.extend(_create_card_elements(route_data, operations, route_card_data))

        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()

    def generate_and_save(
        self,
        route_data: dict,
        operations: list,
        filename: str | None = None,
        route_card_data: dict = None,
    ) -> str:
        """Генерирует PDF и сохраняет на диск.

        Args:
            route_data: Словарь с данными маршрута.
            operations: Список словарей с операциями.
            filename: Имя файла. По умолчанию — route_{designation}_{timestamp}.pdf.
            route_card_data: Данные ЭМК (операторы, даты, количества).

        Returns:
            str: Полный путь к сохранённому файлу.
        """
        os.makedirs(self.output_dir, exist_ok=True)

        if filename is None:
            designation = route_data.get("designation", "unknown")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"route_{designation}_{timestamp}.pdf"

        filepath = os.path.join(self.output_dir, filename)
        pdf_bytes = self.generate(route_data, operations, route_card_data)

        with open(filepath, "wb") as f:
            f.write(pdf_bytes)

        return filepath
