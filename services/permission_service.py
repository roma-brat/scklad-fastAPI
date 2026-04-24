"""
Система разрешений (Permissions) - как в AppSheet
"""

from enum import Enum
from typing import Set, Dict, List
from functools import wraps


class Permission(Enum):
    VIEW_INVENTORY = "view_inventory"
    EDIT_INVENTORY = "edit_inventory"
    DELETE_INVENTORY = "delete_inventory"
    CREATE_INVENTORY = "create_inventory"

    VIEW_TRANSACTIONS = "view_transactions"
    CREATE_TRANSACTIONS = "create_transactions"

    VIEW_ROUTES = "view_routes"
    EDIT_ROUTES = "edit_routes"
    CREATE_ROUTES = "create_routes"
    DELETE_ROUTES = "delete_routes"

    VIEW_REPORTS = "view_reports"
    EXPORT_REPORTS = "export_reports"

    VIEW_DASHBOARD = "view_dashboard"
    CUSTOMIZE_DASHBOARD = "customize_dashboard"

    VIEW_USERS = "view_users"
    EDIT_USERS = "edit_users"
    CREATE_USERS = "create_users"
    DELETE_USERS = "delete_users"

    VIEW_WORKSHOPS = "view_workshops"
    EDIT_WORKSHOPS = "edit_workshops"

    MANAGE_AUTOMATION = "manage_automation"
    VIEW_AUTOMATION = "view_automation"

    ADMIN_SETTINGS = "admin_settings"

    VIEW_OTK = "view_otk"
    APPROVE_OTK = "approve_otk"


ROLE_PERMISSIONS: Dict[str, Set[Permission]] = {
    "user": {
        Permission.VIEW_INVENTORY,
        Permission.VIEW_TRANSACTIONS,
        Permission.VIEW_ROUTES,
        Permission.VIEW_REPORTS,
        Permission.VIEW_DASHBOARD,
    },
    "storekeeper": {
        Permission.VIEW_INVENTORY,
        Permission.EDIT_INVENTORY,
        Permission.CREATE_INVENTORY,
        Permission.CREATE_TRANSACTIONS,
        Permission.VIEW_TRANSACTIONS,
        Permission.VIEW_DASHBOARD,
        Permission.VIEW_WORKSHOPS,
    },
    "technologist": {
        Permission.VIEW_INVENTORY,
        Permission.VIEW_TRANSACTIONS,
        Permission.VIEW_ROUTES,
        Permission.EDIT_ROUTES,
        Permission.CREATE_ROUTES,
        Permission.VIEW_REPORTS,
        Permission.VIEW_DASHBOARD,
        Permission.VIEW_WORKSHOPS,
    },
    "master": {
        Permission.VIEW_INVENTORY,
        Permission.CREATE_TRANSACTIONS,
        Permission.VIEW_TRANSACTIONS,
        Permission.VIEW_ROUTES,
        Permission.VIEW_REPORTS,
        Permission.VIEW_DASHBOARD,
        Permission.VIEW_WORKSHOPS,
        Permission.EDIT_WORKSHOPS,
    },
    "foreman": {
        Permission.VIEW_INVENTORY,
        Permission.EDIT_INVENTORY,
        Permission.CREATE_TRANSACTIONS,
        Permission.VIEW_TRANSACTIONS,
        Permission.VIEW_ROUTES,
        Permission.EDIT_ROUTES,
        Permission.VIEW_REPORTS,
        Permission.EXPORT_REPORTS,
        Permission.VIEW_DASHBOARD,
        Permission.VIEW_WORKSHOPS,
        Permission.EDIT_WORKSHOPS,
    },
    "technologist_designer": {
        Permission.VIEW_INVENTORY,
        Permission.VIEW_TRANSACTIONS,
        Permission.VIEW_ROUTES,
        Permission.EDIT_ROUTES,
        Permission.CREATE_ROUTES,
        Permission.DELETE_ROUTES,
        Permission.VIEW_REPORTS,
        Permission.EXPORT_REPORTS,
        Permission.VIEW_DASHBOARD,
        Permission.CUSTOMIZE_DASHBOARD,
        Permission.VIEW_WORKSHOPS,
        Permission.EDIT_WORKSHOPS,
    },
    "chief_designer": {
        Permission.VIEW_INVENTORY,
        Permission.EDIT_INVENTORY,
        Permission.VIEW_TRANSACTIONS,
        Permission.CREATE_TRANSACTIONS,
        Permission.VIEW_ROUTES,
        Permission.EDIT_ROUTES,
        Permission.CREATE_ROUTES,
        Permission.DELETE_ROUTES,
        Permission.VIEW_REPORTS,
        Permission.EXPORT_REPORTS,
        Permission.VIEW_DASHBOARD,
        Permission.CUSTOMIZE_DASHBOARD,
        Permission.VIEW_USERS,
        Permission.VIEW_WORKSHOPS,
        Permission.EDIT_WORKSHOPS,
    },
    "chief_engineer": {
        Permission.VIEW_INVENTORY,
        Permission.EDIT_INVENTORY,
        Permission.DELETE_INVENTORY,
        Permission.VIEW_TRANSACTIONS,
        Permission.CREATE_TRANSACTIONS,
        Permission.VIEW_ROUTES,
        Permission.EDIT_ROUTES,
        Permission.CREATE_ROUTES,
        Permission.DELETE_ROUTES,
        Permission.VIEW_REPORTS,
        Permission.EXPORT_REPORTS,
        Permission.VIEW_DASHBOARD,
        Permission.CUSTOMIZE_DASHBOARD,
        Permission.VIEW_USERS,
        Permission.VIEW_WORKSHOPS,
        Permission.EDIT_WORKSHOPS,
        Permission.VIEW_AUTOMATION,
    },
    "admin": set(Permission),
    "otk": {
        Permission.VIEW_DASHBOARD,
        Permission.VIEW_OTK,
        Permission.APPROVE_OTK,
    },
}


PERMISSION_LABELS: Dict[Permission, str] = {
    Permission.VIEW_INVENTORY: "Просмотр склада",
    Permission.EDIT_INVENTORY: "Редактирование склада",
    Permission.DELETE_INVENTORY: "Удаление со склада",
    Permission.CREATE_INVENTORY: "Добавление на склад",
    Permission.VIEW_TRANSACTIONS: "Просмотр транзакций",
    Permission.CREATE_TRANSACTIONS: "Создание транзакций",
    Permission.VIEW_ROUTES: "Просмотр маршрутов",
    Permission.EDIT_ROUTES: "Редактирование маршрутов",
    Permission.CREATE_ROUTES: "Создание маршрутов",
    Permission.DELETE_ROUTES: "Удаление маршрутов",
    Permission.VIEW_REPORTS: "Просмотр отчетов",
    Permission.EXPORT_REPORTS: "Экспорт отчетов",
    Permission.VIEW_DASHBOARD: "Просмотр дашборда",
    Permission.CUSTOMIZE_DASHBOARD: "Настройка дашборда",
    Permission.VIEW_USERS: "Просмотр пользователей",
    Permission.EDIT_USERS: "Редактирование пользователей",
    Permission.CREATE_USERS: "Создание пользователей",
    Permission.DELETE_USERS: "Удаление пользователей",
    Permission.VIEW_WORKSHOPS: "Просмотр цехов",
    Permission.EDIT_WORKSHOPS: "Редактирование цехов",
    Permission.MANAGE_AUTOMATION: "Управление автоматизацией",
    Permission.VIEW_AUTOMATION: "Просмотр автоматизации",
    Permission.ADMIN_SETTINGS: "Административные настройки",
    Permission.VIEW_OTK: "Просмотр ОТК",
    Permission.APPROVE_OTK: "Подтверждение ОТК",
}


class PermissionService:
    """Сервис для проверки разрешений"""

    @staticmethod
    def get_permissions_for_role(role: str) -> Set[Permission]:
        return ROLE_PERMISSIONS.get(role, set())

    @staticmethod
    def has_permission(role: str, permission: Permission) -> bool:
        return permission in ROLE_PERMISSIONS.get(role, set())

    @staticmethod
    def has_any_permission(role: str, permissions: List[Permission]) -> bool:
        role_perms = ROLE_PERMISSIONS.get(role, set())
        return any(p in role_perms for p in permissions)

    @staticmethod
    def has_all_permissions(role: str, permissions: List[Permission]) -> bool:
        role_perms = ROLE_PERMISSIONS.get(role, set())
        return all(p in role_perms for p in permissions)

    @staticmethod
    def can_access_screen(role: str, screen_name: str) -> bool:
        screen_permissions = {
            "dashboard": [Permission.VIEW_DASHBOARD],
            "inventory": [Permission.VIEW_INVENTORY],
            "transactions": [Permission.VIEW_TRANSACTIONS],
            "routes": [Permission.VIEW_ROUTES],
            "reports": [Permission.VIEW_REPORTS],
            "users": [Permission.VIEW_USERS],
            "workshops": [Permission.VIEW_WORKSHOPS],
            "automation": [Permission.VIEW_AUTOMATION, Permission.MANAGE_AUTOMATION],
            "otk": [Permission.VIEW_OTK],
            "settings": [Permission.ADMIN_SETTINGS],
        }
        required = screen_permissions.get(screen_name, [])
        return PermissionService.has_any_permission(role, required)

    @staticmethod
    def get_role_display_name(role: str) -> str:
        role_names = {
            "user": "Пользователь",
            "technologist": "Технолог",
            "master": "Мастер цеха",
            "foreman": "Начальник цеха",
            "admin": "Администратор",
            "storekeeper": "Кладовщик",
            "chief_designer": "Главный конструктор",
            "chief_engineer": "Главный инженер проекта",
            "technologist_designer": "Технолог-конструктор",
            "otk": "ОТК",
        }
        return role_names.get(role, role)


def require_permission(permission: Permission):
    """Декоратор для проверки разрешения"""

    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            user = self.app.get_current_user()
            role = user.role if user else "user"
            if not PermissionService.has_permission(role, permission):
                if hasattr(self.app, "show_error"):
                    self.app.show_error(
                        f"У вас нет разрешения: {PERMISSION_LABELS.get(permission, permission.value)}"
                    )
                return None
            return func(self, *args, **kwargs)

        return wrapper

    return decorator


def require_any_permission(*permissions: Permission):
    """Декоратор для проверки хотя бы одного разрешения"""

    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            user = self.app.get_current_user()
            role = user.role if user else "user"
            if not PermissionService.has_any_permission(role, list(permissions)):
                perms_names = ", ".join(
                    PERMISSION_LABELS.get(p, p.value) for p in permissions
                )
                if hasattr(self.app, "show_error"):
                    self.app.show_error(f"У вас нет разрешений: {perms_names}")
                return None
            return func(self, *args, **kwargs)

        return wrapper

    return decorator
