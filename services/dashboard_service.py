"""
Сервис настраиваемых дашбордов - как в AppSheet
"""
from enum import Enum
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


class WidgetType(Enum):
    STAT_CARD = "stat_card"
    CHART = "chart"
    TABLE = "table"
    LIST = "list"
    GAUGE = "gauge"
    PROGRESS = "progress"
    TIMELINE = "timeline"
    ALERTS = "alerts"


class ChartType(Enum):
    BAR = "bar"
    LINE = "line"
    PIE = "pie"
    DONUT = "donut"
    AREA = "area"


@dataclass
class Widget:
    id: str
    type: WidgetType
    title: str
    data_source: str = ""
    config: Dict[str, Any] = field(default_factory=dict)
    position: Dict[str, int] = field(default_factory=lambda: {"x": 0, "y": 0, "w": 1, "h": 1})
    style: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Dashboard:
    name: str
    id: Optional[int] = None
    description: str = ""
    owner_id: int = 0
    is_default: bool = False
    is_shared: bool = False
    widgets: List[Widget] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


WIDGET_TEMPLATES = {
    "total_items": {
        "type": WidgetType.STAT_CARD,
        "title": "Всего позиций",
        "data_source": "items",
        "config": {"icon": "inventory_2", "color": "blue"}
    },
    "low_stock": {
        "type": WidgetType.ALERTS,
        "title": "Заканчивается",
        "data_source": "low_stock_items",
        "config": {"icon": "warning", "color": "orange"}
    },
    "recent_transactions": {
        "type": WidgetType.LIST,
        "title": "Последние операции",
        "data_source": "transactions",
        "config": {"limit": 10, "icon": "swap_horiz"}
    },
    "inventory_by_category": {
        "type": WidgetType.CHART,
        "title": "По категориям",
        "data_source": "items_by_category",
        "config": {"chart_type": ChartType.PIE}
    },
    "stock_level": {
        "type": WidgetType.GAUGE,
        "title": "Заполненность",
        "data_source": "stock_level",
        "config": {"max_value": 100, "icon": "inventory"}
    },
    "daily_movement": {
        "type": WidgetType.CHART,
        "title": "Движение за день",
        "data_source": "daily_transactions",
        "config": {"chart_type": ChartType.BAR}
    },
    "workshop_status": {
        "type": WidgetType.TIMELINE,
        "title": "Статус цехов",
        "data_source": "workshops",
        "config": {"icon": "factory"}
    },
}


class DashboardService:
    """Сервис для управления дашбордами"""
    
    def __init__(self, db=None):
        self.db = db
        self._dashboards: Dict[int, List[Dashboard]] = {}
    
    def get_user_dashboards(self, user_id: int) -> List[Dashboard]:
        """Получение дашбордов пользователя"""
        return self._dashboards.get(user_id, [self._create_default_dashboard()])
    
    def get_default_dashboard(self, user_id: int) -> Dashboard:
        """Получение дашборда по умолчанию"""
        user_dashboards = self.get_user_dashboards(user_id)
        for dashboard in user_dashboards:
            if dashboard.is_default:
                return dashboard
        return user_dashboards[0] if user_dashboards else self._create_default_dashboard()
    
    def _create_default_dashboard(self) -> Dashboard:
        """Создание дашборда по умолчанию"""
        widgets = [
            Widget(
                id="total_items",
                type=WidgetType.STAT_CARD,
                title="Всего позиций",
                data_source="items",
                config={"icon": "inventory_2", "color": "blue"},
                position={"x": 0, "y": 0, "w": 1, "h": 1}
            ),
            Widget(
                id="low_stock",
                type=WidgetType.ALERTS,
                title="Заканчивается",
                data_source="low_stock_items",
                config={"icon": "warning", "color": "orange"},
                position={"x": 1, "y": 0, "w": 1, "h": 1}
            ),
            Widget(
                id="recent_transactions",
                type=WidgetType.LIST,
                title="Последние операции",
                data_source="transactions",
                config={"limit": 10, "icon": "swap_horiz"},
                position={"x": 2, "y": 0, "w": 1, "h": 2}
            ),
            Widget(
                id="inventory_by_category",
                type=WidgetType.CHART,
                title="По категориям",
                data_source="items_by_category",
                config={"chart_type": ChartType.PIE},
                position={"x": 0, "y": 1, "w": 2, "h": 1}
            ),
        ]
        
        return Dashboard(
            name="Главная",
            description="Основной дашборд",
            is_default=True,
            widgets=widgets
        )
    
    def create_dashboard(self, user_id: int, name: str, description: str = "") -> Dashboard:
        """Создание нового дашборда"""
        dashboard = Dashboard(
            name=name,
            description=description,
            owner_id=user_id,
            widgets=[]
        )
        
        if user_id not in self._dashboards:
            self._dashboards[user_id] = []
        self._dashboards[user_id].append(dashboard)
        
        return dashboard
    
    def add_widget(self, user_id: int, dashboard_name: str, widget: Widget):
        """Добавление виджета на дашборд"""
        dashboards = self._dashboards.get(user_id, [])
        for dashboard in dashboards:
            if dashboard.name == dashboard_name:
                dashboard.widgets.append(widget)
                return True
        return False
    
    def remove_widget(self, user_id: int, dashboard_name: str, widget_id: str):
        """Удаление виджета"""
        dashboards = self._dashboards.get(user_id, [])
        for dashboard in dashboards:
            if dashboard.name == dashboard_name:
                dashboard.widgets = [w for w in dashboard.widgets if w.id != widget_id]
                return True
        return False
    
    def update_widget_position(self, user_id: int, dashboard_name: str, widget_id: str, position: Dict[str, int]):
        """Обновление позиции виджета"""
        dashboards = self._dashboards.get(user_id, [])
        for dashboard in dashboards:
            if dashboard.name == dashboard_name:
                for widget in dashboard.widgets:
                    if widget.id == widget_id:
                        widget.position = position
                        return True
        return False
    
    def get_available_widgets(self) -> List[Dict[str, Any]]:
        """Получение списка доступных виджетов"""
        return [
            {"id": k, "name": v["title"], "type": v["type"].value}
            for k, v in WIDGET_TEMPLATES.items()
        ]


def create_stat_widget_data(db, config: Dict[str, Any]) -> Dict[str, Any]:
    """Создание данных для статистического виджета"""
    if config.get("data_source") == "items":
        from models import Item
        count = db.session.query(Item).count()
        return {"value": count, "label": "позиций", "trend": None}
    elif config.get("data_source") == "low_stock_items":
        from models import Item
        items = db.session.query(Item).filter(Item.quantity <= Item.min_stock).all()
        return {"count": len(items), "items": [i.to_dict() for i in items[:5]]}
    return {}
