# roles.py
"""
Роли пользователей системы — единая сущность для управления правами и свойствами.
Каждая роль описывает: название, иконку, цвет, права экранов по умолчанию,
автоматические экраны (без отображения в UI), и дополнительные свойства.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Role:
    """Роль пользователя в системе."""
    id: str                              # уникальный идентификатор ( совпадает с role в БД)
    label: str                            # отображаемое имя роли
    description: str = ""                 # описание роли
    icon: str = "fa fa-user"             # FontAwesome иконка
    color: str = "gray"                  # цвет для UI (gray, blue, green, red, purple, orange)
    default_screens: list = field(default_factory=list)   # экраны по умолчанию
    auto_screens: list = field(default_factory=list)        # автоматические экраны (не в UI)
    is_admin: bool = False               # имеет права администратора
    can_manage_users: bool = False      # может управлять пользователями
    can_manage_planning: bool = False   # может управлять планированием
    can_view_reports: bool = False       # может видеть отчёты
    can_manage_equipment: bool = False   # может управлять оборудованием
    can_manage_routes: bool = False      # может управлять маршрутами
    can_manage_orders: bool = False      # может управлять заказами
    can_access_otk: bool = False        # имеет доступ к ОТК
    can_access_workshop_inventory: bool = False  # доступ к инструментам на станках

    # Кастомные свойства (для ролей с особыми требованиями)
    route_view_mode: str = "approved_only"  # режим просмотра маршрутов: approved_only, all, in_work
    is_mobile_allowed: bool = True         # разрешён мобильный доступ
    workstation_required: bool = False      # требуется указание рабочего места

    @property
    def all_screens(self) -> list:
        """Все доступные экраны для роли (default + auto)."""
        return list(set(self.default_screens) | set(self.auto_screens))

    def has_screen(self, screen_id: str) -> bool:
        """Проверить наличие экрана у роли."""
        return screen_id in self.all_screens

    def to_dict(self) -> dict:
        """Сериализация в словарь (для JSON/API)."""
        return {
            "id": self.id,
            "label": self.label,
            "description": self.description,
            "icon": self.icon,
            "color": self.color,
            "default_screens": self.default_screens,
            "auto_screens": self.auto_screens,
            "all_screens": self.all_screens,
            "permissions": {
                "is_admin": self.is_admin,
                "can_manage_users": self.can_manage_users,
                "can_manage_planning": self.can_manage_planning,
                "can_view_reports": self.can_view_reports,
                "can_manage_equipment": self.can_manage_equipment,
                "can_manage_routes": self.can_manage_routes,
                "can_manage_orders": self.can_manage_orders,
                "can_access_otk": self.can_access_otk,
                "can_access_workshop_inventory": self.can_access_workshop_inventory,
            },
            "route_view_mode": self.route_view_mode,
            "is_mobile_allowed": self.is_mobile_allowed,
            "workstation_required": self.workstation_required,
        }

    @classmethod
    def get_role(cls, role_id: str) -> "Role":
        """Получить роль по ID."""
        role = ROLES.get(role_id)
        if role is None:
            return ROLES["user"]  # Fallback на user
        return role

    @classmethod
    def get_all_roles(cls) -> dict:
        """Получить все роли."""
        return dict(ROLES)

    @classmethod
    def get_roles_list(cls) -> list:
        """Получить список всех ролей (для UI)."""
        return [
            {
                "id": r.id,
                "label": r.label,
                "description": r.description,
                "icon": r.icon,
                "color": r.color,
                "default_screens": r.default_screens,
            }
            for r in ROLES.values()
        ]


# ==================== ОПРЕДЕЛЕНИЕ РОЛЕЙ ====================

ROLES: dict[str, Role] = {

    # ─── Базовые роли (не трогаем) ───────────────────────────

    "user": Role(
        id="user",
        label="Пользователь",
        description="Базовый пользователь — доступ только к личной странице и складу",
        icon="fa fa-user",
        color="gray",
        default_screens=["dashboard", "inventory", "transactions"],
        auto_screens=["my_page"],          # автоматически добавляется, не в UI
        is_admin=False,
        workstation_required=True,
    ),

    "otk": Role(
        id="otk",
        label="ОТК",
        description="Отдел технического контроля — проверка и приёмка деталей",
        icon="fa fa-clipboard-check",
        color="orange",
        default_screens=["dashboard", "otk"],
        auto_screens=["otk", "order_card"],  # автоматически добавляется, не в UI
        is_admin=False,
        can_access_otk=True,
        route_view_mode="all",
    ),

    # ─── Складские роли ──────────────────────────────────────

    "storekeeper": Role(
        id="storekeeper",
        label="Кладовщик",
        description="Заведующий складом — управление инструментами и инвентарём",
        icon="fa fa-warehouse",
        color="yellow",
        default_screens=[
            "dashboard", "inventory", "transactions",
            "import_export", "workshop_inventory",
        ],
        auto_screens=["my_page"],
        is_admin=False,
        can_manage_equipment=True,
        can_access_workshop_inventory=True,
        workstation_required=True,
    ),

    # ─── Производственные роли ────────────────────────────────

    "technologist": Role(
        id="technologist",
        label="Технолог",
        description="Технолог — создание маршрутов и работа с материалами",
        icon="fa fa-tools",
        color="blue",
        default_screens=[
            "dashboard", "inventory", "details", "routes",
            "materials", "transactions",
        ],
        auto_screens=["my_page"],
        is_admin=False,
        can_manage_routes=True,
        can_manage_equipment=True,
    ),

    "technologist_designer": Role(
        id="technologist_designer",
        label="Технолог-конструктор",
        description="Технолог и конструктор — полный цикл разработки",
        icon="fa fa-drafting-compass",
        color="indigo",
        default_screens=[
            "dashboard", "details", "routes", "materials",
            "equipment", "transactions", "workshop_inventory",
        ],
        auto_screens=["my_page"],
        is_admin=False,
        can_manage_routes=True,
        can_manage_equipment=True,
        can_access_workshop_inventory=True,
    ),

    "master": Role(
        id="master",
        label="Мастер цеха",
        description="Мастер — управление производством на участке",
        icon="fa fa-hard-hat",
        color="purple",
        default_screens=[
            "dashboard", "inventory", "details", "routes",
            "materials", "equipment", "transactions", "workshop_inventory",
        ],
        auto_screens=["my_page"],
        is_admin=False,
        can_manage_routes=True,
        can_manage_equipment=True,
        can_manage_orders=True,
        can_view_reports=True,
        can_access_workshop_inventory=True,
    ),

    "foreman": Role(
        id="foreman",
        label="Начальник цеха",
        description="Начальник цеха — полный контроль участка и планирование",
        icon="fa fa-industry",
        color="purple",
        default_screens=[
            "dashboard", "inventory", "details", "routes",
            "materials", "equipment", "reports", "transactions",
            "workshop_inventory", "planning", "planning_calendar", "planning_gantt",
        ],
        auto_screens=["my_page"],
        is_admin=False,
        can_manage_routes=True,
        can_manage_equipment=True,
        can_manage_planning=True,
        can_view_reports=True,
        can_access_workshop_inventory=True,
    ),

    # ─── Инженерные роли ─────────────────────────────────────

    "chief_designer": Role(
        id="chief_designer",
        label="Главный конструктор",
        description="Главный конструктор — проектирование и управление маршрутами",
        icon="fa fa-drafting-compass",
        color="red",
        default_screens=[
            "dashboard", "details", "routes", "materials",
            "reports", "planning_settings", "transactions",
        ],
        auto_screens=["my_page"],
        is_admin=False,
        can_manage_routes=True,
        can_manage_planning=True,
        can_view_reports=True,
    ),

    "chief_engineer": Role(
        id="chief_engineer",
        label="Главный инженер проекта",
        description="ГИП — общее руководство проектами и производством",
        icon="fa fa-project-diagram",
        color="red",
        default_screens=[
            "dashboard", "inventory", "details", "routes",
            "materials", "equipment", "reports", "transactions",
            "workshop_inventory", "planning", "planning_calendar", "planning_gantt",
        ],
        auto_screens=["my_page"],
        is_admin=False,
        can_manage_routes=True,
        can_manage_equipment=True,
        can_manage_planning=True,
        can_view_reports=True,
        can_access_workshop_inventory=True,
    ),

    # ─── Администратор ───────────────────────────────────────

    "admin": Role(
        id="admin",
        label="Администратор",
        description="Администратор системы — полный доступ",
        icon="fa fa-crown",
        color="red",
        default_screens=[
            # Все экраны (будет заполнено после инициализации)
        ],
        is_admin=True,
        can_manage_users=True,
        can_manage_planning=True,
        can_view_reports=True,
        can_manage_equipment=True,
        can_manage_routes=True,
        can_manage_orders=True,
        can_access_otk=True,
        can_access_workshop_inventory=True,
        route_view_mode="all",
        workstation_required=False,
    ),
}


# ==================== ИНИЦИАЛИЗАЦИЯ ADMIN ====================
# После определения ALL_SCREENS — заполняем admin все экраны
def _init_admin_role():
    """Заполнить роль admin всеми экранами."""
    from api.users import ALL_SCREENS  # noqa: lazy import чтобы избежать цикла

    admin_role = ROLES["admin"]
    admin_role.default_screens = [s["id"] for s in ALL_SCREENS]
    # Добавляем автоматические для admin
    admin_role.auto_screens = ["my_page", "otk", "order_card"]


# ==================== УТИЛИТЫ ====================

def get_role_screens(role_id: str) -> list:
    """Получить все экраны для роли (default + auto)."""
    role = Role.get_role(role_id)
    return role.all_screens


def has_permission(role_id: str, permission: str) -> bool:
    """Проверить есть ли у роли определённое разрешение."""
    role = Role.get_role(role_id)
    return getattr(role, permission, False)


def check_screen_access(role_id: str, screen_id: str) -> bool:
    """Проверить доступ роли к экрану."""
    role = Role.get_role(role_id)
    return role.has_screen(screen_id)


def get_default_screens(role_id: str) -> list:
    """Получить дефолтные экраны для роли (без auto)."""
    role = Role.get_role(role_id)
    return list(role.default_screens)


def get_role_route_view_mode(role_id: str) -> str:
    """Получить режим просмотра маршрутов по умолчанию для роли."""
    return ROLES.get(role_id, ROLES["user"]).route_view_mode
