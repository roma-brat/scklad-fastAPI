"""DOCX генератор маршрутных карт для FastAPI приложения.

Генерирует DOCX из шаблона «Шаблон Маршрутной карты.docx» с помощью docxtpl.
Заполняет данные маршрута, операции, вставляет QR-код и эскиз формы.
"""

from __future__ import annotations

import os
import qrcode
from io import BytesIO
from datetime import datetime
from typing import Optional
from docxtpl import DocxTemplate, InlineImage
from docx.shared import Mm


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


def safe_text(value) -> str:
    """Безопасное преобразование значения в строку."""
    return str(value) if value is not None else ""


def _resolve_template_path() -> str:
    """Возвращает путь к шаблону DOCX.

    Ищет в нескольких местах:
    1. Папка «Документы» в корне проекта
    2. Папка forms в корне проекта
    3. Папка рядом с этим файлом
    """
    template_name = "Шаблон Маршрутной карты.docx"

    # 1. Проектная папка «Документы»
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    candidate = os.path.join(project_root, "Документы", template_name)
    if os.path.exists(candidate):
        return candidate

    # 2. Папка forms в корне проекта
    candidate = os.path.join(project_root, "forms", template_name)
    if os.path.exists(candidate):
        return candidate

    # 3. Рядом с этим файлом (services/)
    candidate = os.path.join(os.path.dirname(os.path.abspath(__file__)), template_name)
    if os.path.exists(candidate):
        return candidate

    raise FileNotFoundError(
        f"Шаблон DOCX не найден: {template_name}. "
        f"Поместите файл в папку «Документы» или «forms» в корне проекта."
    )


def _resolve_form_image_path(form_file: str) -> str | None:
    """Возвращает путь к PNG-файлу формы (эскиза)."""
    # 1. Папка forms в корне проекта
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    candidate = os.path.join(project_root, "forms", form_file)
    if os.path.exists(candidate):
        return candidate

    # 2. Рядом с этим файлом
    candidate = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "forms", form_file)
    if os.path.exists(candidate):
        return candidate

    return None


class RouteDOCXGenerator:
    """Генератор DOCX маршрутных карт из шаблона docxtpl."""

    def __init__(self, template_path: str | None = None, output_dir: str | None = None):
        """
        Args:
            template_path: Путь к шаблону DOCX. По умолчанию ищет в проекте.
            output_dir: Директория для временного сохранения. По умолчанию — /tmp/routes_docx.
        """
        self.template_path = template_path or _resolve_template_path()
        self.output_dir = output_dir or "/tmp/routes_docx"

    def generate(self, route_data: dict, operations: list) -> bytes:
        """Генерирует DOCX и возвращает как bytes.

        Args:
            route_data: Словарь с данными маршрута
                (detail_name, designation, mark_name, sortament_name, dimensions,
                 quantity, form_type, preprocessing, param_l, param_w, param_s,
                 param_d, param_d1, quantity_from_blank, order_id, id).
            operations: Список словарей с операциями
                (workshop_name, operation_name, equipment_name, notes, seq/sequence_number,
                 duration/duration_minutes, is_cooperation).

        Returns:
            bytes: Содержимое DOCX-файла.
        """
        doc = DocxTemplate(self.template_path)

        # === ОБРАБОТКА ОПЕРАЦИЙ ===
        processed_operations = []
        for op in operations:
            ws = safe_text(op.get("workshop_name", ""))

            # Преобразование названия цеха
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

            op_text = f"{safe_text(op.get('operation_name', ''))}"
            equip = safe_text(op.get("equipment_name"))
            if equip and equip != "—":
                op_text += f", {equip}"

            notes = safe_text(op.get("notes"))
            if notes:
                op_text += f" ({notes})"

            seq = op.get("sequence_number", op.get("seq", 0))
            processed_operations.append(
                {
                    "seq": f"{seq:02d}" if isinstance(seq, int) else safe_text(seq),
                    "workshop": workshop,
                    "op_text": op_text,
                    "duration": op.get("duration", op.get("duration_minutes", "")),
                }
            )

        # === ПРЕДВАРИТЕЛЬНАЯ ОБРАБОТКА ===
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

        # === ИЗОБРАЖЕНИЯ (QR и Эскиз) ===
        # Генерируем QR
        order_id = route_data.get("order_id", route_data.get("id", ""))
        route_id = route_data.get("id", "")
        qr_data_string = f"sklad://order/{order_id}?route={route_id}"
        qr_buf = generate_qr_code(qr_data_string)
        qr_image = InlineImage(doc, qr_buf, width=Mm(20))

        # Подтягиваем эскиз
        sketch_image: InlineImage | str = ""
        if form_type:
            form_files = {
                "Параллелепипед": "Параллелепипед.png",
                "Цилиндр": "Цилиндр.png",
                "Цилиндр с отверстием": "ЦилиндрОтверстие.png",
                "Техпроцесс": "Техпроцесс.png",
            }
            fname = form_files.get(form_type)
            if fname:
                img_path = _resolve_form_image_path(fname)
                if img_path:
                    sketch_image = InlineImage(doc, img_path, width=Mm(20))

        # === ФОРМИРОВАНИЕ КОНТЕКСТА ===
        context = {
            "date_now": datetime.now().strftime("%d.%m.%Y"),
            "detail_name": safe_text(route_data.get("detail_name", "Изделие")),
            "designation": safe_text(route_data.get("designation", "")),
            "mark_name": safe_text(route_data.get("mark_name", "")),
            "sortament_name": safe_text(route_data.get("sortament_name", "")),
            "dimensions": safe_text(route_data.get("dimensions", "")),
            "quantity": route_data.get("quantity", 1),
            "quantity_from_blank": route_data.get("quantity_from_blank", route_data.get("quantity", 1)),
            "operations": processed_operations,
            "preprocess_text": preprocess_text,
            "qr_code": qr_image,
            "sketch_img": sketch_image,
        }

        # Рендерим
        doc.render(context)

        # Сохраняем в BytesIO для возврата без записи на диск
        output_buf = BytesIO()
        doc.save(output_buf)
        output_buf.seek(0)
        return output_buf.getvalue()

    def generate_and_save(
        self,
        route_data: dict,
        operations: list,
        filename: str | None = None,
    ) -> str:
        """Генерирует DOCX и сохраняет на диск.

        Args:
            route_data: Словарь с данными маршрута.
            operations: Список словарей с операциями.
            filename: Имя файла. По умолчанию — route_{designation}_{timestamp}.docx.

        Returns:
            str: Полный путь к сохранённому файлу.
        """
        os.makedirs(self.output_dir, exist_ok=True)

        if filename is None:
            designation = route_data.get("designation", "unknown")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"route_{designation}_{timestamp}.docx"

        filepath = os.path.join(self.output_dir, filename)
        docx_bytes = self.generate(route_data, operations)

        with open(filepath, "wb") as f:
            f.write(docx_bytes)

        return filepath
