# services/google_export_service.py
"""Сервис экспорта производственного плана в Google Sheets"""
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]


class GoogleExportService:
    def __init__(self, credentials_path: str, spreadsheet_id: str = None):
        self.credentials_path = credentials_path
        self.spreadsheet_id = spreadsheet_id
        self._client = None
    
    def _get_client(self):
        """Ленивая инициализация клиента gspread"""
        if self._client is None:
            try:
                creds = Credentials.from_service_account_file(
                    self.credentials_path,
                    scopes=SCOPES
                )
                self._client = gspread.authorize(creds)
                logger.info("Google Sheets client initialized for export")
            except Exception as e:
                logger.error(f"Failed to initialize Google Sheets client: {e}")
                return None
        return self._client
    
    def export_production_schedule(self, schedule: List[Dict], 
                                   sheet_name: str = "План производства") -> Optional[str]:
        """Экспорт производственного плана в Google Sheets"""
        def _export():
            try:
                client = self._get_client()
                if not client:
                    return None
                
                if not self.spreadsheet_id:
                    spreadsheet = client.create(f"План производства - {datetime.now().strftime('%Y-%m-%d')}")
                    self.spreadsheet_id = spreadsheet.id
                    logger.info(f"Created new spreadsheet: {self.spreadsheet_id}")
                
                spreadsheet = client.open_by_key(self.spreadsheet_id)
                
                try:
                    worksheet = spreadsheet.worksheet(sheet_name)
                    worksheet.clear()
                except gspread.WorksheetNotFound:
                    worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=12)
                
                headers = [
                    "ID",
                    "Дата",
                    "Станок",
                    "Обозначение",
                    "Деталь",
                    "Операция",
                    "Количество",
                    "Дней",
                    "Статус",
                    "Приоритет"
                ]
                worksheet.append_row(headers)
                
                rows = []
                for item in schedule:
                    planned_date = item.get('planned_date', '')
                    if isinstance(planned_date, datetime):
                        planned_date = planned_date.strftime('%d.%m.%Y')
                    
                    status_text = {
                        'planned': 'Запланировано',
                        'in_progress': 'В работе',
                        'completed': 'Выполнено',
                        'delayed': 'Задержка'
                    }.get(item.get('status', ''), item.get('status', ''))
                    
                    rows.append([
                        item.get('id', ''),
                        planned_date,
                        item.get('equipment_name', ''),
                        item.get('designation', ''),
                        item.get('detail_name', ''),
                        item.get('operation_name', ''),
                        item.get('quantity', 1),
                        item.get('duration_days', 1),
                        status_text,
                        item.get('priority', 5)
                    ])
                
                if rows:
                    worksheet.append_rows(rows, value_input_option='USER_ENTERED')
                
                logger.info(f"Exported {len(rows)} schedule items to {sheet_name}")
                return self.spreadsheet_id
                
            except Exception as e:
                logger.error(f"Google Sheets export error: {e}")
                return None
        
        return _export()
    
    def export_equipment_load(self, load_data: Dict, 
                              sheet_name: str = "Загрузка станков") -> Optional[str]:
        """Экспорт загрузки станков"""
        def _export():
            try:
                client = self._get_client()
                if not client or not self.spreadsheet_id:
                    return None
                
                spreadsheet = client.open_by_key(self.spreadsheet_id)
                
                try:
                    worksheet = spreadsheet.worksheet(sheet_name)
                    worksheet.clear()
                except gspread.WorksheetNotFound:
                    worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=100, cols=6)
                
                headers = ["Станок", "Загружено (мин)", "Доступно (мин)", "Загрузка (%)"]
                worksheet.append_row(headers)
                
                rows = []
                for item in load_data:
                    rows.append([
                        item.get('equipment_name', ''),
                        item.get('total_scheduled_minutes', 0),
                        item.get('total_available_minutes', 0),
                        round(item.get('utilization_percent', 0), 1)
                    ])
                
                if rows:
                    worksheet.append_rows(rows, value_input_option='USER_ENTERED')

                logger.info(f"Exported {len(rows)} equipment load items")
                return self.spreadsheet_id

            except Exception as e:
                logger.error(f"Google Sheets equipment load export error: {e}")
                return None
        
        return _export()
    
    def get_spreadsheet_url(self) -> Optional[str]:
        """Получить URL таблицы"""
        if self.spreadsheet_id:
            return f"https://docs.google.com/spreadsheets/d/{self.spreadsheet_id}"
        return None
    
    def create_readonly_link(self) -> Optional[str]:
        """Создать ссылку только для чтения (публикация)"""
        if not self.spreadsheet_id:
            return None
        return f"https://docs.google.com/spreadsheets/d/{self.spreadsheet_id}/edit?usp=sharing"
