"""
Система автоматизации (Bots) - как в AppSheet
"""
from enum import Enum
from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class TriggerType(Enum):
    INVENTORY_LOW = "inventory_low"
    INVENTORY_CREATED = "inventory_created"
    INVENTORY_UPDATED = "inventory_updated"
    INVENTORY_DELETED = "inventory_deleted"
    
    TRANSACTION_CREATED = "transaction_created"
    TRANSACTION_UPDATED = "transaction_updated"
    
    ROUTE_CREATED = "route_created"
    ROUTE_UPDATED = "route_updated"
    ROUTE_COMPLETED = "route_completed"
    
    USER_CREATED = "user_created"
    USER_LOGIN = "user_login"
    
    SCHEDULED = "scheduled"


class ActionType(Enum):
    SEND_NOTIFICATION = "send_notification"
    UPDATE_FIELD = "update_field"
    CREATE_RECORD = "create_record"
    DELETE_RECORD = "delete_record"
    RUN_SCRIPT = "run_script"
    SEND_EMAIL = "send_email"
    WEBHOOK = "webhook"


@dataclass
class Trigger:
    type: TriggerType
    conditions: Dict[str, Any] = field(default_factory=dict)
    schedule: Optional[str] = None


@dataclass
class Action:
    type: ActionType
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Bot:
    name: str
    id: Optional[int] = None
    description: str = ""
    enabled: bool = True
    triggers: List[Trigger] = field(default_factory=list)
    actions: List[Action] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


TRIGGER_LABELS = {
    TriggerType.INVENTORY_LOW: "Остаток на складе ниже минимума",
    TriggerType.INVENTORY_CREATED: "Создана новая позиция",
    TriggerType.INVENTORY_UPDATED: "Обновлена позиция",
    TriggerType.INVENTORY_DELETED: "Удалена позиция",
    TriggerType.TRANSACTION_CREATED: "Создана транзакция",
    TriggerType.TRANSACTION_UPDATED: "Обновлена транзакция",
    TriggerType.ROUTE_CREATED: "Создан маршрут",
    TriggerType.ROUTE_UPDATED: "Обновлен маршрут",
    TriggerType.ROUTE_COMPLETED: "Маршрут завершен",
    TriggerType.USER_CREATED: "Создан пользователь",
    TriggerType.USER_LOGIN: "Вход пользователя",
    TriggerType.SCHEDULED: "По расписанию",
}

ACTION_LABELS = {
    ActionType.SEND_NOTIFICATION: "Отправить уведомление",
    ActionType.UPDATE_FIELD: "Обновить поле",
    ActionType.CREATE_RECORD: "Создать запись",
    ActionType.DELETE_RECORD: "Удалить запись",
    ActionType.RUN_SCRIPT: "Выполнить скрипт",
    ActionType.SEND_EMAIL: "Отправить email",
    ActionType.WEBHOOK: "Вызвать webhook",
}


class AutomationService:
    """Сервис для управления автоматизацией (ботами)"""
    
    def __init__(self, db=None):
        self.db = db
        self._bots: Dict[str, Bot] = {}
        self._event_handlers: Dict[TriggerType, List[Callable]] = {}
    
    def register_bot(self, bot: Bot):
        """Регистрация бота"""
        self._bots[bot.name] = bot
        for trigger in bot.triggers:
            if trigger.type not in self._event_handlers:
                self._event_handlers[trigger.type] = []
            self._event_handlers[trigger.type].append(bot)
    
    def unregister_bot(self, bot_name: str):
        """Удаление бота"""
        if bot_name in self._bots:
            bot = self._bots.pop(bot_name)
            for trigger in bot.triggers:
                if trigger.type in self._event_handlers:
                    self._event_handlers[trigger.type] = [
                        b for b in self._event_handlers[trigger.type] 
                        if b.name != bot_name
                    ]
    
    def trigger_event(self, trigger_type: TriggerType, context: Dict[str, Any]):
        """Запуск события для всех ботов"""
        if trigger_type not in self._event_handlers:
            return
        
        for bot in self._event_handlers[trigger_type]:
            if not bot.enabled:
                continue
            
            if not self._check_conditions(bot, context):
                continue
            
            self._execute_actions(bot, context)
    
    def _check_conditions(self, bot: Bot, context: Dict[str, Any]) -> bool:
        """Проверка условий запуска бота"""
        for trigger in bot.triggers:
            if trigger.type == TriggerType.INVENTORY_LOW:
                quantity = context.get('quantity', 0)
                min_stock = context.get('min_stock', 0)
                return quantity < min_stock
        return True
    
    def _execute_actions(self, bot: Bot, context: Dict[str, Any]):
        """Выполнение действий бота"""
        for action in bot.actions:
            try:
                if action.type == ActionType.SEND_NOTIFICATION:
                    self._send_notification(action.params, context)
                elif action.type == ActionType.UPDATE_FIELD:
                    self._update_field(action.params, context)
                elif action.type == ActionType.CREATE_RECORD:
                    self._create_record(action.params, context)
                elif action.type == ActionType.WEBHOOK:
                    self._webhook(action.params, context)
            except Exception as e:
                logger.error(f"Error executing action {action.type} for bot {bot.name}: {e}")
    
    def _send_notification(self, params: Dict[str, Any], context: Dict[str, Any]):
        """Отправка уведомления"""
        message = params.get('message', '').format(**context)
        title = params.get('title', 'Уведомление').format(**context)
        logger.info(f"NOTIFICATION: [{title}] {message}")
    
    def _update_field(self, params: Dict[str, Any], context: Dict[str, Any]):
        """Обновление поля"""
        table = params.get('table')
        record_id = params.get('record_id')
        field = params.get('field')
        value = params.get('value', '').format(**context)
        logger.info(f"UPDATE: {table}.{record_id}.{field} = {value}")
    
    def _create_record(self, params: Dict[str, Any], context: Dict[str, Any]):
        """Создание записи"""
        table = params.get('table')
        data = params.get('data', {})
        formatted_data = {k: v.format(**context) if isinstance(v, str) else v for k, v in data.items()}
        logger.info(f"CREATE: {table} -> {formatted_data}")
    
    def _webhook(self, params: Dict[str, Any], context: Dict[str, Any]):
        """Вызов webhook"""
        url = params.get('url', '').format(**context)
        method = params.get('method', 'POST')
        logger.info(f"WEBHOOK: {method} {url}")
    
    def get_bots(self) -> List[Bot]:
        """Получение списка ботов"""
        return list(self._bots.values())
    
    def get_bot(self, name: str) -> Optional[Bot]:
        """Получение бота по имени"""
        return self._bots.get(name)
    
    def enable_bot(self, name: str):
        """Включение бота"""
        if name in self._bots:
            self._bots[name].enabled = True
    
    def disable_bot(self, name: str):
        """Выключение бота"""
        if name in self._bots:
            self._bots[name].enabled = False


def create_default_bots() -> List[Bot]:
    """Создание стандартных ботов"""
    bots = []
    
    bot1 = Bot(
        name="low_stock_alert",
        description="Уведомление о низком остатке",
        triggers=[Trigger(type=TriggerType.INVENTORY_LOW)],
        actions=[
            Action(
                type=ActionType.SEND_NOTIFICATION,
                params={
                    "title": "⚠️ Низкий остаток",
                    "message": "Товар {item_name} на складе: {quantity} (мин: {min_stock})"
                }
            )
        ]
    )
    bots.append(bot1)
    
    bot2 = Bot(
        name="new_transaction_alert",
        description="Уведомление о новой транзакции",
        triggers=[Trigger(type=TriggerType.TRANSACTION_CREATED)],
        actions=[
            Action(
                type=ActionType.SEND_NOTIFICATION,
                params={
                    "title": "📦 Новая транзакция",
                    "message": "Создана транзакция: {quantity} x {item_name}"
                }
            )
        ]
    )
    bots.append(bot2)
    
    return bots
