# services/planning_rules.py
"""
Библиотека правил планирования производства.
Все правила и константы для планирования деталей на станках.

Использование:
    from services.planning_rules import (
        WORKING_HOURS_PER_DAY,
        is_working_day,
        calculate_duration_days,
        normalize_equipment,
        find_available_slot,
        # и другие функции
    )
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import re


# ============================================================================
# КОНСТАНТЫ
# ============================================================================

WORKING_HOURS_PER_DAY = 7
"""
Количество рабочих часов в рабочем дне.
Используется по умолчанию, если не указано иное в настройках станка.
"""

MINUTES_PER_DAY = WORKING_HOURS_PER_DAY * 60
"""
Количество минут в рабочем дне (по умолчанию 420 минут).
"""

MAX_SEARCH_DAYS = 365
"""
Максимальное количество дней для поиска свободного слота.
"""

DEFAULT_DURATION_MINUTES = 60
"""
Длительность операции по умолчанию (в минутах).
"""

DEFAULT_PRIORITY = 5
"""
Приоритет заказа по умолчанию.
"""

PARTS_PER_DAY_CONSTANT = 420
"""
Константа для расчёта количества деталей в день.
Используется в формуле: parts_per_day = max(1, int(420 / duration_minutes))
"""


# ============================================================================
# БАЗОВЫЕ ФУНКЦИИ ПЛАВИРОВАНИЯ
# ============================================================================


def is_working_day(date: datetime) -> bool:
    """
    Проверяет, является ли день рабочим.

    Рабочие дни: понедельник - пятница (weekday 0-4).
    Выходные: суббота и воскресенье (weekday 5-6).

    Args:
        date: Дата для проверки

    Returns:
        True если рабочий день, False если выходной
    """
    return date.weekday() < 5


def get_next_working_day(date: datetime) -> datetime:
    """
    Возвращает следующий рабочий день (включая переданный, если он рабочий).

    Args:
        date: Начальная дата

    Returns:
        Следующий рабочий день
    """
    current = date
    while current.weekday() >= 5:
        current += timedelta(days=1)
    return current


def is_equipment_working_day(
    date: datetime,
    equipment_id: int,
    equipment_calendar: dict,
    equipment_list: List[Dict],
) -> bool:
    """
    Проверяет, являетсяется ли день рабочим для конкретного станка.

    Приоритет проверки:
    1. Календарь станка (если запись есть - используется её значение is_working)
    2. default_working_hours станка (если > 0 - рабочий день)
    3. По умолчанию: пн-пт рабочие, сб-вс выходные

    Args:
        date: Дата для проверки
        equipment_id: ID станка
        equipment_calendar: dict {date_key: calendar_entry} - предзагруженный календарь
        equipment_list: Список оборудования из БД

    Returns:
        True если рабочий день, False если выходной
    """
    if isinstance(date, datetime):
        date_key = date.strftime("%Y-%m-%d")
    else:
        date_key = str(date)

    if equipment_calendar and date_key in equipment_calendar:
        entry = equipment_calendar[date_key]
        is_working = entry.get("is_working")
        if is_working is not None:
            return bool(is_working)
        working_hours = entry.get("working_hours")
        if working_hours is not None and working_hours > 0:
            return True
        return False

    for eq in equipment_list:
        if eq.get("id") == equipment_id:
            default_hours = eq.get("default_working_hours", WORKING_HOURS_PER_DAY)
            if default_hours and default_hours > 0:
                return date.weekday() < 5
            return False

    return date.weekday() < 5


def get_equipment_hours_for_day(
    date: datetime,
    equipment_id: int,
    equipment_calendar: dict,
    equipment_list: List[Dict],
) -> int:
    """
    Получает количество рабочих часов для станка на конкретный день.

    Args:
        date: Дата
        equipment_id: ID станка
        equipment_calendar: dict {date_key: calendar_entry}
        equipment_list: Список оборудования

    Returns:
        Количество рабочих часов (0 если выходной)
    """
    if isinstance(date, datetime):
        date_key = date.strftime("%Y-%m-%d")
    else:
        date_key = str(date)

    if equipment_calendar and date_key in equipment_calendar:
        entry = equipment_calendar[date_key]
        if entry.get("is_working") == False:
            return 0
        working_hours = entry.get("working_hours")
        if working_hours is not None:
            return working_hours

    for eq in equipment_list:
        if eq.get("id") == equipment_id:
            return eq.get("default_working_hours", WORKING_HOURS_PER_DAY)

    return WORKING_HOURS_PER_DAY


def add_equipment_working_days(
    start_date: datetime,
    days_to_add: int,
    equipment_id: int,
    equipment_calendar: dict,
    equipment_list: List[Dict],
) -> datetime:
    """
    Добавляет рабочие дни к дате с учётом календаря конкретного станка.

    Args:
        start_date: Начальная дата
        days_to_add: Количество рабочих дней для добавления
        equipment_id: ID станка
        equipment_calendar: dict {date_key: calendar_entry}
        equipment_list: Список оборудования

    Returns:
        Новая дата после добавления рабочих дней
    """
    current = start_date
    days_added = 0

    while days_added < days_to_add:
        if is_equipment_working_day(
            current, equipment_id, equipment_calendar, equipment_list
        ):
            days_added += 1
            if days_added >= days_to_add:
                break
        current += timedelta(days=1)

    return current


def find_next_equipment_working_day(
    start_date: datetime,
    equipment_id: int,
    equipment_calendar: dict,
    equipment_list: List[Dict],
    max_days: int = MAX_SEARCH_DAYS,
) -> Optional[datetime]:
    """
    Находит следующий рабочий день для конкретного станка.

    Args:
        start_date: Начальная дата поиска
        equipment_id: ID станка
        equipment_calendar: dict {date_key: calendar_entry}
        equipment_list: Список оборудования
        max_days: Максимальное количество дней для поиска

    Returns:
        Следующий рабочий день или None
    """
    current = start_date
    for _ in range(max_days):
        if is_equipment_working_day(
            current, equipment_id, equipment_calendar, equipment_list
        ):
            return current
        current += timedelta(days=1)
    return None


def calculate_duration_days(
    duration_minutes: int, hours_per_day: int = WORKING_HOURS_PER_DAY
) -> int:
    """
    Рассчитывает количество рабочих дней для выполнения операции.

    Формула: days = ceil(total_minutes / minutes_per_day)
    Всегда возвращает минимум 1 день.

    Args:
        duration_minutes: Общая длительность операции в минутах
        hours_per_day: Рабочих часов в день (по умолчанию 7)

    Returns:
        Количество рабочих дней (минимум 1)

    Example:
        >>> calculate_duration_days(120, 7)  # 2 часа при 7ч/день
        1
        >>> calculate_duration_days(480, 7)  # 8 часов при 7ч/день
        1
        >>> calculate_duration_days(500, 7)  # 8.3 часа при 7ч/день
        1
        >>> calculate_duration_days(840, 7)  # 14 часов при 7ч/день
        2
    """
    minutes_per_day = hours_per_day * 60
    if minutes_per_day == 0:
        return 1
    days = (duration_minutes + minutes_per_day - 1) // minutes_per_day
    return max(1, days)


def calculate_parts_per_day(duration_minutes: int) -> int:
    """
    Рассчитывает количество деталей, которые можно обработать за один день.

    Формула: parts_per_day = max(1, int(420 / duration_minutes))

    Args:
        duration_minutes: Время на одну деталь в минутах

    Returns:
        Количество деталей в день (минимум 1)

    Example:
        >>> calculate_parts_per_day(30)  # 30 мин на деталь
        14
        >>> calculate_parts_per_day(60)  # 60 мин на деталь
        7
        >>> calculate_parts_per_day(120)  # 120 мин на деталь
        3
    """
    if duration_minutes <= 0:
        return 1
    return max(1, int(PARTS_PER_DAY_CONSTANT / duration_minutes))


def calculate_days_needed(total_parts: int, parts_per_day: int) -> int:
    """
    Рассчитывает количество дней для обработки всех деталей.

    Args:
        total_parts: Общее количество деталей
        parts_per_day: Количество деталей в день

    Returns:
        Количество дней (минимум 1)

    Example:
        >>> calculate_days_needed(100, 10)
        10
        >>> calculate_days_needed(95, 10)
        10
        >>> calculate_days_needed(1, 10)
        1
    """
    if parts_per_day <= 0:
        return total_parts
    return max(1, (total_parts + parts_per_day - 1) // parts_per_day)


def get_minutes_needed(duration_minutes: int, quantity: int) -> int:
    """
    Рассчитывает общее количество минут для выполнения операции.

    Args:
        duration_minutes: Время на одну деталь в минутах
        quantity: Количество деталей

    Returns:
        Общее количество минут
    """
    return duration_minutes * quantity


def calculate_available_minutes_for_day(
    date: datetime,
    equipment_id: int,
    equipment_calendar: dict,
    equipment_list: List[Dict],
    existing_schedule: List[Dict],
    operation_type_id: int = None,
    exclude_order_id: int = None,
) -> int:
    """
    Рассчитывает свободные минуты для станка на конкретный день.

    Учитывает:
    - Рабочие часы станка на этот день (из календаря или настроек)
    - Уже запланированные операции на этот день для этого станка
    - Если указан operation_type_id - учитывает только операции этого типа
    - Если указан exclude_order_id - игнорирует операции этого заказа

    Args:
        date: Дата для проверки
        equipment_id: ID станка
        equipment_calendar: dict {date_key: calendar_entry}
        equipment_list: Список оборудования
        existing_schedule: Список уже запланированных операций (из БД + текущий цикл)
        operation_type_id: ID типа операции для фильтрации (опционально)
        exclude_order_id: ID заказа для исключения из расчёта (опционально)

    Returns:
        Количество свободных минут (0 если нет места)
    """
    if isinstance(date, datetime):
        date_key = date.strftime("%Y-%m-%d")
    else:
        date_key = str(date)

    available_hours = get_equipment_hours_for_day(
        date, equipment_id, equipment_calendar, equipment_list
    )

    if available_hours <= 0:
        return 0

    total_minutes = available_hours * 60

    occupied_minutes = 0
    for item in existing_schedule:
        item_date = item.get("planned_date")
        if item_date:
            if isinstance(item_date, str):
                item_date_key = item_date[:10]
            elif hasattr(item_date, "strftime"):
                item_date_key = item_date.strftime("%Y-%m-%d")
            else:
                item_date_key = str(item_date)

            if item_date_key == date_key and item.get("equipment_id") == equipment_id:
                if exclude_order_id is not None:
                    item_order = item.get("order_id")
                    if item_order == exclude_order_id:
                        continue
                if operation_type_id is not None:
                    item_type = item.get("operation_type_id")
                    if item_type != operation_type_id:
                        continue
                qty = item.get("quantity", 0)
                duration = item.get("duration_minutes", 60)
                occupied_minutes += qty * duration

    available = total_minutes - occupied_minutes
    return max(0, available)


def calculate_parts_for_day(duration_minutes: int, available_minutes: int) -> int:
    """
    Рассчитывает сколько деталей поместится в свободное время.

    Args:
        duration_minutes: Время на одну деталь в минутах
        available_minutes: Свободное время в минутах

    Returns:
        Количество деталей которое поместится

    Example:
        >>> calculate_parts_for_day(60, 300)  # 60 мин/дет, 5 часов свободно
        5
        >>> calculate_parts_for_day(60, 30)   # 60 мин/дет, 30 мин свободно
        0
    """
    if available_minutes <= 0 or duration_minutes <= 0:
        return 0
    return available_minutes // duration_minutes


def is_day_fully_available(
    date: datetime,
    equipment_id: int,
    equipment_calendar: dict,
    equipment_list: List[Dict],
    existing_schedule: List[Dict] = None,
    threshold: float = 0.9,
) -> bool:
    """
    Проверяет, является ли день "полностью свободным" для оборудования.

    День считается полностью свободным, если свободно >= threshold (по умолчанию 90%)
    рабочего времени оборудования.

    Args:
        date: Дата для проверки
        equipment_id: ID станка
        equipment_calendar: dict {date_key: calendar_entry}
        equipment_list: Список оборудования
        existing_schedule: Список уже запланированных операций (опционально)
        threshold: Порог свободного времени (0.0 - 1.0), по умолчанию 0.9 (90%)

    Returns:
        True если день свободен >= threshold, иначе False
    """
    if existing_schedule is None:
        existing_schedule = []

    available_hours = get_equipment_hours_for_day(
        date, equipment_id, equipment_calendar, equipment_list
    )

    if available_hours <= 0:
        return False

    total_minutes = available_hours * 60

    occupied_minutes = 0
    for item in existing_schedule:
        item_date = item.get("planned_date")
        if item_date:
            if isinstance(item_date, str):
                item_date_key = item_date[:10]
            elif hasattr(item_date, "strftime"):
                item_date_key = item_date.strftime("%Y-%m-%d")
            else:
                item_date_key = str(item_date)

            date_key = (
                date.strftime("%Y-%m-%d") if isinstance(date, datetime) else str(date)
            )

            if item_date_key == date_key and item.get("equipment_id") == equipment_id:
                qty = item.get("quantity", 0)
                duration = item.get("duration_minutes", 60)
                occupied_minutes += qty * duration

    free_minutes = total_minutes - occupied_minutes
    free_ratio = free_minutes / total_minutes if total_minutes > 0 else 0

    return free_ratio >= threshold


def calculate_available_minutes_for_day_after_time(
    date: datetime,
    equipment_id: int,
    equipment_calendar: dict,
    equipment_list: List[Dict],
    existing_schedule: List[Dict],
    after_time_minutes: int = 0,
    operation_type_id: int = None,
) -> int:
    """
    Рассчитывает свободные минуты для станка после указанного времени в тот же день.

    Учитывает:
    - Рабочие часы станка на этот день
    - Уже запланированные операции на этот день
    - Время начала отсчёта (after_time_minutes)
    - Если указан operation_type_id - учитывает только операции этого типа

    Args:
        date: Дата для проверки
        equipment_id: ID станка
        equipment_calendar: dict {date_key: calendar_entry}
        equipment_list: Список оборудования
        existing_schedule: Список уже запланированных операций
        after_time_minutes: Время начала отсчёта в минутах от начала дня (0-420)
                          Например, 300 = 17:00 (если рабочий день 7 часов)
        operation_type_id: ID типа операции для фильтрации (опционально)

    Returns:
        Количество свободных минут после after_time_minutes
    """
    if isinstance(date, datetime):
        date_key = date.strftime("%Y-%m-%d")
    else:
        date_key = str(date)

    available_hours = get_equipment_hours_for_day(
        date, equipment_id, equipment_calendar, equipment_list
    )

    if available_hours <= 0:
        return 0

    total_minutes = available_hours * 60

    if after_time_minutes >= total_minutes:
        return 0

    occupied_after_time = 0
    for item in existing_schedule:
        item_date = item.get("planned_date")
        if item_date:
            if isinstance(item_date, str):
                item_date_key = item_date[:10]
            elif hasattr(item_date, "strftime"):
                item_date_key = item_date.strftime("%Y-%m-%d")
            else:
                item_date_key = str(item_date)

            if item_date_key == date_key and item.get("equipment_id") == equipment_id:
                if operation_type_id is not None:
                    item_type = item.get("operation_type_id")
                    if item_type != operation_type_id:
                        continue
                qty = item.get("quantity", 0)
                duration = item.get("duration_minutes", 60)
                item_duration = qty * duration

                occupied_after_time += item_duration

    available = total_minutes - after_time_minutes - occupied_after_time
    return max(0, available)


# ============================================================================
# ФУНКЦИИ ДЛЯ РАБОТЫ С ДАТАМИ
# ============================================================================


def find_next_working_day(
    start_date: datetime, max_days: int = MAX_SEARCH_DAYS
) -> Optional[datetime]:
    """
    Находит следующий рабочий день начиная с start_date.

    Args:
        start_date: Начальная дата поиска
        max_days: Максимальное количество дней для поиска

    Returns:
        Следующий рабочий день или None если не найден
    """
    current = start_date
    for _ in range(max_days):
        if is_working_day(current):
            return current
        current += timedelta(days=1)
    return None


def find_available_slot(
    start_date: datetime, duration_days: int, max_search_days: int = MAX_SEARCH_DAYS
) -> Optional[datetime]:
    """
    Находит ближайшую доступную дату для слота заданной продолжительности.

    Пропускает выходные дни.

    Args:
        start_date: Начальная дата поиска
        duration_days: Требуемая продолжительность в днях
        max_search_days: Максимальное количество дней для поиска

    Returns:
        Дата начала доступного слота или None
    """
    current_date = start_date

    for _ in range(max_search_days):
        if is_working_day(current_date):
            duration_days -= 1
            if duration_days <= 0:
                return current_date

        current_date += timedelta(days=1)

    return None


def add_working_days(start_date: datetime, days_to_add: int) -> datetime:
    """
    Добавляет рабочие дни к дате.

    Args:
        start_date: Начальная дата
        days_to_add: Количество рабочих дней для добавления

    Returns:
        Новая дата
    """
    current = start_date
    days_added = 0

    while days_added < days_to_add:
        if is_working_day(current):
            days_added += 1
            if days_added >= days_to_add:
                break
        current += timedelta(days=1)

    return current


def get_date_range(start_date: str, end_date: str) -> List[str]:
    """
    Возвращает список всех дат в диапазоне.

    Args:
        start_date: Начальная дата в формате '%d.%m.%Y'
        end_date: Конечная дата в формате '%d.%m.%Y'

    Returns:
        Список дат в формате '%d.%m.%Y'
    """
    dates = []
    try:
        start = datetime.strptime(start_date, "%d.%m.%Y")
        end = datetime.strptime(end_date, "%d.%m.%Y")
        current = start

        while current <= end:
            dates.append(current.strftime("%d.%m.%Y"))
            current += timedelta(days=1)
    except ValueError:
        pass

    return dates


# ============================================================================
# ФУНКЦИИ ДЛЯ НОРМАЛИЗАЦИИ И ПОИСКА ОБОРУДОВАНИЯ
# ============================================================================


def normalize_equipment(name: str) -> str:
    """
    Нормализует название станка для поиска и сравнения.

    Выполняет:
    - Удаление текста в скобках (FANUC), (токарный) и т.д.
    - Замена кириллицы на латинские аналоги (С -> c, О -> 0)
    - Удаление специальных символов (_, №, -, пробелов)

    Args:
        name: Название станка

    Returns:
        Нормализованное название (нижний регистр)

    Example:
        >>> normalize_equipment("Станок ЧПУ-123 (FANUC)")
        'станокчпу123'
        >>> normalize_equipment("Токарный №5")
        'токарный5'
    """
    name = re.sub(r"\s*\([^)]*\)", "", name)
    name = name.replace("С", "C").replace("с", "c")
    name = name.replace("О", "0").replace("о", "0")
    name = name.replace("_", "").replace("№", "N")
    name = name.replace("-", "").replace(" ", "")
    return name.lower()


def equipment_match(name1: str, name2: str) -> bool:
    """
    Проверяет совпадение двух названий станков.

    Args:
        name1: Первое название
        name2: Второе название

    Returns:
        True если совпадают
    """
    return normalize_equipment(name1) == normalize_equipment(name2)


def equipment_contains(container: str, search: str) -> bool:
    """
    Проверяет, содержится ли нормализованное название search в container.

    Args:
        container: Название-контейнер
        search: Название для поиска

    Returns:
        True если содержится
    """
    norm_container = normalize_equipment(container)
    norm_search = normalize_equipment(search)
    return norm_search in norm_container or norm_container in norm_search


def find_equipment_row(
    worksheet_data: List[List[str]], equipment_name: str
) -> Optional[int]:
    """
    Находит строку с оборудованием в данных таблицы.

    Сначала ищет точное совпадение, затем частичное.

    Args:
        worksheet_data: Данные таблицы (список строк)
        equipment_name: Название станка для поиска

    Returns:
        Номер строки (1-based) или None если не найден
    """
    equip_normalized = normalize_equipment(equipment_name)

    for row_idx, row in enumerate(worksheet_data, start=1):
        if row and row[0]:
            cell_equip = normalize_equipment(row[0])
            if cell_equip == equip_normalized:
                return row_idx

    for row_idx, row in enumerate(worksheet_data, start=1):
        if row and row[0]:
            cell_equip = normalize_equipment(row[0])
            if equipment_contains(cell_equip, equip_normalized):
                return row_idx

    return None


def find_date_column(headers: List[str], target_date: str) -> Optional[int]:
    """
    Находит колонку с указанной датой в заголовках.

    Args:
        headers: Список заголовков колонок
        target_date: Дата для поиска в формате '%d.%m.%Y'

    Returns:
        Индекс колонки (1-based) или None
    """
    for col_idx, header in enumerate(headers, start=1):
        if header.strip() == target_date.strip():
            return col_idx
    return None


def is_cell_empty(value: Optional[str]) -> bool:
    """
    Проверяет, пустая ли ячейка.

    Args:
        value: Значение ячейки

    Returns:
        True если пустая
    """
    return not value or not value.strip()


def is_valid_date_format(date_str: str, format: str = "%d.%m.%Y") -> bool:
    """
    Проверяет, соответствует ли строка формату даты.

    Args:
        date_str: Строка с датой
        format: Ожидаемый формат

    Returns:
        True если валидная дата
    """
    try:
        datetime.strptime(date_str, format)
        return True
    except ValueError:
        return False


def parse_date(date_str: str, format: str = "%d.%m.%Y") -> Optional[datetime]:
    """
    Парсит строку в дату.

    Args:
        date_str: Строка с датой
        format: Формат даты

    Returns:
        Объект datetime или None при ошибке
    """
    try:
        return datetime.strptime(date_str, format)
    except ValueError:
        return None


def format_date(date: datetime, format: str = "%d.%m.%Y") -> str:
    """
    Форматирует дату в строку.

    Args:
        date: Объект datetime
        format: Требуемый формат

    Returns:
        Строка с датой
    """
    return date.strftime(format)


def format_date_iso(date: datetime) -> str:
    """
    Форматирует дату в формат ISO (YYYY-MM-DD).

    Args:
        date: Объект datetime

    Returns:
        Строка в формате YYYY-MM-DD
    """
    return date.strftime("%Y-%m-%d")


# ============================================================================
# ФУНКЦИИ ДЛЯ РАСЧЁТА РАСПИСАНИЯ
# ============================================================================


def calculate_schedule_for_operations(
    operations: List[Dict], quantity: int, start_date: datetime = None
) -> List[Dict]:
    """
    Рассчитывает расписание для списка операций.

    Операции выполняются последовательно. Для каждой операции:
    1. Рассчитывается количество деталей в день
    2. Детали распределяются по рабочим дням
    3. После завершения операции - переход к следующей

    Args:
        operations: Список операций с полями:
            - sequence_number: номер операции
            - duration_minutes: время на одну деталь
            - equipment_name: название станка
            - operation_name: название операции
        quantity: Общее количество деталей
        start_date: Дата начала (по умолчанию сегодня)

    Returns:
        Список записей расписания с полями:
            - date: дата в формате '%d.%m.%Y'
            - datetime: объект datetime
            - equipment_name: название станка
            - operation_name: название операции
            - parts: количество деталей
            - duration_minutes: время на деталь
            - operation_seq: номер операции
    """
    if start_date is None:
        start_date = datetime.now()

    schedule = []
    current_date = start_date

    for op in operations:
        duration_minutes = op.get("duration_minutes", DEFAULT_DURATION_MINUTES)
        equipment_name = op.get("equipment_name", "Unknown")
        operation_name = op.get("operation_name", "Operation")

        parts_per_day = calculate_parts_per_day(duration_minutes)
        remaining_parts = quantity
        op_start_date = current_date

        while remaining_parts > 0:
            while not is_working_day(current_date):
                current_date += timedelta(days=1)

            parts_today = min(remaining_parts, parts_per_day)

            schedule.append(
                {
                    "date": current_date.strftime("%d.%m.%Y"),
                    "datetime": current_date,
                    "equipment_name": equipment_name,
                    "operation_name": operation_name,
                    "parts": parts_today,
                    "duration_minutes": duration_minutes,
                    "operation_seq": op.get("sequence_number", 1),
                }
            )

            remaining_parts -= parts_today
            current_date += timedelta(days=1)

    return schedule


def find_free_date_for_equipment(
    worksheet_data: List[List[str]],
    headers: List[str],
    row_idx: int,
    start_date: str,
    max_days: int = MAX_SEARCH_DAYS,
) -> Optional[str]:
    """
    Находит ближайшую свободную дату для станка в строке.

    Args:
        worksheet_data: Данные таблицы
        headers: Заголовки (даты)
        row_idx: Индекс строки станка (1-based)
        start_date: Начальная дата в формате '%d.%m.%Y'
        max_days: Максимальное количество дней для поиска

    Returns:
        Свободная дата в формате '%d.%m.%Y' или None
    """
    headers_clean = {}
    for i, h in enumerate(headers, start=1):
        if h and "." in h and len(h) >= 8:
            headers_clean[h.strip()] = i

    row_data = worksheet_data[row_idx - 1] if row_idx <= len(worksheet_data) else []

    try:
        current_date = datetime.strptime(start_date, "%d.%m.%Y")
    except ValueError:
        return start_date

    for _ in range(max_days):
        date_str = current_date.strftime("%d.%m.%Y")

        col_idx = headers_clean.get(date_str)

        if col_idx:
            cell_val = row_data[col_idx - 1] if col_idx <= len(row_data) else None
            if is_cell_empty(cell_val):
                return date_str
        else:
            return date_str

        current_date += timedelta(days=1)
        while not is_working_day(current_date):
            current_date += timedelta(days=1)

    return None


def find_equipment_in_rows(
    equipment_rows: Dict[str, int], equip_name: str
) -> Optional[int]:
    """
    Находит строку станка в маппинге.

    Сначала ищет точное совпадение, затем частичное.

    Args:
        equipment_rows: Словарь {нормализованное_название: номер_строки}
        equip_name: Название станка для поиска

    Returns:
        Номер строки или None
    """
    equip_normalized = normalize_equipment(equip_name)

    if equip_normalized in equipment_rows:
        return equipment_rows[equip_normalized]

    for eq_key, row_idx in equipment_rows.items():
        if equip_normalized in eq_key or eq_key in equip_normalized:
            return row_idx

    return None


def build_cell_value(
    existing_value: Optional[str], parts: int, detail_name: str
) -> str:
    """
    Формирует значение для ячейки расписания.

    Args:
        existing_value: Существующее значение ячейки
        parts: Количество деталей
        detail_name: Название детали

    Returns:
        Строка для записи в ячейку
    """
    cell_value = f"{parts} шт {detail_name}"

    if existing_value and existing_value.strip():
        cell_value = f"{cell_value}, {existing_value}"

    return cell_value


# ============================================================================
# ФУНКЦИИ ДЛЯ РАБОТЫ С GOOGLE SHEETS
# ============================================================================


def parse_quantity_from_cell(cell_value: str) -> Optional[int]:
    """
    Извлекает количество штук из значения ячейки.

    Ищет паттерн типа "100 шт" или "50шт".

    Args:
        cell_value: Значение ячейки

    Returns:
        Количество или None
    """
    if not cell_value:
        return None

    match = re.search(r"(\d+)\s*шт", cell_value, re.IGNORECASE)
    if match:
        return int(match.group(1))

    return None


def cell_matches_pattern(
    cell_value: str, detail_name: str, designation: str = ""
) -> bool:
    """
    Проверяет, соответствует ли ячейка шаблону поиска.

    Args:
        cell_value: Значение ячейки
        detail_name: Название детали
        designation: Обозначение детали

    Returns:
        True если соответствует
    """
    if not cell_value or not cell_value.strip():
        return False

    cell_lower = cell_value.lower()
    search_pattern = detail_name.lower() if detail_name else ""
    search_designation = designation.lower() if designation else ""

    if search_pattern and search_pattern in cell_lower:
        return True
    if search_designation and search_designation in cell_lower:
        return True

    return False


def filter_schedule_by_date_range(
    schedule: List[Dict],
    min_date: Optional[datetime] = None,
    max_date: Optional[datetime] = None,
) -> List[Dict]:
    """
    Фильтрует расписание по диапазону дат.

    Args:
        schedule: Список записей расписания
        min_date: Минимальная дата (включительно)
        max_date: Максимальная дата (включительно)

    Returns:
        Отфильтрованный список
    """
    result = []

    for item in schedule:
        date_str = item.get("date", "")
        try:
            item_date = datetime.strptime(date_str, "%d.%m.%Y")

            if min_date and item_date < min_date:
                continue
            if max_date and item_date > max_date:
                continue

            result.append(item)
        except ValueError:
            result.append(item)

    return result


# ============================================================================
# ФУНКЦИИ ДЛЯ РАБОТЫ С БД И СТАНКАМИ
# ============================================================================


def get_equipment_working_hours_from_settings(
    equipment_list: List[Dict], equipment_id: int, calendar_entry: Optional[Dict] = None
) -> int:
    """
    Получает рабочие часы для станка из настроек или календаря.

    Приоритет:
    1. Календарь записи (если is_working = False -> 0)
    2. Календарь записи (working_hours)
    3. default_working_hours в настройках станка
    4. WORKING_HOURS_PER_DAY по умолчанию

    Args:
        equipment_list: Список оборудования из БД
        equipment_id: ID станка
        calendar_entry: Запись из календаря (опционально)

    Returns:
        Количество рабочих часов
    """
    if calendar_entry is not None:
        if calendar_entry.get("is_working") == False:
            return 0
        if calendar_entry.get("working_hours"):
            return calendar_entry["working_hours"]

    for eq in equipment_list:
        if eq["id"] == equipment_id:
            return eq.get("default_working_hours", WORKING_HOURS_PER_DAY)

    return WORKING_HOURS_PER_DAY


def calculate_total_minutes(duration_minutes: int, quantity: int) -> int:
    """
    Рассчитывает общую длительность в минутах.

    Args:
        duration_minutes: Время на одну деталь
        quantity: Количество деталей

    Returns:
        Общее количество минут
    """
    return duration_minutes * quantity


def calculate_utilization_percent(
    scheduled_minutes: int, available_minutes: int
) -> float:
    """
    Рассчитывает процент загрузки.

    Args:
        scheduled_minutes: Запланированные минуты
        available_minutes: Доступные минуты

    Returns:
        Процент загрузки (0-100+)
    """
    if available_minutes <= 0:
        return 0
    return (scheduled_minutes / available_minutes) * 100


# ============================================================================
# КОНСТРУКТОРЫ РАСПИСАНИЯ
# ============================================================================


def create_schedule_item(
    date: datetime,
    equipment_name: str,
    operation_name: str,
    parts: int,
    duration_minutes: int,
    sequence_number: int,
) -> Dict:
    """
    Создаёт запись расписания.

    Args:
        date: Дата выполнения
        equipment_name: Название станка
        operation_name: Название операции
        parts: Количество деталей
        duration_minutes: Время на деталь
        sequence_number: Номер операции

    Returns:
        Словарь с записью расписания
    """
    return {
        "date": date.strftime("%Y-%m-%d"),
        "datetime": date,
        "equipment_name": equipment_name,
        "operation_name": operation_name,
        "parts": parts,
        "duration_minutes": duration_minutes,
        "operation_seq": sequence_number,
    }


def group_by_equipment(schedule: List[Dict]) -> Dict[str, Dict]:
    """
    Группирует записи расписания по оборудованию.

    Args:
        schedule: Список записей расписания

    Returns:
        Словарь {оборудование: {dates: set, parts: int}}
    """
    grouped = {}

    for item in schedule:
        equip = item.get("equipment_name", "Unknown")
        if equip not in grouped:
            grouped[equip] = {"dates": set(), "parts": 0}

        date = item.get("date", "")
        if date:
            grouped[equip]["dates"].add(date)

        parts = item.get("parts", 0)
        grouped[equip]["parts"] += parts

    return grouped


def format_schedule_message(
    schedule: List[Dict], start_date: str, end_date: str
) -> str:
    """
    Формирует текстовое сообщение о расписании.

    Args:
        schedule: Список записей
        start_date: Дата начала
        end_date: Дата окончания

    Returns:
        Текстовое сообщение
    """
    msg = "Заказ добавлен в план!\n"
    msg += f"Период: {start_date} - {end_date}\n"

    grouped = group_by_equipment(schedule)

    for equip, data in list(grouped.items())[:5]:
        dates_list = sorted(data["dates"])
        first_date = dates_list[0] if dates_list else ""
        last_date = dates_list[-1] if dates_list else ""
        msg += f"{equip}: {first_date} - {last_date} ({data['parts']} шт)\n"

    if len(grouped) > 5:
        msg += f"... и ещё {len(grouped) - 5} станков"

    return msg


# ============================================================================
# ВАЛИДАЦИЯ
# ============================================================================


def validate_schedule_data(
    order_data: Dict, operations: List[Dict]
) -> Tuple[bool, str]:
    """
    Валидирует данные для планирования.

    Args:
        order_data: Данные заказа
        operations: Список операций

    Returns:
        (is_valid, error_message)
    """
    if not order_data:
        return False, "Заказ не найден"

    if not operations:
        return False, "Нет операций в маршруте"

    for op in operations:
        # Пропускаем проверку для кооперативных операций (выполняются на стороннем предприятии)
        if not op.get("is_cooperation"):
            if not op.get("equipment_id") and not op.get("equipment_name"):
                return False, f"Операция {op.get('sequence_number', '?')} без станка"

    return True, ""


def get_order_priority(order_data: Dict, default: int = DEFAULT_PRIORITY) -> int:
    """
    Получает приоритет заказа.

    Args:
        order_data: Данные заказа
        default: Приоритет по умолчанию

    Returns:
        Значение приоритета
    """
    return order_data.get("priority", default)
