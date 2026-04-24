# services/google_sync_service.py
"""Сервис синхронизации с Google Sheets"""
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

class GoogleSyncService:
    def __init__(self, credentials_path: str, spreadsheet_id: str = None):
        self.credentials_path = credentials_path
        self.spreadsheet_id = spreadsheet_id
        self.executor = ThreadPoolExecutor(max_workers=2)
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
                logger.info("Google Sheets client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Google Sheets client: {e}")
                return None
        return self._client
    
    async def export_transactions_async(self, transactions: List[Dict], sheet_name: str = "Операции") -> bool:
        """Асинхронный экспорт транзакций в Google Sheets"""
        def _sync():
            try:
                client = self._get_client()
                if not client:
                    return False
                
                if not self.spreadsheet_id:
                    spreadsheet = client.create(f"Склад - {datetime.now().strftime('%Y-%m-%d')}")
                    self.spreadsheet_id = spreadsheet.id
                    logger.info(f"Created new spreadsheet: {self.spreadsheet_id}")
                
                spreadsheet = client.open_by_key(self.spreadsheet_id)
                
                try:
                    worksheet = spreadsheet.worksheet(sheet_name)
                except gspread.WorksheetNotFound:
                    worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=10)
                
                headers = ["ID", "Дата", "Пользователь", "Товар", "Тип", "Количество", "Детали", "Причина"]
                existing = worksheet.get_all_values()
                
                if not existing:
                    worksheet.append_row(headers)
                
                rows = []
                for t in transactions:
                    rows.append([
                        t.get('id', ''),
                        t.get('timestamp', ''),
                        t.get('username', ''),
                        t.get('item_name', ''),
                        t.get('operation_type', ''),
                        t.get('quantity', ''),
                        t.get('detail', ''),
                        t.get('reason', '')
                    ])
                
                if rows:
                    worksheet.append_rows(rows, value_input_option='USER_ENTERED')
                
                logger.info(f"Exported {len(rows)} transactions to {sheet_name}")
                return True
                
            except Exception as e:
                logger.error(f"Google Sheets sync error: {e}")
                return False
        
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self.executor, _sync)
    
    async def export_inventory_async(self, items: List[Dict], sheet_name: str = "Остатки") -> bool:
        """Асинхронный экспорт остатков товаров"""
        def _sync():
            try:
                client = self._get_client()
                if not client or not self.spreadsheet_id:
                    return False
                
                spreadsheet = client.open_by_key(self.spreadsheet_id)
                
                try:
                    worksheet = spreadsheet.worksheet(sheet_name)
                    worksheet.clear()
                except gspread.WorksheetNotFound:
                    worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=8)
                
                headers = ["ID товара", "Название", "Количество", "Мин. остаток", "Категория", "Место", "Статус"]
                worksheet.append_row(headers)
                
                rows = []
                for item in items:
                    status = "КРИТИЧНО" if item.get('quantity', 0) <= item.get('min_stock', 0) else "OK"
                    rows.append([
                        item.get('item_id', ''),
                        item.get('name', ''),
                        item.get('quantity', 0),
                        item.get('min_stock', 0),
                        item.get('category', ''),
                        item.get('location', ''),
                        status
                    ])
                
                worksheet.append_rows(rows, value_input_option='USER_ENTERED')
                logger.info(f"Exported {len(rows)} items to {sheet_name}")
                return True
                
            except Exception as e:
                logger.error(f"Google Sheets inventory sync error: {e}")
                return False
        
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self.executor, _sync)
    
    async def export_report_async(self, data: Dict[str, Any], report_type: str) -> bool:
        """Генерация и экспорт отчёта"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        
        if report_type == 'daily':
            sheet_name = f"Отчёт за {timestamp}"
            return await self.export_transactions_async(data.get('transactions', []), sheet_name)
        elif report_type == 'inventory':
            return await self.export_inventory_async(data.get('items', []), "Остатки")
        
        return False
    
    def get_spreadsheet_url(self) -> Optional[str]:
        """Получить URL таблицы"""
        if self.spreadsheet_id:
            return f"https://docs.google.com/spreadsheets/d/{self.spreadsheet_id}"
        return None
    
    async def import_from_sheets_async(self, db_session) -> Dict[str, Any]:
        """Асинхронный импорт товаров из Google Sheets"""
        from models import Item
        
        def _sync():
            try:
                client = self._get_client()
                if not client or not self.spreadsheet_id:
                    return {"success": False, "message": "Google Sheets не настроен"}
                
                spreadsheet = client.open_by_key(self.spreadsheet_id)
                worksheet = spreadsheet.sheet1
                
                records = worksheet.get_all_records()
                if not records:
                    return {"success": False, "message": "Таблица пуста"}
                
                imported = 0
                updated = 0
                
                for row in records:
                    item_id = str(row.get('ID номер', ''))
                    name = row.get('Имя', '')
                    category = row.get('Категория', '')
                    location = row.get('Место', '')
                    quantity = int(row.get('Остаток', 0) or 0)
                    min_stock = int(row.get('Минимальный остаток', 0) or 0)
                    
                    if not item_id or not name:
                        continue
                    
                    existing = db_session.query(Item).filter(Item.item_id == item_id).first()
                    
                    if existing:
                        existing.name = name
                        existing.category = category
                        existing.location = location
                        existing.quantity = quantity
                        existing.min_stock = min_stock
                        updated += 1
                    else:
                        item = Item(
                            item_id=item_id,
                            name=name,
                            category=category,
                            location=location,
                            quantity=quantity,
                            min_stock=min_stock
                        )
                        db_session.add(item)
                        imported += 1
                
                db_session.commit()
                logger.info(f"Imported {imported} new items, updated {updated} items from Google Sheets")
                return {"success": True, "imported": imported, "updated": updated}
                
            except Exception as e:
                logger.error(f"Google Sheets import error: {e}")
                return {"success": False, "message": str(e)}
        
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self.executor, _sync)
    
    def shutdown(self):
        """Очистка ресурсов"""
        self.executor.shutdown(wait=True)
        logger.info("GoogleSyncService shutdown")
