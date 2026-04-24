"""
Сервис для импорта данных из Excel в БД с сравнением и выборочным обновлением
"""

import logging
import math
import pandas as pd
import openpyxl
from typing import Dict, List, Any
from sqlalchemy import text

logger = logging.getLogger(__name__)

# Таблицы, которые НЕ обрабатываем при импорте
EXCLUDED_TABLES = {"items", "audit_log"}

# Поля, которые НЕ сравниваем (служебные)
SKIP_COMPARE_FIELDS = {"id", "created_at", "updated_at"}


class DbImportService:
    """Сервис для сравнительного импорта данных из Excel в БД"""

    def __init__(self, db_manager):
        """
        Args:
            db_manager: DatabaseManager экземпляр
        """
        self.db = db_manager

    def get_available_tables(self) -> List[str]:
        """
        Получить список таблиц БД для импорта (кроме audit_log).

        Returns:
            List[str]: Список имён таблиц
        """
        from sqlalchemy import text
        
        tables = []
        try:
            with self.db.get_session() as session:
                # Пробуем PostgreSQL (information_schema)
                try:
                    result = session.execute(text(
                        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name != 'audit_log' ORDER BY table_name"
                    ))
                    for row in result.fetchall():
                        tables.append(row[0])
                except Exception:
                    # Fallback для SQLite
                    result = session.execute(text(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT IN ('sqlite_sequence', 'audit_log') ORDER BY name"
                    ))
                    for row in result.fetchall():
                        tables.append(row[0])
                    
            logger.info(f"get_available_tables: returning {tables}")
        except Exception as e:
            logger.error(f"Error getting tables: {e}")
            # Fallback на SQLAlchemy metadata
            from models import Base
            for table in Base.metadata.sorted_tables:
                if table.name != 'audit_log':
                    tables.append(table.name)
        
        return tables

    def read_excel_sheets(self, file_path: str) -> Dict[str, pd.DataFrame]:
        """
        Чтение всех листов Excel файла.

        Args:
            file_path: Путь к Excel файлу

        Returns:
            Dict[имя_листа: DataFrame]
        """
        result = {}
        try:
            wb = openpyxl.load_workbook(file_path, data_only=True)

            for sheet_name in wb.sheetnames:
                try:
                    df = pd.read_excel(file_path, sheet_name=sheet_name, dtype=str)
                    df = df.fillna("")
                    # Убираем пробелы из названий колонок
                    df.columns = [str(c).strip() for c in df.columns]
                    if not df.empty:
                        result[sheet_name] = df
                        logger.info(
                            f"Read sheet '{sheet_name}': {len(df)} rows, {len(df.columns)} cols"
                        )
                except Exception as e:
                    logger.warning(f"Could not read sheet '{sheet_name}': {e}")

            wb.close()
        except Exception as e:
            logger.error(f"Error reading Excel file: {e}", exc_info=True)
            raise

        return result

    def get_table_columns(self, table_name: str) -> List[str]:
        """
        Получить список колонок таблицы из БД.

        Args:
            table_name: Имя таблицы

        Returns:
            List[str]: Список имён колонок
        """
        from models import Base

        for table in Base.metadata.sorted_tables:
            if table.name == table_name:
                return [col.name for col in table.columns]
        return []

    def get_table_column_types(self, table_name: str) -> Dict[str, type]:
        """
        Получить типы колонок таблицы из БД.

        Args:
            table_name: Имя таблицы

        Returns:
            Dict[str, type]: {имя_колонки: Python-тип}
        """
        from models import Base
        from sqlalchemy import Float, Integer, Numeric, String, DateTime, Date, Boolean

        type_map = {
            Float: float,
            Integer: int,
            Numeric: float,
            String: str,
            DateTime: str,
            Date: str,
            Boolean: bool,
        }

        for table in Base.metadata.sorted_tables:
            if table.name == table_name:
                result = {}
                for col in table.columns:
                    col_type = type(col.type)
                    result[col.name] = type_map.get(col_type, str)
                return result
        return {}

    def _convert_value_for_db(self, val, target_type: type):
        """
        Конвертировать значение в тип БД.

        Args:
            val: Значение из Excel (обычно строка)
            target_type: Целевой Python-тип

        Returns:
            Конвертированное значение или исходное если конвертация не удалась
        """
        if val is None or val == "":
            return None

        if target_type is float:
            try:
                cleaned = str(val).replace(",", ".").strip()
                return float(cleaned)
            except (ValueError, TypeError):
                return None
        elif target_type is int:
            try:
                cleaned = str(val).replace(",", ".").strip()
                return int(float(cleaned))
            except (ValueError, TypeError):
                return None
        elif target_type is bool:
            if isinstance(val, str):
                return val.lower() in ("true", "1", "yes", "да")
            return bool(val)
        else:
            return str(val) if val is not None else None

    def get_table_data(self, table_name: str) -> List[Dict]:
        """
        Получить все данные из таблицы БД.

        Args:
            table_name: Имя таблицы

        Returns:
            List[Dict]: Список строк в виде словарей
        """
        try:
            with self.db.get_session() as session:
                query = text(f'SELECT * FROM "{table_name}"')
                result = session.execute(query)
                columns = list(result.keys())
                rows = result.fetchall()

                table_data = []
                for row in rows:
                    row_dict = {}
                    for col_name in columns:
                        val = dict(zip(columns, row))[col_name]
                        if hasattr(val, "isoformat"):
                            val = val.isoformat()
                        elif isinstance(val, bytes):
                            val = val.decode("utf-8", errors="replace")
                        elif isinstance(val, bool):
                            val = str(val)
                        elif isinstance(val, (int, float)):
                            val = str(val)
                        row_dict[col_name] = val if val is not None else ""
                    table_data.append(row_dict)

                logger.info(f"Read {len(table_data)} rows from '{table_name}'")
                logger.info(f"First 3 rows from '{table_name}': {table_data[:3]}")
                return table_data

        except Exception as e:
            logger.error(f"Error reading table '{table_name}': {e}", exc_info=True)
            return []

    def compare_table_data(
        self, table_name: str, excel_df: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Сравнить данные из Excel с данными в БД по полю id.

        Args:
            table_name: Имя таблицы
            excel_df: DataFrame из Excel

        Returns:
            Dict с результатами сравнения:
            - rows_to_add: список новых строк
            - rows_to_update: список изменённых строк с деталями
            - rows_unchanged: количество без изменений
            - total_excel: всего строк в Excel
            - total_db: всего строк в БД
            - matched_by_id: сколько найдено совпадений по id
        """
        logger.info(f"=== compare_table_data START for '{table_name}' ===")
        logger.info(f"Excel df shape: {excel_df.shape}, columns: {list(excel_df.columns)}")
        
        result = {
            "table_name": table_name,
            "rows_to_add": [],
            "rows_to_update": [],
            "rows_unchanged": 0,
            "total_excel": len(excel_df),
            "total_db": 0,
            "matched_by_id": 0,
            "columns_excel": list(excel_df.columns),
            "columns_db": self.get_table_columns(table_name),
        }

        # Получаем данные из БД
        db_data = self.get_table_data(table_name)
        result["total_db"] = len(db_data)

        if not db_data:
            # Если таблица пустая, все строки из Excel - новые
            for idx, row in excel_df.iterrows():
                row_dict = {}
                for col in excel_df.columns:
                    val = row.get(col, "")
                    if pd.isna(val) or str(val).lower() == "nan":
                        val = ""
                    row_dict[str(col).strip()] = str(val).strip()
                result["rows_to_add"].append(
                    {"row_index": idx, "data": row_dict, "changes": {}}
                )
            return result

        # Создаём индекс БД по id
        db_by_id = {}
        for db_row in db_data:
            row_id = str(db_row.get("id", "")).strip()
            if row_id:
                db_by_id[row_id] = db_row

        # Определяем колонку id в Excel
        id_col_excel = None
        for col in excel_df.columns:
            if str(col).strip().lower() == "id":
                id_col_excel = col
                break

        if not id_col_excel:
            logger.warning(f"No 'id' column found in Excel for table '{table_name}'")
            # Все строки - новые
            for idx, row in excel_df.iterrows():
                row_dict = {}
                for col in excel_df.columns:
                    val = row.get(col, "")
                    if pd.isna(val) or str(val).lower() == "nan":
                        val = ""
                    row_dict[str(col).strip()] = str(val).strip()
                result["rows_to_add"].append(
                    {"row_index": idx, "data": row_dict, "changes": {}}
                )
            return result

        # Проходим по строкам Excel
        for idx, row in excel_df.iterrows():
            excel_id = str(row.get(id_col_excel, "")).strip()
            if not excel_id or excel_id.lower() == "nan":
                continue

            # Собираем данные строки Excel
            excel_row = {}
            for col in excel_df.columns:
                val = row.get(col, "")
                if pd.isna(val) or str(val).lower() == "nan":
                    val = ""
                excel_row[str(col).strip()] = str(val).strip()

            if excel_id in db_by_id:
                # Строка есть в БД - сравниваем
                result["matched_by_id"] += 1
                db_row = db_by_id[excel_id]
                changes = self._compare_row(table_name, excel_row, db_row)

                logger.info(f"Row {excel_id}: db_row={db_row}, excel_row={excel_row}")
                logger.info(f"Row {excel_id} changes: {changes}")

                if changes:
                    result["rows_to_update"].append(
                        {
                            "row_index": idx,
                            "id": excel_id,
                            "excel_data": excel_row,
                            "db_data": db_row,
                            "changes": changes,
                        }
                    )
                else:
                    result["rows_unchanged"] += 1
            else:
                # Строки нет в БД - добавляем
                result["rows_to_add"].append(
                    {"row_index": idx, "data": excel_row, "changes": {}}
                )

        logger.info(
            f"Comparison for '{table_name}': "
            f"to_add={len(result['rows_to_add'])}, "
            f"to_update={len(result['rows_to_update'])}, "
            f"unchanged={result['rows_unchanged']}"
        )
        
        logger.info(f"=== compare_table_data END for '{table_name}' ===")
        logger.info(f"Result: {result}")

        return result

    def _compare_row(
        self, table_name: str, excel_row: Dict, db_row: Dict
    ) -> Dict[str, Dict]:
        """
        Сравнить одну строку Excel с строкой из БД.

        Args:
            table_name: Имя таблицы
            excel_row: Данные из Excel
            db_row: Данные из БД

        Returns:
            Dict[имя_поля: {old: старое, new: новое}] или пустой dict если нет изменений
        """
        changes = {}
        db_columns = self.get_table_columns(table_name)
        
        logger.info(f"_compare_row: db_columns={db_columns}")
        logger.info(f"_compare_row: excel_row={excel_row}")
        logger.info(f"_compare_row: db_row={db_row}")

        for col in db_columns:
            if col in SKIP_COMPARE_FIELDS:
                continue

            # Получаем значение из Excel по имени колонки БД
            excel_val = ""
            for excel_col, val in excel_row.items():
                if str(excel_col).strip().lower() == col.lower():
                    excel_val = val
                    break

            # Получаем значение из БД
            db_val = db_row.get(col, "")
            if db_val is None:
                db_val = ""
            
            # Нормализуем для сравнения - приводим к float если возможно
            excel_val_norm = self._normalize_value(str(excel_val))
            db_val_norm = self._normalize_value(str(db_val))
            
            logger.info(f"  Field '{col}': excel='{excel_val}' (raw={type(excel_val).__name__}) -> norm='{excel_val_norm}' vs db='{db_val}' -> norm='{db_val_norm}'")

            if excel_val_norm != db_val_norm:
                # Дополнительная проверка: если оба значения numeric, сравниваем как числа
                try:
                    excel_num = float(str(excel_val).replace(",", ".").replace("\xa0", "").replace(" ", ""))
                    db_num = float(str(db_val).replace(",", ".").replace("\xa0", "").replace(" ", ""))
                    if excel_num == db_num:
                        logger.info(f"    -> Same numeric value, no change")
                        continue
                except (ValueError, TypeError):
                    pass
                
                changes[col] = {"old": db_val, "new": excel_val}
                logger.info(f"    -> CHANGE detected")

        return changes

    def _normalize_value(self, val: str) -> str:
        """
        Нормализация значения для сравнения.

        Args:
            val: Строковое значение

        Returns:
            str: Нормализованное значение
        """
        if not val:
            return ""
        val = str(val).strip()
        
        # Приводим boolean строку к единому формату
        if val.lower() in ("true", "1", "да", "yes"):
            return "true"
        if val.lower() in ("false", "0", "нет", "no"):
            return "false"

        # Очищаем пробелы и NBSP для числовых значений
        cleaned = val.replace("\xa0", "").replace("\u00a0", "").replace(" ", "")

        # Пробуем преобразовать в float и обратно в строку
        try:
            num = float(cleaned.replace(",", "."))
            # Проверяем на inf и nan
            if math.isinf(num) or math.isnan(num):
                return cleaned
            # Если это целое число, убираем .0
            if num == int(num):
                return str(int(num))
            return str(num)
        except (ValueError, OverflowError):
            return val

    def _clean_value_for_db(self, val) -> str:
        """
        Очистка значения для записи в БД.
        Убирает неразрывные пробелы, обычные пробелы в числах.

        Args:
            val: Значение из Excel

        Returns:
            str: Очищенное значение
        """
        if val is None:
            return ""
        val = str(val)
        # Убираем неразрывные пробелы (NBSP)
        val = val.replace("\xa0", "").replace("\u00a0", "")
        # Убираем обычные пробелы если строка выглядит как число
        cleaned = val.replace(" ", "")
        try:
            float(cleaned.replace(",", "."))
            return cleaned
        except ValueError:
            return val

    def apply_import(
        self,
        table_name: str,
        rows_to_add: List[Dict],
        rows_to_update: List[Dict],
        selected_add: List[int],
        selected_update: List[int],
    ) -> Dict[str, int]:
        """
        Применить изменения в БД.

        Args:
            table_name: Имя таблицы
            rows_to_add: Список новых строк
            rows_to_update: Список изменённых строк
            selected_add: Индексы выбранных строк для добавления
            selected_update: Индексы выбранных строк для обновления

        Returns:
            Dict со статистикой: {added: int, updated: int, errors: int}
        """
        stats = {"added": 0, "updated": 0, "errors": 0}
        db_columns = self.get_table_columns(table_name)

        # Добавление новых строк
        for idx in selected_add:
            if idx >= len(rows_to_add):
                continue
            row_data = rows_to_add[idx].get("data", {})
            try:
                self._insert_row(table_name, db_columns, row_data)
                stats["added"] += 1
            except Exception as e:
                logger.error(f"Error inserting row {idx} in '{table_name}': {e}")
                stats["errors"] += 1

        # Обновление существующих строк
        for idx in selected_update:
            if idx >= len(rows_to_update):
                continue
            row_info = rows_to_update[idx]
            row_id = row_info.get("id")
            changes = row_info.get("changes", {})
            try:
                self._update_row(table_name, row_id, changes)
                stats["updated"] += 1
            except Exception as e:
                logger.error(f"Error updating row id={row_id} in '{table_name}': {e}")
                stats["errors"] += 1

        logger.info(f"Import to '{table_name}': {stats}")
        return stats

    def _insert_row(self, table_name: str, db_columns: List[str], row_data: Dict):
        """
        Вставить новую строку в таблицу.
        """
        column_types = self.get_table_column_types(table_name)

        # Фильтруем только колонки которые есть в БД
        insert_data = {}
        for col in db_columns:
            val = ""
            for excel_col, excel_val in row_data.items():
                if str(excel_col).strip().lower() == col.lower():
                    val = self._clean_value_for_db(excel_val)
                    break

            if val or val == 0:
                # Конвертируем значение в тип БД
                target_type = column_types.get(col, str)
                insert_data[col] = self._convert_value_for_db(val, target_type)

        if not insert_data:
            return

        # Не вставляем id если он не задан
        if "id" in insert_data and not insert_data["id"]:
            del insert_data["id"]

        columns_str = ", ".join(f'"{k}"' for k in insert_data.keys())
        placeholders = ", ".join(f":{k}" for k in insert_data.keys())

        query = text(
            f'INSERT INTO "{table_name}" ({columns_str}) VALUES ({placeholders})'
        )

        with self.db.get_session() as session:
            session.execute(query, insert_data)

    def _update_row(self, table_name: str, row_id: str, changes: Dict[str, Dict]):
        """
        Обновить существующую строку в таблице.
        """
        if not changes:
            return

        column_types = self.get_table_column_types(table_name)
        set_parts = []
        params = {"_row_id": row_id}

        for col, change_info in changes.items():
            new_val = change_info.get("new", "")
            new_val = self._clean_value_for_db(new_val)

            target_type = column_types.get(col, str)
            converted_val = self._convert_value_for_db(new_val, target_type)

            param_name = f"param_{col}"
            set_parts.append(f'"{col}" = :{param_name}')
            params[param_name] = converted_val

        set_clause = ", ".join(set_parts)
        query = text(f'UPDATE "{table_name}" SET {set_clause} WHERE id = :_row_id')

        with self.db.get_session() as session:
            session.execute(query, params)

    def find_matching_sheets(
        self, excel_sheets: Dict[str, pd.DataFrame]
    ) -> Dict[str, str]:
        """
        Сопоставить листы Excel с таблицами БД.

        Args:
            excel_sheets: {имя_листа: DataFrame}

        Returns:
            Dict[имя_таблицы: имя_листа]
        """
        db_tables = self.get_available_tables()
        matching = {}

        for sheet_name in excel_sheets.keys():
            sheet_lower = sheet_name.strip().lower()

            for table_name in db_tables:
                table_lower = table_name.lower()

                # Точное совпадение
                if sheet_lower == table_lower:
                    matching[table_name] = sheet_name
                    break

                # Совпадение с учётом подчёркиваний/пробелов
                sheet_norm = sheet_lower.replace("_", "").replace(" ", "")
                table_norm = table_lower.replace("_", "").replace(" ", "")
                if sheet_norm == table_norm:
                    matching[table_name] = sheet_name
                    break

        logger.info(f"Matched sheets to tables: {matching}")
        return matching

    # Wrapper методы для API
    def compare_with_database(self, table_name: str, excel_df) -> Dict[str, Any]:
        """Обёртка для compare_table_data - возвращает данные в формате для UI"""
        result = self.compare_table_data(table_name, excel_df)
        
        # Преобразуем в формат для UI
        ui_result = {
            "table_name": result["table_name"],
            "total_excel": result["total_excel"],
            "total_db": result["total_db"],
            "unchanged": result["rows_unchanged"],
            "updated": len(result["rows_to_update"]),
            "new_items": len(result["rows_to_add"]),
            "changes": [],  # For UI - details of changes
            "new": [],      # For UI - new items
            "rows_to_update": result["rows_to_update"],
            "rows_to_add": result["rows_to_add"],
            "columns_excel": result["columns_excel"],
            "columns_db": result["columns_db"],
            "matched_by_id": result["matched_by_id"]
        }
        
        # Формируем changes для UI
        for row_info in result["rows_to_update"]:
            ui_result["changes"].append({
                "id": row_info.get("id"),
                "fields": row_info.get("changes", {})
            })
        
        # Формируем new для UI
        for row in result["rows_to_add"]:
            ui_result["new"].append(row.get("data", {}))
        
        return ui_result

    def import_to_database(self, table_name: str, excel_df,
                          update_existing: bool = True,
                          insert_new: bool = True) -> Dict[str, int]:
        """
        Импорт данных из Excel в таблицу БД.

        Args:
            table_name: Имя таблицы
            excel_df: DataFrame из Excel
            update_existing: Обновлять существующие записи
            insert_new: Добавлять новые записи

        Returns:
            Dict со статистикой: {updated: int, inserted: int, errors: int}
        """
        comparison = self.compare_table_data(table_name, excel_df)

        stats = {"updated": 0, "inserted": 0, "errors": 0}
        db_columns = self.get_table_columns(table_name)

        # Обновление существующих строк
        if update_existing:
            for row_info in comparison.get('rows_to_update', []):
                row_id = row_info.get("id")
                changes = row_info.get("changes", {})
                if changes:
                    try:
                        self._update_row(table_name, row_id, changes)
                        stats["updated"] += 1
                    except Exception as e:
                        logger.error(f"Error updating row id={row_id}: {e}")
                        stats["errors"] += 1

        # Добавление новых строк
        if insert_new:
            for row in comparison.get('rows_to_add', []):
                row_data = row.get("data", {})
                if row_data:
                    try:
                        self._insert_row(table_name, db_columns, row_data)
                        stats["inserted"] += 1
                    except Exception as e:
                        logger.error(f"Error inserting row: {e}")
                        stats["errors"] += 1

        logger.info(f"Import to '{table_name}': {stats}")
        return stats

    def create_table_from_excel(self, table_name: str, excel_df, use_app_id: bool = True) -> Dict[str, Any]:
        """
        Создать новую таблицу в БД на основе структуры DataFrame из Excel.
        
        Args:
            table_name: Имя таблицы для создания
            excel_df: DataFrame из Excel с колонками для создания таблицы
            use_app_id: Использовать app_id как уникальный идентификатор
            
        Returns:
            Dict с результатом: {success: bool, columns_created: int, error: str}
        """
        from sqlalchemy import text
        from models import Base
        from database import engine
        
        try:
            # Получаем список существующих таблиц
            existing_tables = self.get_available_tables()
            
            # Проверяем, существует ли таблица
            normalized_name = table_name.strip().lower().replace(' ', '_').replace('-', '_')
            if normalized_name in [t.lower() for t in existing_tables]:
                return {
                    'success': False,
                    'error': f'Таблица "{table_name}" уже существует в базе данных',
                    'columns_created': 0
                }
            
            # Формируем колонки для CREATE TABLE
            columns_def = ['id INTEGER PRIMARY KEY AUTOINCREMENT']
            
            # Получаем колонки из Excel
            excel_columns = list(excel_df.columns)
            
            for col in excel_columns:
                col_normalized = str(col).strip()
                if col_normalized.lower() in ('id', 'created_at', 'updated_at'):
                    continue
                    
                # Тип данных по умолчанию - TEXT
                sql_type = 'TEXT'
                
                # Пробуем определить тип по данным
                sample_values = excel_df[col].dropna().head(10)
                if len(sample_values) > 0:
                    try:
                        # Проверяем на числа
                        numeric_vals = pd.to_numeric(sample_values, errors='coerce')
                        if numeric_vals.notna().sum() == len(sample_values):
                            if all(numeric_vals == numeric_vals.astype(int)):
                                sql_type = 'INTEGER'
                            else:
                                sql_type = 'REAL'
                    except:
                        pass
                
                # Имя колонки (sanitize)
                safe_col_name = col_normalized.replace(' ', '_').replace('-', '_').replace('.', '_')
                safe_col_name = ''.join(c for c in safe_col_name if c.isalnum() or c == '_')
                if safe_col_name[0].isdigit():
                    safe_col_name = 'col_' + safe_col_name
                
                columns_def.append(f'"{safe_col_name}" {sql_type}')
            
            # Добавляем timestamps
            columns_def.append('created_at TEXT')
            columns_def.append('updated_at TEXT')
            
            # Создаём таблицу
            create_sql = f'CREATE TABLE "{table_name}" ({", ".join(columns_def)})'
            
            logger.info(f"Creating table '{table_name}': {create_sql}")
            
            with self.db.get_session() as session:
                session.execute(text(create_sql))
                session.commit()
            
            # Регистрируем таблицу в SQLAlchemy metadata
            # Это нужно чтобы таблица появилась в get_available_tables() после создания
            
            return {
                'success': True,
                'table_name': table_name,
                'columns_created': len(columns_def),
                'columns': excel_columns
            }
            
        except Exception as e:
            logger.error(f"Error creating table '{table_name}': {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'columns_created': 0
            }
    
    def detect_new_tables(self, excel_sheets: Dict[str, pd.DataFrame]) -> List[Dict[str, Any]]:
        """
        Определить какие листы Excel соответствуют новым таблицам ( которых нет в БД).
        
        Args:
            excel_sheets: {имя_листа: DataFrame}
            
        Returns:
            List[Dict] с информацией о новых таблицах
        """
        existing_tables = self.get_available_tables()
        
        # Нормализуем названия таблиц для сравнения (без учета регистра и спецсимволов)
        def normalize(name):
            return name.strip().lower().replace(' ', '').replace('_', '').replace('-', '')
        
        existing_normalized = {normalize(t): t for t in existing_tables}
        
        logger.info(f"detect_new_tables: existing_tables = {existing_tables}")
        
        new_tables = []
        for sheet_name, df in excel_sheets.items():
            sheet_normalized = normalize(sheet_name)
            
            # Проверяем точное совпадение
            matched = False
            for existing_norm, existing_orig in existing_normalized.items():
                # Точное совпадение после нормализации
                if sheet_normalized == existing_norm:
                    matched = True
                    logger.info(f"detect_new_tables: '{sheet_name}' matched with '{existing_orig}'")
                    break
            
            if not matched:
                logger.info(f"detect_new_tables: '{sheet_name}' is NEW")
                new_tables.append({
                    'sheet_name': sheet_name,
                    'table_name': sheet_name,  # Используем оригинальное имя
                    'rows': len(df),
                    'columns': list(df.columns),
                    'columns_count': len(df.columns)
                })
        
        return new_tables
    
    def get_table_structure(self, table_name: str) -> List[str]:
        """Получить список колонок таблицы"""
        return self.get_table_columns(table_name)
