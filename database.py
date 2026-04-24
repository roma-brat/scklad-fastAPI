# database.py
"""
Менеджер базы данных PostgreSQL
"""

from sqlalchemy import create_engine, text, func
from sqlalchemy.orm import sessionmaker, scoped_session, joinedload
from contextlib import contextmanager
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging
import json
import time
import threading

from models import (
    Base,
    User,
    Item,
    Transaction,
    InventoryChange,
    AuditLog,
    Workshop,
    Material,
    OperationType,
)
from models import (
    Equipment,
)
from models import EquipmentInstance

logger = logging.getLogger(__name__)


class FastCache:
    """Быстрый in-memory кэш с TTL"""

    def __init__(self):
        self._cache: Dict[str, tuple] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key in self._cache:
                cached_time, value = self._cache[key]
                if time.time() - cached_time < 5:
                    return value
                del self._cache[key]
        return None

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._cache[key] = (time.time(), value)

    def invalidate(self, key: str = None) -> None:
        with self._lock:
            if key:
                self._cache.pop(key, None)
            else:
                self._cache.clear()


fast_cache = FastCache()


class DatabaseManager:
    """
    Менеджер подключения и операций с PostgreSQL
    """

    def __init__(self, database_url: str):
        """
        Инициализация подключения к PostgreSQL
        :param database_url: Строка подключения, например:
            postgresql://user:password@localhost:5432/sklad_db
        """
        self.engine = create_engine(
            database_url,
            pool_pre_ping=True,  # Проверка соединения перед использованием
            pool_recycle=3600,  # Пересоздание соединения через час
            echo=False,  # Логирование SQL (True для отладки)
        )

        # Создаём все таблицы
        Base.metadata.create_all(self.engine)

        # Миграция: добавляем колонку login если её нет
        self._migrate_add_login_column()

        # Миграция: увеличиваем размер колонки role
        self._migrate_role_column()

        # Миграции для планирования
        self._migrate_planning_rules_table()
        self._migrate_orders_manual_fields()

        # Сессия с автоматическим управлением
        self.SessionLocal = scoped_session(
            sessionmaker(bind=self.engine, autoflush=False, autocommit=False)
        )

        logger.info("DatabaseManager initialized")

        # Создаём admin пользователя если его нет
        self._ensure_admin_exists()

    def _ensure_admin_exists(self):
        """Создать admin пользователя если его нет"""
        try:
            with self.get_session() as session:
                from models import User

                admin = session.query(User).filter(User.username == "admin").first()
                if not admin:
                    admin = User(
                        login="admin",
                        username="admin",
                        role="admin",
                        workstation="Офис",
                    )
                    admin.set_password("admin_1234")
                    session.add(admin)
                    session.commit()
                    logger.info(
                        "Created default admin user (username: admin, password: admin_1234)"
                    )
        except Exception as e:
            logger.warning(f"Failed to create admin user: {e}")

    def _migrate_add_login_column(self):
        """Миграция: больше не нужна - используем username"""
        pass

    def _migrate_role_column(self):
        """Миграция: увеличиваем размер колонки role с VARCHAR(20) до VARCHAR(50)"""
        try:
            from sqlalchemy import text

            with self.engine.connect() as conn:
                # Проверяем текущий тип колонки
                result = conn.execute(
                    text("""
                    SELECT character_maximum_length 
                    FROM information_schema.columns 
                    WHERE table_name = 'users' AND column_name = 'role'
                """)
                )
                row = result.fetchone()

                if row and row[0] and row[0] < 50:
                    logger.info(f"🔧 Миграция: role VARCHAR({row[0]}) → VARCHAR(50)")
                    conn.execute(
                        text("ALTER TABLE users ALTER COLUMN role TYPE VARCHAR(50)")
                    )

                    # Обновляем CHECK constraint
                    conn.execute(
                        text("""
                        ALTER TABLE users DROP CONSTRAINT IF EXISTS users_role_check
                    """)
                    )
                    conn.execute(
                        text("""
                        ALTER TABLE users ADD CONSTRAINT users_role_check 
                        CHECK (role IN ('admin', 'storekeeper', 'user', 'technologist', 
                                       'foreman', 'master', 'chief_designer', 
                                       'chief_engineer', 'technologist_designer', 'otk'))
                    """)
                    )

                    conn.commit()
                    logger.info("✅ Миграция role завершена: VARCHAR(50)")
                else:
                    logger.debug(
                        "Role column already VARCHAR(50) or doesn't exist, skipping migration"
                    )
        except Exception as e:
            logger.warning(f"⚠️ Role migration skipped (non-critical): {e}")

    def _migrate_planning_rules_table(self):
        """Создать таблицу planning_rules если нет"""
        try:
            with self.engine.connect() as conn:
                conn.execute(
                    text("""
                    CREATE TABLE IF NOT EXISTS planning_rules (
                        id SERIAL PRIMARY KEY,
                        key VARCHAR(100) UNIQUE NOT NULL,
                        value TEXT,
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                """)
                )
                conn.commit()
        except Exception as e:
            logger.warning(f"⚠️ planning_rules migration skipped: {e}")

    def _migrate_orders_manual_fields(self):
        """Миграция: сделать orders.route_id nullable + добавить поля для ручных записей"""
        try:
            from sqlalchemy import inspect

            inspector = inspect(self.engine)
            columns = [c["name"] for c in inspector.get_columns("orders")]

            with self.engine.connect() as conn:
                if "route_id" in columns:
                    conn.execute(
                        text("""
                        ALTER TABLE orders ALTER COLUMN route_id DROP NOT NULL
                    """)
                    )

                if "manual_detail_name" not in columns:
                    conn.execute(
                        text("""
                        ALTER TABLE orders ADD COLUMN manual_detail_name VARCHAR(255)
                    """)
                    )

                if "manual_quantity" not in columns:
                    conn.execute(
                        text("""
                        ALTER TABLE orders ADD COLUMN manual_quantity INTEGER
                    """)
                    )

                # Снимаем NOT NULL с blanks_needed и quantity для ручных заказов
                for col_name in ("blanks_needed", "quantity"):
                    if col_name in columns:
                        conn.execute(
                            text(f"""
                            ALTER TABLE orders ALTER COLUMN {col_name} DROP NOT NULL
                        """)
                        )

                conn.commit()
                logger.info(
                    "✅ Migration: orders.route_id nullable + manual fields added"
                )

                # Миграция: добавить колонку route_card_data для ЭМК
                if "route_card_data" not in columns:
                    conn.execute(
                        text("""
                        ALTER TABLE orders ADD COLUMN route_card_data JSONB
                    """)
                    )
                    conn.commit()
                    logger.info("✅ Migration: orders.route_card_data added")
        except Exception as e:
            logger.warning(f"⚠️ Orders migration skipped: {e}")

    def get_planning_setting(self, key: str, default=None):
        """Получить настройку планирования из planning_rules"""
        try:
            with self.get_session() as session:
                result = session.execute(
                    text("SELECT value FROM planning_rules WHERE key = :key LIMIT 1"),
                    {"key": key},
                )
                row = result.fetchone()
                if row:
                    return row[0]
                return default
        except Exception:
            return default

    def set_planning_setting(self, key: str, value):
        """Установить настройку планирования"""
        try:
            with self.get_session() as session:
                existing = session.execute(
                    text("SELECT id FROM planning_rules WHERE key = :key LIMIT 1"),
                    {"key": key},
                ).fetchone()

                if existing:
                    session.execute(
                        text(
                            "UPDATE planning_rules SET value = :value WHERE key = :key"
                        ),
                        {"key": key, "value": str(value)},
                    )
                else:
                    session.execute(
                        text(
                            "INSERT INTO planning_rules (key, value) VALUES (:key, :value)"
                        ),
                        {"key": key, "value": str(value)},
                    )
                session.commit()
        except Exception as e:
            logger.error(f"Set planning setting error: {e}")

    @contextmanager
    def get_session(self):
        """Контекстный менеджер для работы с сессией"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            try:
                session.expunge_all()
            except Exception:
                pass
            try:
                session.close()
            except Exception:
                pass

    # ==================== User Operations ====================

    def authenticate_user(self, login: str, password: str) -> Optional[User]:
        """Проверка учётных данных - по логину или фамилии"""
        with self.get_session() as session:
            # Сначала пробуем найти по логину (точный поиск)
            user = (
                session.query(User)
                .filter(User.login == login, User.is_active == True)
                .first()
            )

            # Если не найден, пробуем по username (Фамилия Имя) - поиск по фамилии
            if not user:
                surname = login.strip().split()[0] if login.strip() else ""
                if surname:
                    user = (
                        session.query(User)
                        .filter(
                            User.username.ilike(f"{surname}%"), User.is_active == True
                        )
                        .first()
                    )

            if user and user.check_password(password):
                session.refresh(user)
                session.expunge(user)
                return user
            return None

    def create_user(
        self,
        login: str,
        username: str,
        password: str,
        role: str = "user",
        workstations: str = None,
    ) -> Optional[User]:
        """Создание нового пользователя"""
        with self.get_session() as session:
            # Проверка уникальности логина
            existing_login = session.query(User).filter(User.login == login).first()
            if existing_login:
                return None

            user = User(
                login=login, username=username, role=role, workstations=workstations
            )
            user.set_password(password)

            session.add(user)
            session.flush()  # Получаем ID

            self.log_audit(
                action="create_user",
                entity_type="user",
                entity_id=user.id,
                new_values={"login": login, "username": username, "role": role},
            )

            return user

    @staticmethod
    def get_display_role(db_role: str) -> str:
        """Обратный маппинг роли из БД для отображения"""
        reverse_map = {
            "technologist": "technologist",
        }
        return reverse_map.get(db_role, db_role)

    def update_user_role(self, user_id: int, new_role: str) -> bool:
        """Изменение роли пользователя - с маппингом для БД"""
        from sqlalchemy import text

        role_map = {
            "master": "master",
            "foreman": "foreman",
            "technologist": "technologist",
            "admin": "admin",
            "user": "user",
            "storekeeper": "storekeeper",
            "chief_designer": "chief_designer",
            "chief_engineer": "chief_engineer",
            "technologist_designer": "technologist_designer",
            "otk": "otk",
        }

        db_role = role_map.get(new_role, "user")

        try:
            with self.engine.connect() as conn:
                conn.execute(
                    text("""
                    UPDATE users SET role = :role, updated_at = NOW() 
                    WHERE id = :user_id
                """),
                    {"role": db_role, "user_id": user_id},
                )
                conn.commit()

            return True
        except Exception as e:
            logger.error(f"Error updating user role: {e}")
            return False

    def update_user_workstations(self, user_id: int, workstations: str) -> bool:
        """Обновление рабочих мест пользователя"""
        with self.get_session() as session:
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                return False

            old_workstations = user.workstations
            user.workstations = workstations
            user.updated_at = datetime.utcnow()

            self.log_audit(
                action="update_workstations",
                entity_type="user",
                entity_id=user_id,
                old_values={"workstations": old_workstations},
                new_values={"workstations": workstations},
            )

            return True

    def update_user_password(self, user_id: int, new_password: str) -> bool:
        """Обновление пароля пользователя"""
        with self.get_session() as session:
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                return False

            user.set_password(new_password)
            user.updated_at = datetime.utcnow()

            self.log_audit(
                action="update_password",
                entity_type="user",
                entity_id=user_id,
                new_values={"password_changed": True},
            )

            return True

    def toggle_user_active(self, user_id: int) -> Optional[dict]:
        """Переключение статуса активности пользователя"""
        with self.get_session() as session:
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                return None

            user.is_active = not user.is_active
            user.updated_at = datetime.utcnow()

            # Сохраняем данные до выхода из сессии
            result = {
                "id": user.id,
                "username": user.username,
                "is_active": user.is_active,
            }

            self.log_audit(
                action="toggle_user_active",
                entity_type="user",
                entity_id=user_id,
                old_values={"is_active": not user.is_active},
                new_values={"is_active": user.is_active},
            )

            return result

    def delete_user(self, user_id: int) -> bool:
        """Удаление пользователя"""
        with self.get_session() as session:
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                return False

            username = user.username
            session.delete(user)

            self.log_audit(
                action="delete_user",
                entity_type="user",
                entity_id=user_id,
                old_values={"username": username},
            )

            return True

    def get_user_screen_permissions(self, user_id: int) -> Optional[list]:
        """Получение списка доступных экранов пользователя.
        Возвращает None если не настроено (fallback на роль).
        """
        with self.get_session() as session:
            user = session.query(User).filter(User.id == user_id).first()
            if not user or user.screen_permissions is None:
                return None
            try:
                return json.loads(user.screen_permissions)
            except (json.JSONDecodeError, TypeError):
                return None

    def update_user_screen_permissions(
        self, user_id: int, screens: Optional[list]
    ) -> bool:
        """Обновление списка доступных экранов пользователя.
        Если screens=None — сброс на роль (NULL в БД).
        """
        with self.get_session() as session:
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                return False

            old_value = user.screen_permissions
            if screens is None:
                user.screen_permissions = None
            else:
                user.screen_permissions = json.dumps(screens)
            user.updated_at = datetime.utcnow()

            self.log_audit(
                action="update_user_screen_permissions",
                entity_type="user",
                entity_id=user_id,
                old_values={"screen_permissions": old_value},
                new_values={"screen_permissions": user.screen_permissions},
            )

            return True

    def update_user_screen_permissions_dict(
        self, user_id: int, data: dict
    ) -> bool:
        """Обновление screen_permissions как словаря {screens: [...], route_view_mode: "..."}."""
        with self.get_session() as session:
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                return False

            old_value = user.screen_permissions
            user.screen_permissions = json.dumps(data)
            user.updated_at = datetime.utcnow()

            self.log_audit(
                action="update_user_screen_permissions_dict",
                entity_type="user",
                entity_id=user_id,
                old_values={"screen_permissions": old_value},
                new_values={"screen_permissions": user.screen_permissions},
            )

            return True

    def get_user_route_view_mode(self, user_id: int) -> str:
        """Получение режима просмотра маршрутов пользователя.
        Возвращает 'approved_only' или 'all'. По умолчанию 'approved_only'.
        """
        with self.get_session() as session:
            user = session.query(User).filter(User.id == user_id).first()
            if not user or not user.screen_permissions:
                return "approved_only"
            try:
                data = json.loads(user.screen_permissions)
                if isinstance(data, dict):
                    return data.get("route_view_mode", "approved_only")
            except (json.JSONDecodeError, TypeError):
                pass
            return "approved_only"

    def update_user_route_view_mode(self, user_id: int, view_mode: str) -> bool:
        """Обновление режима просмотра маршрутов пользователя.
        view_mode: 'approved_only' или 'all'
        """
        if view_mode not in ("approved_only", "all"):
            view_mode = "approved_only"

        with self.get_session() as session:
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                return False

            old_value = user.screen_permissions
            try:
                data = json.loads(old_value) if old_value else {}
                if not isinstance(data, dict):
                    data = {"screens": data} if isinstance(data, list) else {}
            except (json.JSONDecodeError, TypeError):
                data = {}

            data["route_view_mode"] = view_mode
            user.screen_permissions = json.dumps(data)
            user.updated_at = datetime.utcnow()

            self.log_audit(
                action="update_user_route_view_mode",
                entity_type="user",
                entity_id=user_id,
                old_values={"route_view_mode": old_value},
                new_values={"route_view_mode": user.screen_permissions},
            )

            return True

    def get_all_users(self) -> List[dict]:
        """Получение всех пользователей (возвращает словари)"""
        with self.get_session() as session:
            users = session.query(User).order_by(User.username).all()
            user_ids = [u.id for u in users]

            eq_map = {}
            if user_ids:
                eq_instances = (
                    session.query(EquipmentInstance)
                    .filter(EquipmentInstance.operator_id.in_(user_ids))
                    .all()
                )
                eq_ids = [
                    int(ei.equipment_id) for ei in eq_instances if ei.equipment_id
                ]
                equipment = {}
                if eq_ids:
                    for eq in (
                        session.query(Equipment).filter(Equipment.id.in_(eq_ids)).all()
                    ):
                        equipment[eq.id] = eq.name
                for ei in eq_instances:
                    eq_name = equipment.get(int(ei.equipment_id), "")
                    display = f"{eq_name} ({ei.number})" if eq_name else ei.number
                    eq_map[ei.operator_id] = display

            result = []
            for user in users:
                workstation = user.workstation or eq_map.get(user.id)
                result.append(
                    {
                        "id": user.id,
                        "username": user.username,
                        "role": user.role,
                        "workstation": workstation,
                        "workstations": user.workstations,
                        "is_active": user.is_active,
                    }
                )
            return result

    def get_users_by_role(self, role: str) -> List[User]:
        """Получение пользователей по роли"""
        with self.get_session() as session:
            users = session.query(User).filter(User.role == role).all()
            return users

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Получение пользователя по ID"""
        with self.get_session() as session:
            return session.query(User).filter(User.id == user_id).first()

    # ==================== Item Operations ====================

    def get_item_by_id(self, item_id: str) -> Optional[dict]:
        """Поиск товара по item_id, возвращает dict (не ORM объект)"""
        with self.get_session() as session:
            item = session.query(Item).filter(Item.item_id == item_id).first()
            if item:
                return item.to_dict()
            return None

    def get_item_by_db_id(self, db_id: int) -> Optional[Item]:
        """Поиск товара по внутреннему ID"""
        with self.get_session() as session:
            return session.query(Item).filter(Item.id == db_id).first()

    def get_all_items(self, use_cache: bool = True) -> List[Item]:
        """Получение всех товаров с оптимизированным кэшем"""
        if use_cache:
            cached = fast_cache.get("all_items")
            if cached is not None:
                return cached

        with self.get_session() as session:
            items = session.query(Item).order_by(Item.name).all()
            result = [item.to_dict() for item in items]
            fast_cache.set("all_items", result)
            return result

    def get_items_light(self, limit: int = 100, offset: int = 0) -> List[dict]:
        """Быстрое получение товаров только с основными полями (для списков)"""
        with self.get_session() as session:
            items = (
                session.query(
                    Item.id,
                    Item.item_id,
                    Item.name,
                    Item.quantity,
                    Item.min_stock,
                    Item.category,
                )
                .order_by(Item.name)
                .offset(offset)
                .limit(limit)
                .all()
            )
            return [
                {
                    "id": i[0],
                    "item_id": i[1],
                    "name": i[2],
                    "quantity": i[3],
                    "min_stock": i[4],
                    "category": i[5],
                }
                for i in items
            ]

    def get_items_fast(self, limit: int = 100, offset: int = 0) -> List[Item]:
        """Быстрое получение товаров с пагинацией"""
        with self.get_session() as session:
            items = (
                session.query(Item)
                .order_by(Item.name)
                .offset(offset)
                .limit(limit)
                .all()
            )
            session.expunge_all()
            return items

    def get_items_count(self) -> int:
        """Получить общее количество товаров"""
        with self.get_session() as session:
            return session.query(func.count(Item.id)).scalar() or 0

    def get_items_dict_list(self, use_cache: bool = True) -> List[dict]:
        """Получить товары как словари (для быстрого отображения)"""
        import time

        cache_key = "_items_dict_cache"
        if use_cache and hasattr(self, cache_key) and getattr(self, cache_key, None):
            cached_time, cached_items = getattr(self, cache_key)
            if time.time() - cached_time < 5:
                return cached_items

        with self.get_session() as session:
            items = (
                session.query(
                    Item.id,
                    Item.item_id,
                    Item.name,
                    Item.quantity,
                    Item.min_stock,
                    Item.category,
                    Item.location,
                    Item.image_url,
                    Item.shop_url,
                )
                .order_by(Item.name)
                .all()
            )
            result = [
                {
                    "id": i[0],
                    "item_id": i[1],
                    "name": i[2],
                    "quantity": i[3],
                    "min_stock": i[4],
                    "category": i[5],
                    "location": i[6],
                    "image_url": i[7],
                    "shop_url": i[8],
                }
                for i in items
            ]
            setattr(self, cache_key, (time.time(), result))
            return result

    def invalidate_items_cache(self):
        """Инвалидировать кэш товаров"""
        fast_cache.invalidate("all_items")
        fast_cache.invalidate("items_dict_list")
        fast_cache.invalidate("items_count")
        fast_cache.invalidate("categories")
        fast_cache.invalidate("spec_keys")

    def get_all_categories(self) -> List[str]:
        """Получение всех уникальных категорий"""
        cached = fast_cache.get("categories")
        if cached is not None:
            return cached

        with self.get_session() as session:
            categories = (
                session.query(Item.category)
                .filter(Item.category.isnot(None), Item.category != "")
                .distinct()
                .all()
            )
            result = sorted([c[0] for c in categories if c[0]])
            fast_cache.set("categories", result)
            return result

    def get_all_spec_keys(self) -> List[str]:
        """Получение всех уникальных параметров характеристик"""
        with self.get_session() as session:
            specs = (
                session.query(Item.specifications)
                .filter(Item.specifications.isnot(None), Item.specifications != "")
                .all()
            )

            all_keys = set()
            for (spec_json,) in specs:
                try:
                    spec_dict = json.loads(spec_json)
                    all_keys.update(spec_dict.keys())
                except:
                    pass
            return sorted(all_keys)

    def get_low_stock_items(self) -> List[Item]:
        """Товары с низким остатком"""
        with self.get_session() as session:
            return session.query(Item).filter(Item.quantity <= Item.min_stock).all()

    def create_item(
        self,
        item_id: str,
        name: str,
        quantity: int = 0,
        min_stock: int = 1,
        category: str = None,
        location: str = None,
    ) -> Optional[Item]:
        """Создание нового товара"""
        with self.get_session() as session:
            existing = session.query(Item).filter(Item.item_id == item_id).first()
            if existing:
                return None

            item = Item(
                item_id=item_id,
                name=name,
                quantity=quantity,
                min_stock=min_stock,
                category=category,
                location=location,
            )
            session.add(item)
            session.flush()

            self.log_audit(
                action="create_item",
                entity_type="item",
                entity_id=item.id,
                new_values={"item_id": item_id, "name": name},
            )

            return item

    def update_item_quantity(
        self,
        item_id: str,
        new_quantity: int,
        changed_by: int,
        operation_type: str,
        detail: str = None,
        reason: str = None,
    ) -> bool:
        """
        Обновление количества товара с записью транзакции
        """
        with self.get_session() as session:
            item = session.query(Item).filter(Item.item_id == item_id).first()
            if not item:
                return False

            old_quantity = item.quantity
            quantity_delta = new_quantity - old_quantity

            # Обновляем количество
            item.quantity = new_quantity
            item.updated_at = datetime.utcnow()

            # Записываем изменение инвентаря
            inv_change = InventoryChange(
                item_id=item.id,
                old_quantity=old_quantity,
                new_quantity=new_quantity,
                changed_by=changed_by,
            )
            session.add(inv_change)

            # Записываем транзакцию
            transaction = Transaction(
                user_id=changed_by,
                item_id=item.id,
                quantity=abs(quantity_delta),
                operation_type=operation_type,
                detail=detail,
                reason=reason,
            )
            session.add(transaction)

            self.log_audit(
                action=f"{operation_type}_item",
                entity_type="item",
                entity_id=item.id,
                old_values={"quantity": old_quantity},
                new_values={"quantity": new_quantity},
            )

            return True

    def income_item(
        self, item_id: str, quantity: int, user_id: int, detail: str = None
    ) -> bool:
        """Приход товара"""
        with self.get_session() as session:
            item = session.query(Item).filter(Item.item_id == item_id).first()
            if not item:
                return False

            new_quantity = item.quantity + quantity
            return self.update_item_quantity(
                item_id=item_id,
                new_quantity=new_quantity,
                changed_by=user_id,
                operation_type="income",
                detail=detail,
            )

    def expense_item(
        self,
        item_id: str,
        quantity: int,
        user_id: int,
        reason: str = None,
        detail: str = None,
    ) -> bool:
        """Расход товара"""
        with self.get_session() as session:
            item = session.query(Item).filter(Item.item_id == item_id).first()
            if not item or item.quantity < quantity:
                return False

            new_quantity = item.quantity - quantity
            return self.update_item_quantity(
                item_id=item_id,
                new_quantity=new_quantity,
                changed_by=user_id,
                operation_type="expense",
                detail=detail,
                reason=reason,
            )

    def add_to_workshop_inventory(
        self, item_id: str, equipment_id: int, quantity: int = 1
    ) -> bool:
        """Добавить инструмент на склад станка"""
        from models import WorkshopInventory

        try:
            with self.get_session() as session:
                item = session.query(Item).filter(Item.item_id == item_id).first()
                if not item:
                    return False

                existing = (
                    session.query(WorkshopInventory)
                    .filter(
                        WorkshopInventory.item_id == item.id,
                        WorkshopInventory.equipment_id == equipment_id,
                    )
                    .first()
                )

                if existing:
                    existing.quantity += quantity
                else:
                    workshop_item = WorkshopInventory(
                        item_id=item.id, equipment_id=equipment_id, quantity=quantity
                    )
                    session.add(workshop_item)

                session.commit()
                return True
        except Exception as e:
            logger.error(f"Error adding to workshop inventory: {e}")
            return False

    def remove_from_workshop_inventory(
        self, item_id: str, equipment_id: int, quantity: int = 1
    ) -> bool:
        """Убрать инструмент со склада станка"""
        from models import WorkshopInventory

        try:
            with self.get_session() as session:
                item = session.query(Item).filter(Item.item_id == item_id).first()
                if not item:
                    return False

                existing = (
                    session.query(WorkshopInventory)
                    .filter(
                        WorkshopInventory.item_id == item.id,
                        WorkshopInventory.equipment_id == equipment_id,
                    )
                    .first()
                )

                if not existing:
                    return False

                if existing.quantity >= quantity:
                    existing.quantity -= quantity
                    if existing.quantity <= 0:
                        session.delete(existing)
                    session.commit()
                    return True
                return False
        except Exception as e:
            logger.error(f"Error removing from workshop inventory: {e}")
            return False

    def get_workshop_inventory(self, equipment_id: int = None) -> List[dict]:
        """Получить инвентарь склада станка"""
        from models import WorkshopInventory

        try:
            with self.get_session() as session:
                query = session.query(WorkshopInventory).options(
                    joinedload(WorkshopInventory.item),
                    joinedload(WorkshopInventory.equipment),
                )

                if equipment_id:
                    query = query.filter(WorkshopInventory.equipment_id == equipment_id)

                items = query.all()
                return [item.to_dict() for item in items]
        except Exception as e:
            logger.error(f"Error getting workshop inventory: {e}")
            return []

    def get_all_workshops_inventory(self) -> List[dict]:
        """Получить инвентарь всех складов станков"""
        return self.get_workshop_inventory()

    def get_equipment_with_storage(self) -> List[dict]:
        """Получить список станков со складами из БД (по флагу has_workshop_inventory)"""
        from models import Equipment

        try:
            with self.get_session() as session:
                equipment = (
                    session.query(Equipment)
                    .filter(Equipment.has_workshop_inventory == True)
                    .all()
                )
                return [{"id": eq.id, "name": eq.name} for eq in equipment]
        except Exception as e:
            logger.error(f"Error getting equipment with storage: {e}")
            return []

    def delete_workshop_inventory_item(self, inventory_id: int) -> bool:
        """Удалить запись инструмента со склада станка по ID"""
        from models import WorkshopInventory

        try:
            with self.get_session() as session:
                item = (
                    session.query(WorkshopInventory)
                    .filter(WorkshopInventory.id == inventory_id)
                    .first()
                )
                if item:
                    session.delete(item)
                    session.commit()
                    return True
                return False
        except Exception as e:
            logger.error(f"Error deleting workshop inventory item: {e}")
            return False

    def remove_from_workshop_inventory_by_id(
        self, inventory_id: int, quantity: int = 1
    ) -> bool:
        """Уменьшить количество инструмента со склада станка по ID"""
        from models import WorkshopInventory

        try:
            with self.get_session() as session:
                item = (
                    session.query(WorkshopInventory)
                    .filter(WorkshopInventory.id == inventory_id)
                    .first()
                )

                if not item:
                    return False

                if item.quantity >= quantity:
                    item.quantity -= quantity
                    if item.quantity <= 0:
                        session.delete(item)
                    session.commit()
                    return True
                return False
        except Exception as e:
            logger.error(f"Error removing from workshop inventory by id: {e}")
            return False

    def give_item_to_user(self, item_id: str, user_id: int, quantity: int = 1) -> bool:
        """Выдать инструмент пользователю (взять со склада)"""
        from models import UserItems

        try:
            with self.get_session() as session:
                item = session.query(Item).filter(Item.item_id == item_id).first()
                if not item:
                    return False

                existing = (
                    session.query(UserItems)
                    .filter(UserItems.item_id == item.id, UserItems.user_id == user_id)
                    .first()
                )

                if existing:
                    existing.quantity += quantity
                else:
                    user_item = UserItems(
                        item_id=item.id, user_id=user_id, quantity=quantity
                    )
                    session.add(user_item)

                session.commit()
                return True
        except Exception as e:
            logger.error(f"Error giving item to user: {e}")
            return False

    def return_item_from_user(
        self, item_id: str, user_id: int, quantity: int = 1
    ) -> bool:
        """Вернуть инструмент от пользователя"""
        from models import UserItems

        try:
            with self.get_session() as session:
                item = session.query(Item).filter(Item.item_id == item_id).first()
                if not item:
                    return False

                existing = (
                    session.query(UserItems)
                    .filter(UserItems.item_id == item.id, UserItems.user_id == user_id)
                    .first()
                )

                if not existing:
                    return False

                if existing.quantity >= quantity:
                    existing.quantity -= quantity
                    if existing.quantity <= 0:
                        session.delete(existing)
                    session.commit()
                    return True
                return False
        except Exception as e:
            logger.error(f"Error returning item from user: {e}")
            return False

    def writeoff_item_from_user(
        self, item_id: str, user_id: int, quantity: int = 1, reason: str = ""
    ) -> bool:
        """Списать инструмент от пользователя (без возврата на склад)

        Инструмент уже был списан со склада когда пользователь его взял.
        Здесь мы только удаляем его из user_items и записываем транзакцию списания.
        """
        from models import UserItems

        try:
            with self.get_session() as session:
                item = session.query(Item).filter(Item.item_id == item_id).first()
                if not item:
                    return False

                existing = (
                    session.query(UserItems)
                    .filter(UserItems.item_id == item.id, UserItems.user_id == user_id)
                    .first()
                )

                if not existing:
                    return False

                if existing.quantity >= quantity:
                    # Записываем транзакцию списания
                    from datetime import datetime
                    from models import Transaction

                    transaction = Transaction(
                        user_id=user_id,
                        item_id=item.id,
                        quantity=quantity,
                        operation_type="expense",  # Используем expense вместо writeoff
                        detail=f"Списание: {reason}" if reason else "Списание",
                        reason=reason if reason else "Списание инструмента",
                        timestamp=datetime.utcnow(),
                    )
                    session.add(transaction)

                    # Удаляем из user_items
                    existing.quantity -= quantity
                    if existing.quantity <= 0:
                        session.delete(existing)

                    session.commit()
                    return True
                return False
        except Exception as e:
            logger.error(f"Error writing off item from user: {e}")
            return False

    def get_user_items(self, user_id: int) -> List[dict]:
        """Получить список инструментов на руках у пользователя"""
        from models import UserItems

        try:
            with self.get_session() as session:
                items = (
                    session.query(UserItems)
                    .options(joinedload(UserItems.item))
                    .filter(UserItems.user_id == user_id)
                    .all()
                )
                return [item.to_dict() for item in items]
        except Exception as e:
            logger.error(f"Error getting user items: {e}")
            return []

    def get_all_user_items(self) -> List[dict]:
        """Получить все инструменты на руках у всех пользователей"""
        from models import UserItems

        try:
            with self.get_session() as session:
                items = (
                    session.query(UserItems)
                    .options(joinedload(UserItems.item), joinedload(UserItems.user))
                    .all()
                )
                return [item.to_dict() for item in items]
        except Exception as e:
            logger.error(f"Error getting all user items: {e}")
            return []

    def search_items(self, query: str) -> List[Item]:
        """Поиск товаров по названию, item_id или числовому ID"""
        with self.get_session() as session:
            search_pattern = f"%{query}%"

            # Базовый фильтр: поиск по name и item_id
            conditions = (Item.name.ilike(search_pattern)) | (
                Item.item_id.ilike(search_pattern)
            )

            # Если query является числом, добавляем поиск по Item.id
            if query.isdigit():
                conditions = conditions | (Item.id == int(query))

            items = session.query(Item).filter(conditions).limit(50).all()
            # Преобразуем в dict ДО закрытия сессии
            result = []
            for item in items:
                result.append(
                    {
                        "id": item.id,
                        "item_id": item.item_id,
                        "name": item.name,
                        "quantity": item.quantity,
                        "min_stock": item.min_stock,
                        "category": item.category,
                        "location": item.location,
                        "image_url": item.image_url,
                        "shop_url": item.shop_url,
                        "specifications": item.specifications,
                    }
                )
            return result

    def update_item(self, item: Item) -> bool:
        """Обновление товара"""
        try:
            with self.get_session() as session:
                session.merge(item)
            return True
        except Exception as e:
            logger.error(f"Update item error: {e}")
            return False

    def update_item_by_id(
        self,
        item_id: str,
        name: str = None,
        category: str = None,
        location: str = None,
        quantity: int = None,
        min_stock: int = None,
        image_url: str = None,
        shop_url: str = None,
        specifications: str = None,
    ) -> bool:
        """Обновление товара по ID"""
        try:
            with self.get_session() as session:
                item = session.query(Item).filter(Item.item_id == item_id).first()
                if not item:
                    return False

                if name is not None:
                    item.name = name
                if category is not None:
                    item.category = category
                if location is not None:
                    item.location = location
                if quantity is not None:
                    item.quantity = quantity
                if min_stock is not None:
                    item.min_stock = min_stock
                if image_url is not None:
                    item.image_url = image_url
                if shop_url is not None:
                    item.shop_url = shop_url
                if specifications is not None:
                    item.specifications = specifications

                session.commit()
            return True
        except Exception as e:
            logger.error(f"Update item error: {e}")
            return False

    def update_item_field(
        self, item_id: str, field_name: str, field_value: Any
    ) -> bool:
        """Обновление отдельного поля товара по item_id"""
        try:
            with self.get_session() as session:
                item = session.query(Item).filter(Item.item_id == item_id).first()
                if not item:
                    return False

                if hasattr(item, field_name):
                    setattr(item, field_name, field_value)
                    session.commit()
                    return True
                return False
        except Exception as e:
            logger.error(f"Update item field error: {e}")
            return False

    def add_item(self, item: Item) -> bool:
        """Добавление товара"""
        try:
            with self.get_session() as session:
                existing = (
                    session.query(Item).filter(Item.item_id == item.item_id).first()
                )
                if existing:
                    return False
                session.add(item)
                session.commit()
            return True
        except Exception as e:
            logger.error(f"Add item error: {e}")
            return False

    def delete_item(self, item_id: int) -> bool:
        """Удаление товара"""
        try:
            with self.get_session() as session:
                item = session.query(Item).filter(Item.id == item_id).first()
                if item:
                    session.delete(item)
                    session.commit()
                    return True
                return False
        except Exception as e:
            logger.error(f"Delete item error: {e}")
            return False

    def delete_transaction(self, transaction_id: int) -> bool:
        """Удаление транзакции"""
        try:
            with self.get_session() as session:
                transaction = (
                    session.query(Transaction)
                    .filter(Transaction.id == transaction_id)
                    .first()
                )
                if transaction:
                    session.delete(transaction)
                    session.commit()
                    return True
                return False
        except Exception as e:
            logger.error(f"Delete transaction error: {e}")
            return False

    # ==================== Transaction Operations ====================

    def get_transactions(
        self,
        limit: int = 100,
        offset: int = 0,
        operation_type: str = None,
        user_id: int = None,
        item_id: int = None,
        date_from: datetime = None,
        date_to: datetime = None,
    ) -> List[Transaction]:
        """Получение транзакций с фильтрацией"""
        with self.get_session() as session:
            query = session.query(Transaction).options(
                joinedload(Transaction.user), joinedload(Transaction.item)
            )

            if operation_type:
                query = query.filter(Transaction.operation_type == operation_type)
            if user_id:
                query = query.filter(Transaction.user_id == user_id)
            if item_id:
                query = query.filter(Transaction.item_id == item_id)
            if date_from:
                query = query.filter(Transaction.timestamp >= date_from)
            if date_to:
                query = query.filter(Transaction.timestamp <= date_to)

            transactions = (
                query.order_by(Transaction.timestamp.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )

            # Отсоединяем объекты от сессии, но сохраняем загруженные данные
            session.expunge_all()

            return transactions

    def get_transactions_dict(
        self,
        limit: int = 100,
        offset: int = 0,
        operation_type: str = None,
        user_id: int = None,
        item_id: int = None,
        date_from: datetime = None,
        date_to: datetime = None,
    ) -> List[dict]:
        """Получение транзакций с фильтрацией в виде словарей"""
        with self.get_session() as session:
            query = session.query(Transaction).options(
                joinedload(Transaction.user), joinedload(Transaction.item)
            )

            if operation_type:
                query = query.filter(Transaction.operation_type == operation_type)
            if user_id:
                query = query.filter(Transaction.user_id == user_id)
            if item_id:
                query = query.filter(Transaction.item_id == item_id)
            if date_from:
                query = query.filter(Transaction.timestamp >= date_from)
            if date_to:
                query = query.filter(Transaction.timestamp <= date_to)

            transactions = (
                query.order_by(Transaction.timestamp.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )

            result = []
            for t in transactions:
                result.append(
                    {
                        "id": t.id,
                        "timestamp": t.timestamp,
                        "operation_type": t.operation_type,
                        "quantity": t.quantity,
                        "detail": t.detail,
                        "reason": t.reason,
                        "user_name": t.user.username if t.user else None,
                        "item_name": t.item.name if t.item else None,
                        "item_code": t.item.item_id if t.item else None,
                    }
                )
            return result

    def get_transaction_history(
        self, item_id: str, limit: int = 50
    ) -> List[Transaction]:
        """История операций по товару"""
        with self.get_session() as session:
            item = session.query(Item).filter(Item.item_id == item_id).first()
            if not item:
                return []

            return (
                session.query(Transaction)
                .filter(Transaction.item_id == item.id)
                .order_by(Transaction.timestamp.desc())
                .limit(limit)
                .all()
            )

    # ==================== Audit Log Operations ====================

    def log_audit(
        self,
        action: str,
        entity_type: str = None,
        entity_id: int = None,
        old_values: Dict = None,
        new_values: Dict = None,
        user_id: int = None,
        ip_address: str = None,
    ):
        """Запись в audit log"""
        with self.get_session() as session:
            audit = AuditLog(
                user_id=user_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                old_values=json.dumps(old_values) if old_values else None,
                new_values=json.dumps(new_values) if new_values else None,
                ip_address=ip_address,
            )
            session.add(audit)

    def get_audit_logs(
        self,
        limit: int = 100,
        user_id: int = None,
        action: str = None,
        date_from: datetime = None,
    ) -> List[AuditLog]:
        """Получение audit логов"""
        with self.get_session() as session:
            query = session.query(AuditLog)

            if user_id:
                query = query.filter(AuditLog.user_id == user_id)
            if action:
                query = query.filter(AuditLog.action == action)
            if date_from:
                query = query.filter(AuditLog.timestamp >= date_from)

            return query.order_by(AuditLog.timestamp.desc()).limit(limit).all()

    # ==================== Statistics ====================

    def get_statistics(self, days: int = 7) -> Dict[str, Any]:
        """Получение статистики за период"""
        date_from = datetime.utcnow() - timedelta(days=days)

        with self.get_session() as session:
            # Всего операций
            total_ops = (
                session.query(func.count(Transaction.id))
                .filter(Transaction.timestamp >= date_from)
                .scalar()
                or 0
            )

            # Приход
            income_ops = (
                session.query(func.count(Transaction.id))
                .filter(
                    Transaction.timestamp >= date_from,
                    Transaction.operation_type == "income",
                )
                .scalar()
                or 0
            )

            # Расход
            expense_ops = (
                session.query(func.count(Transaction.id))
                .filter(
                    Transaction.timestamp >= date_from,
                    Transaction.operation_type == "expense",
                )
                .scalar()
                or 0
            )

            # Товары с низким остатком
            low_stock = (
                session.query(func.count(Item.id))
                .filter(Item.quantity <= Item.min_stock)
                .scalar()
                or 0
            )

            # Активные пользователи
            active_users = (
                session.query(func.count(User.id))
                .filter(User.is_active == True)
                .scalar()
                or 0
            )

            return {
                "total_operations": total_ops,
                "income_operations": income_ops,
                "expense_operations": expense_ops,
                "low_stock_items": low_stock,
                "active_users": active_users,
                "period_days": days,
            }

    # ==================== Inventory Changes ====================

    def get_inventory_changes(
        self, item_id: str = None, limit: int = 50
    ) -> List[InventoryChange]:
        """Получение истории изменений инвентаря"""
        with self.get_session() as session:
            query = session.query(InventoryChange)

            if item_id:
                item = session.query(Item).filter(Item.item_id == item_id).first()
                if item:
                    query = query.filter(InventoryChange.item_id == item.id)

            return query.order_by(InventoryChange.timestamp.desc()).limit(limit).all()

    # ==================== Workshops ====================

    def get_all_workshops(self) -> List[dict]:
        """Получение всех цехов"""
        with self.get_session() as session:
            workshops = (
                session.query(Workshop)
                .filter(Workshop.is_active == True)
                .order_by(Workshop.name)
                .all()
            )
            return [
                {"id": w.id, "name": w.name, "description": w.description}
                for w in workshops
            ]

    def add_workshop(self, name: str, description: str = None) -> dict:
        """Добавление цеха"""
        try:
            with self.get_session() as session:
                existing = session.query(Workshop).filter(Workshop.name == name).first()
                if existing:
                    return {
                        "id": existing.id,
                        "name": existing.name,
                        "description": existing.description,
                    }
                workshop = Workshop(name=name, description=description)
                session.add(workshop)
                session.commit()
                session.refresh(workshop)
                return {
                    "id": workshop.id,
                    "name": workshop.name,
                    "description": workshop.description,
                }
        except Exception as e:
            logger.error(f"Add workshop error: {e}")
            return None

    def update_workshop(
        self,
        workshop_id: int,
        name: str = None,
        description: str = None,
        is_active: bool = None,
    ) -> bool:
        """Обновление цеха"""
        try:
            with self.get_session() as session:
                workshop = (
                    session.query(Workshop).filter(Workshop.id == workshop_id).first()
                )
                if not workshop:
                    return False
                if name is not None:
                    workshop.name = name
                if description is not None:
                    workshop.description = description
                if is_active is not None:
                    workshop.is_active = is_active
                session.commit()
                return True
        except Exception as e:
            logger.error(f"Update workshop error: {e}")
            return False

    def delete_workshop(self, workshop_id: int) -> bool:
        """Удаление (деактивация) цеха"""
        return self.update_workshop(workshop_id, is_active=False)

    # ==================== Materials ====================

    def get_all_materials(self) -> List[dict]:
        """Получение всех материалов"""
        with self.get_session() as session:
            materials = (
                session.query(Material)
                .filter(Material.is_active == True)
                .order_by(Material.name)
                .all()
            )
            return [
                {
                    "id": m.id,
                    "name": m.name,
                    "description": m.description,
                    "unit": m.unit,
                }
                for m in materials
            ]

    def add_material(
        self, name: str, description: str = None, unit: str = "шт"
    ) -> dict:
        """Добавление материала"""
        try:
            with self.get_session() as session:
                existing = session.query(Material).filter(Material.name == name).first()
                if existing:
                    return {
                        "id": existing.id,
                        "name": existing.name,
                        "description": existing.description,
                        "unit": existing.unit,
                    }
                material = Material(name=name, description=description, unit=unit)
                session.add(material)
                session.commit()
                session.refresh(material)
                return {
                    "id": material.id,
                    "name": material.name,
                    "description": material.description,
                    "unit": material.unit,
                }
        except Exception as e:
            logger.error(f"Add material error: {e}")
            return None

    def update_material(
        self,
        material_id: int,
        name: str = None,
        description: str = None,
        unit: str = None,
        is_active: bool = None,
    ) -> bool:
        """Обновление материала"""
        try:
            with self.get_session() as session:
                material = (
                    session.query(Material).filter(Material.id == material_id).first()
                )
                if not material:
                    return False
                if name is not None:
                    material.name = name
                if description is not None:
                    material.description = description
                if unit is not None:
                    material.unit = unit
                if is_active is not None:
                    material.is_active = is_active
                session.commit()
                return True
        except Exception as e:
            logger.error(f"Update material error: {e}")
            return False

    def delete_material(self, material_id: int) -> bool:
        """Удаление (деактивация) материала"""
        return self.update_material(material_id, is_active=False)

    # ==================== Operation Types ====================

    def get_all_operation_types(self) -> List[dict]:
        """Получение всех типов операций"""
        with self.get_session() as session:
            ops = (
                session.query(OperationType)
                .filter(OperationType.is_active == True)
                .order_by(OperationType.name)
                .all()
            )
            return [
                {
                    "id": o.id,
                    "name": o.name,
                    "description": o.description,
                    "default_duration": o.default_duration,
                }
                for o in ops
            ]

    def add_operation_type(
        self, name: str, description: str = None, default_duration: int = 60
    ) -> dict:
        """Добавление типа операции"""
        try:
            with self.get_session() as session:
                existing = (
                    session.query(OperationType)
                    .filter(OperationType.name == name)
                    .first()
                )
                if existing:
                    return {
                        "id": existing.id,
                        "name": existing.name,
                        "description": existing.description,
                        "default_duration": existing.default_duration,
                    }
                op_type = OperationType(
                    name=name,
                    description=description,
                    default_duration=default_duration,
                )
                session.add(op_type)
                session.commit()
                session.refresh(op_type)
                return {
                    "id": op_type.id,
                    "name": op_type.name,
                    "description": op_type.description,
                    "default_duration": op_type.default_duration,
                }
        except Exception as e:
            logger.error(f"Add operation type error: {e}")
            return None

    def update_operation_type(
        self,
        op_type_id: int,
        name: str = None,
        description: str = None,
        default_duration: int = None,
        is_active: bool = None,
    ) -> bool:
        """Обновление типа операции"""
        try:
            with self.get_session() as session:
                op_type = (
                    session.query(OperationType)
                    .filter(OperationType.id == op_type_id)
                    .first()
                )
                if not op_type:
                    return False
                if name is not None:
                    op_type.name = name
                if description is not None:
                    op_type.description = description
                if default_duration is not None:
                    op_type.default_duration = default_duration
                if is_active is not None:
                    op_type.is_active = is_active
                session.commit()
                return True
        except Exception as e:
            logger.error(f"Update operation type error: {e}")
            return False

    def delete_operation_type(self, op_type_id: int) -> bool:
        """Удаление (деактивация) типа операции"""
        return self.update_operation_type(op_type_id, is_active=False)

    # ==================== Workshops & Operations ====================

    def get_operations_by_workshop(self, workshop_id: int) -> List[dict]:
        with self.get_session() as session:
            result = session.execute(
                text(
                    "SELECT ot.id, ot.name, ot.default_duration FROM operation_types ot "
                    "JOIN operation_workshop ow ON ow.operation_type_id = ot.id "
                    "WHERE ow.workshop_id = :workshop_id AND ot.is_active = true ORDER BY ot.name"
                ),
                {"workshop_id": workshop_id},
            )
            return [dict(row._mapping) for row in result]

    def get_equipment_by_operation(self, operation_id: int) -> List[dict]:
        """Получить оборудование для типа операции (без дублей)"""
        with self.get_session() as session:
            result = session.execute(
                text(
                    "SELECT DISTINCT e.id, e.name, e.inventory_number FROM equipment e "
                    "JOIN operation_equipment oe ON oe.equipment_id = e.id "
                    "WHERE oe.operation_type_id = :operation_id "
                    "ORDER BY e.name"
                ),
                {"operation_id": operation_id},
            )
            return [dict(row._mapping) for row in result]

    def get_all_cooperatives(self) -> List[dict]:
        with self.get_session() as session:
            result = session.execute(
                text(
                    "SELECT id, name, description FROM cooperatives WHERE is_active = 1 ORDER BY name"
                )
            )
            return [dict(row._mapping) for row in result]

    def get_cooperative_companies(self) -> List[dict]:
        """Alias for get_all_cooperatives"""
        return self.get_all_cooperatives()

    def get_operations_by_cooperative(self, cooperative_id: int) -> List[dict]:
        with self.get_session() as session:
            result = session.execute(
                text(
                    "SELECT ot.id as operation_type_id, ot.name, ot.default_duration FROM operation_types ot "
                    "JOIN operation_cooperative oc ON oc.operation_type_id = ot.id "
                    "WHERE oc.cooperative_id = :cooperative_id AND ot.is_active = true ORDER BY ot.name"
                ),
                {"cooperative_id": cooperative_id},
            )
            return [dict(row._mapping) for row in result]

    # ==================== Material Instances ====================

    def get_all_material_instances(self) -> List[dict]:
        """Получение всех экземпляров сортамента"""
        with self.get_session() as session:
            result = session.execute(
                text("""
                SELECT id, app_id, mark_name, sortament_name, dimension1, dimension2, dimension3, price_per_piece
                FROM material_instances
                ORDER BY mark_name, sortament_name
            """)
            )
            return [dict(row._mapping) for row in result]

    def delete_material_instance(self, instance_id: int) -> bool:
        """Удаление экземпляра сортамента"""
        try:
            with self.get_session() as session:
                session.execute(
                    text("DELETE FROM material_instances WHERE id = :id"),
                    {"id": instance_id},
                )
                session.commit()
            return True
        except Exception as e:
            logger.error(f"Delete material instance error: {e}")
            return False

    def update_material_prices(
        self,
        instance_id: int,
        price_per_ton: float = None,
        price_per_piece: float = None,
    ) -> bool:
        """Обновление цен материала"""
        try:
            with self.get_session() as session:
                updates = []
                params = {"id": instance_id}
                if price_per_ton is not None:
                    updates.append("price_per_ton = :price_per_ton")
                    params["price_per_ton"] = price_per_ton
                if price_per_piece is not None:
                    updates.append("price_per_piece = :price_per_piece")
                    params["price_per_piece"] = price_per_piece
                if updates:
                    query = f"UPDATE material_instances SET {', '.join(updates)} WHERE id = :id"
                    session.execute(text(query), params)
                    session.commit()
                return True
        except Exception as e:
            logger.error(f"Update material prices error: {e}")
            return False

    def update_material_full(
        self,
        instance_id: int,
        mark_name: str = None,
        sortament_name: str = None,
        mark_gost: str = None,
        sortament_gost: str = None,
        dimension1: float = None,
        dimension2: float = None,
        dimension3: float = None,
        price_per_ton: float = None,
        price_per_piece: float = None,
    ) -> bool:
        """Полное обновление материала"""
        try:
            with self.get_session() as session:
                updates = []
                params = {"id": instance_id}
                fields = {
                    "mark_name": mark_name,
                    "sortament_name": sortament_name,
                    "mark_gost": mark_gost,
                    "sortament_gost": sortament_gost,
                    "dimension1": dimension1,
                    "dimension2": dimension2,
                    "dimension3": dimension3,
                    "price_per_ton": price_per_ton,
                    "price_per_piece": price_per_piece,
                }
                for field, value in fields.items():
                    if value is not None:
                        updates.append(f"{field} = :{field}")
                        params[field] = value
                if updates:
                    query = f"UPDATE material_instances SET {', '.join(updates)} WHERE id = :id"
                    session.execute(text(query), params)
                    session.commit()
                return True
        except Exception as e:
            logger.error(f"Update material full error: {e}")
            return False

    # ==================== Equipment ====================

    def get_all_equipment(self, active_only: bool = False) -> List[dict]:
        """Получение всего оборудования (с устранением дубликатов по имени)"""
        with self.get_session() as session:
            query = """
                SELECT id, app_id, name, inventory_number, power, is_universal, is_active, default_working_hours
                FROM equipment
            """
            if active_only:
                query += " WHERE is_active = true"
            query += " ORDER BY COALESCE(position, 999999), name, id"
            result = session.execute(text(query))
            all_equipment = [dict(row._mapping) for row in result]

            # Устраняем дубликаты по имени и фильтруем записи без ID
            seen_names = set()
            unique_equipment = []
            for eq in all_equipment:
                # Пропускаем записи без ID
                if not eq.get("id"):
                    continue
                name_key = (eq.get("name") or "").strip().lower()
                if name_key and name_key not in seen_names:
                    seen_names.add(name_key)
                    unique_equipment.append(eq)

            return unique_equipment

    def update_equipment_settings(
        self,
        equipment_id: int,
        is_active: bool = None,
        default_working_hours: int = None,
    ) -> bool:
        """Обновление настроек оборудования"""
        try:
            with self.get_session() as session:
                updates = []
                params = {"id": equipment_id}
                if is_active is not None:
                    updates.append("is_active = :is_active")
                    params["is_active"] = is_active
                if default_working_hours is not None:
                    updates.append("default_working_hours = :working_hours")
                    params["working_hours"] = default_working_hours

                if updates:
                    query = f"UPDATE equipment SET {', '.join(updates)} WHERE id = :id"
                    session.execute(text(query), params)
                    session.commit()
                return True
        except Exception as e:
            logger.error(f"Update equipment settings error: {e}")
            return False

    # ==================== Equipment Calendar ====================

    def get_equipment_calendar(
        self, equipment_id: int, date_from: datetime, date_to: datetime
    ) -> List[dict]:
        """Получить календарь станка за период"""
        with self.get_session() as session:
            result = session.execute(
                text("""
                SELECT ec.id, ec.equipment_id, ec.date, ec.working_hours, ec.is_working, ec.notes,
                       e.name as equipment_name
                FROM equipment_calendar ec
                JOIN equipment e ON ec.equipment_id = e.id
                WHERE ec.equipment_id = :equipment_id
                  AND ec.date >= :date_from
                  AND ec.date <= :date_to
                ORDER BY ec.date
            """),
                {
                    "equipment_id": equipment_id,
                    "date_from": date_from.date()
                    if isinstance(date_from, datetime)
                    else date_from,
                    "date_to": date_to.date()
                    if isinstance(date_to, datetime)
                    else date_to,
                },
            )
            return [dict(row._mapping) for row in result]

    def get_all_equipment_calendar(
        self, date_from: datetime, date_to: datetime
    ) -> List[dict]:
        """Получить календарь всех станков за период"""
        with self.get_session() as session:
            result = session.execute(
                text("""
                SELECT ec.id, ec.equipment_id, ec.date, ec.working_hours, ec.is_working, ec.notes,
                       e.name as equipment_name
                FROM equipment_calendar ec
                JOIN equipment e ON ec.equipment_id = e.id
                WHERE ec.date >= :date_from
                  AND ec.date <= :date_to
                ORDER BY ec.equipment_id, ec.date
            """),
                {
                    "date_from": date_from.date()
                    if isinstance(date_from, datetime)
                    else date_from,
                    "date_to": date_to.date()
                    if isinstance(date_to, datetime)
                    else date_to,
                },
            )
            return [dict(row._mapping) for row in result]

    def clear_equipment_calendar_day(self, equipment_id: int, date: datetime) -> bool:
        """Удалить настройку дня станка (сбросить к默认值)"""
        try:
            with self.get_session() as session:
                session.execute(
                    text("""
                    DELETE FROM equipment_calendar 
                    WHERE equipment_id = :equipment_id AND date = :date
                """),
                    {
                        "equipment_id": equipment_id,
                        "date": date.date() if isinstance(date, datetime) else date,
                    },
                )
                session.commit()
                return True
        except Exception as e:
            logger.error(f"Clear equipment calendar day error: {e}")
            return False

    # ==================== Production Schedule ====================

    def add_to_production_schedule(
        self,
        order_id: int,
        route_operation_id: int,
        equipment_id: int,
        planned_date: datetime,
        quantity: int = 1,
        priority: int = 5,
        duration_minutes: int = None,
        notes: str = None,
        status: str = "planned",
        is_cooperation: bool = False,
        coop_company_name: str = None,
        coop_duration_days: int = None,
    ) -> dict:
        """Добавить операцию в производственный план"""
        try:
            with self.get_session() as session:
                result = session.execute(
                    text("""
                    INSERT INTO production_schedule 
                    (order_id, route_operation_id, equipment_id, planned_date, quantity, priority, duration_minutes, notes, status, is_cooperation, coop_company_name, coop_duration_days)
                    VALUES (:order_id, :route_operation_id, :equipment_id, :planned_date, :quantity, :priority, :duration_minutes, :notes, :status, :is_cooperation, :coop_company_name, :coop_duration_days)
                    RETURNING id
                """),
                    {
                        "order_id": order_id,
                        "route_operation_id": route_operation_id,
                        "equipment_id": equipment_id,
                        "planned_date": planned_date.date()
                        if isinstance(planned_date, datetime)
                        else planned_date,
                        "quantity": quantity,
                        "priority": priority,
                        "duration_minutes": duration_minutes,
                        "notes": notes,
                        "status": status,
                        "is_cooperation": is_cooperation,
                        "coop_company_name": coop_company_name,
                        "coop_duration_days": coop_duration_days,
                    },
                )
                schedule_id = result.scalar()
                session.commit()
                return {"id": schedule_id, "success": True}
        except Exception as e:
            logger.error(f"Add to production schedule error: {e}")
            return None

    def create_manual_order_with_schedule(
        self,
        detail_name: str,
        quantity: int,
        equipment_id: int,
        planned_date,
        duration_minutes: int = 60,
        priority: int = 5,
        status: str = "planned",
        notes: str = None,
        workday_limit: int = 420,  # 7 часов = 420 минут
    ) -> dict:
        """Создать ручной заказ (без маршрута) и добавить в расписание.

        Если total_time (duration_minutes × quantity) > workday_limit,
        автоматически распределяет на несколько рабочих дней.
        """
        try:
            with self.get_session() as session:
                # Создаём заказ
                order_result = session.execute(
                    text("""
                    INSERT INTO orders (manual_detail_name, manual_quantity, quantity, production_type)
                    VALUES (:detail_name, :quantity, :quantity, 'piece')
                    RETURNING id
                    """),
                    {
                        "detail_name": detail_name,
                        "quantity": quantity,
                    },
                )
                order_id = order_result.scalar()

                # Рассчитываем общее время и распределяем по дням
                total_time = duration_minutes * quantity
                schedule_ids = []

                # Если общее время <= лимита — создаём одну запись
                if total_time <= workday_limit:
                    schedule_result = session.execute(
                        text("""
                        INSERT INTO production_schedule
                        (order_id, equipment_id, planned_date, quantity, priority, duration_minutes, status, notes, route_operation_id)
                        VALUES (:order_id, :equipment_id, :planned_date, :quantity, :priority, :duration_minutes, :status, :notes, NULL)
                        RETURNING id
                        """),
                        {
                            "order_id": order_id,
                            "equipment_id": equipment_id,
                            "planned_date": planned_date.date()
                            if isinstance(planned_date, datetime)
                            else planned_date,
                            "quantity": quantity,
                            "priority": priority,
                            "duration_minutes": duration_minutes,
                            "status": status,
                            "notes": notes,
                        },
                    )
                    schedule_ids.append(schedule_result.scalar())
                else:
                    # Распределяем на несколько дней
                    remaining_qty = quantity
                    remaining_time = total_time
                    current_date = (
                        planned_date
                        if isinstance(planned_date, datetime)
                        else datetime(
                            planned_date.year, planned_date.month, planned_date.day
                        )
                    )

                    while remaining_qty > 0 and remaining_time > 0:
                        # Пропускаем выходные (Сб=5, Вс=6)
                        while current_date.weekday() >= 5:
                            current_date += timedelta(days=1)

                        # Сколько можно сделать за этот день
                        qty_per_day = (
                            workday_limit // duration_minutes
                        )  # макс штук за день
                        if qty_per_day == 0:
                            qty_per_day = 1  # минимум 1 шт если время > лимита дня

                        qty_today = min(remaining_qty, qty_per_day)
                        time_today = qty_today * duration_minutes

                        # Убедимся что не превышаем лимит дня
                        if time_today > workday_limit:
                            time_today = workday_limit
                            qty_today = time_today // duration_minutes
                            if qty_today == 0:
                                qty_today = 1
                                time_today = duration_minutes

                        schedule_result = session.execute(
                            text("""
                            INSERT INTO production_schedule
                            (order_id, equipment_id, planned_date, quantity, priority, duration_minutes, status, notes, route_operation_id)
                            VALUES (:order_id, :equipment_id, :planned_date, :qty, :priority, :duration_minutes, :status, :notes, NULL)
                            RETURNING id
                            """),
                            {
                                "order_id": order_id,
                                "equipment_id": equipment_id,
                                "planned_date": current_date.date(),
                                "qty": qty_today,
                                "priority": priority,
                                "duration_minutes": time_today,
                                "status": status,
                                "notes": notes,
                            },
                        )
                        schedule_ids.append(schedule_result.scalar())

                        remaining_qty -= qty_today
                        remaining_time -= time_today

                        # Переходим к следующему дню
                        current_date += timedelta(days=1)

                session.commit()
                return {
                    "success": True,
                    "order_id": order_id,
                    "schedule_id": schedule_ids[0]
                    if len(schedule_ids) == 1
                    else schedule_ids,
                    "schedule_count": len(schedule_ids),
                }
        except Exception as e:
            logger.error(f"Create manual order with schedule error: {e}", exc_info=True)
            return {"success": False, "message": str(e)}

    def get_production_schedule(
        self,
        date_from: datetime = None,
        date_to: datetime = None,
        equipment_id: int = None,
        order_id: int = None,
    ) -> List[dict]:
        """Получить производственный план с фильтрами"""
        with self.get_session() as session:
            conditions = []
            params = {}

            def to_date(val):
                if val is None:
                    return None
                if hasattr(val, "value"):
                    val = val.value
                if hasattr(val, "date"):
                    return val.date()
                if isinstance(val, datetime):
                    return val.date()
                return val

            if date_from:
                conditions.append("ps.planned_date >= :date_from")
                params["date_from"] = to_date(date_from)
            if date_to:
                conditions.append("ps.planned_date <= :date_to")
                params["date_to"] = to_date(date_to)
            if equipment_id:
                conditions.append("ps.equipment_id = :equipment_id")
                params["equipment_id"] = equipment_id
            if order_id:
                conditions.append("ps.order_id = :order_id")
                params["order_id"] = order_id

            where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            result = session.execute(
                text(f"""
                SELECT ps.id, ps.order_id, ps.route_operation_id, ps.equipment_id,
                       ps.planned_date, ps.actual_date, ps.status, ps.priority,
                       ps.quantity, ps.duration_minutes, ps.notes, ps.is_manual_override,
                       ps.taken_at, ps.completed_at, ps.taken_by, ps.completed_by,
                       ps.is_cooperation, ps.coop_company_name, ps.coop_duration_days,
                       e.name as equipment_name,
                       dr.designation, dr.detail_name, o.quantity as order_quantity,
                       o.production_type, o.batch_number, o.order_number,
                       ot.name as operation_name,
                       ro.sequence_number, ro.operation_type_id, ro.total_time,
                       mi.mark_name, mi.sortament_name
                FROM production_schedule ps
                JOIN orders o ON ps.order_id = o.id
                LEFT JOIN detail_routes dr ON o.route_id = dr.id
                LEFT JOIN material_instances mi ON dr.material_instance_id = mi.id
                LEFT JOIN equipment e ON ps.equipment_id = e.id
                LEFT JOIN route_operations ro ON ps.route_operation_id = ro.id
                LEFT JOIN operation_types ot ON ro.operation_type_id = ot.id
                {where}
                ORDER BY ps.planned_date, ps.priority DESC, ro.sequence_number
            """),
                params,
            )
            return [dict(row._mapping) for row in result]

    def update_schedule_item(
        self,
        schedule_id: int,
        planned_date: datetime = None,
        equipment_id: int = None,
        status: str = None,
        priority: int = None,
        notes: str = None,
        is_manual_override: bool = False,
    ) -> bool:
        """Обновить элемент плана"""
        try:
            with self.get_session() as session:
                updates = []
                params = {"id": schedule_id}

                if planned_date is not None:
                    updates.append("planned_date = :planned_date")
                    params["planned_date"] = (
                        planned_date.date()
                        if isinstance(planned_date, datetime)
                        else planned_date
                    )
                if equipment_id is not None:
                    updates.append("equipment_id = :equipment_id")
                    params["equipment_id"] = equipment_id
                if status is not None:
                    updates.append("status = :status")
                    params["status"] = status
                if priority is not None:
                    updates.append("priority = :priority")
                    params["priority"] = priority
                if notes is not None:
                    updates.append("notes = :notes")
                    params["notes"] = notes
                if is_manual_override:
                    updates.append("is_manual_override = true")

                if updates:
                    query = f"UPDATE production_schedule SET {', '.join(updates)} WHERE id = :id"
                    session.execute(text(query), params)
                    session.commit()
                return True
        except Exception as e:
            logger.error(f"Update schedule item error: {e}")
            return False

    def delete_schedule_item(self, schedule_id: int) -> bool:
        """Удалить элемент из плана"""
        try:
            with self.get_session() as session:
                session.execute(
                    text("DELETE FROM production_schedule WHERE id = :id"),
                    {"id": schedule_id},
                )
                session.commit()
                return True
        except Exception as e:
            logger.error(f"Delete schedule item error: {e}")
            return False

    def clear_order_schedule(self, order_id: int) -> bool:
        """Очистить весь план для заказа и сбросить даты в заказе.

        Также очищает route_card_data для перегенерации при новом планировании.
        """
        try:
            with self.get_session() as session:
                # Удаляем расписание
                session.execute(
                    text("DELETE FROM production_schedule WHERE order_id = :order_id"),
                    {"order_id": order_id},
                )
                # Очищаем даты в заказе и route_card_data (будут пересозданы при новом планировании)
                session.execute(
                    text(
                        "UPDATE orders SET start_date = NULL, end_date = NULL, route_card_data = NULL WHERE id = :order_id"
                    ),
                    {"order_id": order_id},
                )
                session.commit()
                return True
        except Exception as e:
            logger.error(f"Clear order schedule error: {e}")
            return False

    def mark_schedule_taken(self, schedule_id: int, user: str) -> bool:
        """Отметить что операция взята в работу

        Args:
            schedule_id: ID записи в production_schedule
            user: имя пользователя (кто взял)

        Returns:
            bool: True если успешно
        """
        try:
            with self.get_session() as session:
                session.execute(
                    text("""
                    UPDATE production_schedule 
                    SET taken_at = NOW(), taken_by = :user, status = 'in_progress'
                    WHERE id = :id AND (taken_at IS NULL OR status = 'planned')
                """),
                    {"id": schedule_id, "user": user},
                )
                session.commit()
                return True
        except Exception as e:
            logger.error(f"Mark schedule taken error: {e}")
            return False

    def mark_schedule_completed(self, schedule_id: int, user: str) -> bool:
        """Отметить что операция завершена

        Args:
            schedule_id: ID записи в production_schedule
            user: имя пользователя (кто завершил)

        Returns:
            bool: True если успешно
        """
        try:
            with self.get_session() as session:
                session.execute(
                    text("""
                    UPDATE production_schedule 
                    SET completed_at = NOW(), completed_by = :user
                    WHERE id = :id AND completed_at IS NULL
                """),
                    {"id": schedule_id, "user": user},
                )
                session.commit()
                return True
        except Exception as e:
            logger.error(f"Mark schedule completed error: {e}")
            return False

    def get_schedule_tracking_stats(self, schedule_id: int) -> dict:
        """Получить статистику отслеживания по операции

        Returns:
            dict с taken_at, completed_at, taken_by, completed_by, avg_time_per_unit
        """
        try:
            with self.get_session() as session:
                result = session.execute(
                    text("""
                    SELECT taken_at, completed_at, taken_by, completed_by, quantity
                    FROM production_schedule
                    WHERE id = :id
                """),
                    {"id": schedule_id},
                )
                row = result.fetchone()
                if not row:
                    return None

                taken_at = row[0]
                completed_at = row[1]
                taken_by = row[2]
                completed_by = row[3]
                quantity = row[4] or 1

                avg_time_per_unit = None
                if taken_at and completed_at:
                    total_seconds = (completed_at - taken_at).total_seconds()
                    avg_time_per_unit = (
                        total_seconds / quantity if quantity > 0 else None
                    )

                return {
                    "taken_at": taken_at,
                    "completed_at": completed_at,
                    "taken_by": taken_by,
                    "completed_by": completed_by,
                    "quantity": quantity,
                    "avg_time_per_unit": avg_time_per_unit,
                }
        except Exception as e:
            logger.error(f"Get schedule tracking stats error: {e}")
            return None

    # ==================== Schedule Events ====================

    def create_schedule_event(
        self, schedule_id: int, event_type: str, user: str
    ) -> bool:
        """Создать событие-флаг для задачи"""
        try:
            with self.get_session() as session:
                session.execute(
                    text("""
                    INSERT INTO schedule_events (schedule_id, event_type, created_by, created_at)
                    VALUES (:schedule_id, :event_type, :user, CURRENT_TIMESTAMP)
                    """),
                    {
                        "schedule_id": schedule_id,
                        "event_type": event_type,
                        "user": user,
                    },
                )
                session.commit()
                return True
        except Exception as e:
            logger.error(f"Create schedule event error: {e}")
            return False

    def get_schedule_events(self, schedule_id: int) -> list:
        """Получить все события для задачи"""
        try:
            with self.get_session() as session:
                result = session.execute(
                    text("""
                    SELECT event_type, created_by, created_at
                    FROM schedule_events
                    WHERE schedule_id = :id
                    ORDER BY created_at DESC
                    """),
                    {"id": schedule_id},
                )
                rows = result.fetchall()
                return [
                    {"event_type": r[0], "created_by": r[1], "created_at": str(r[2])}
                    for r in rows
                ]
        except Exception as e:
            logger.error(f"Get schedule events error: {e}")
            return []

    def get_otk_pending_tasks(self) -> list:
        """Получить задачи ожидающие проверки ОТК"""
        try:
            with self.get_session() as session:
                result = session.execute(
                    text("""
                    SELECT DISTINCT ps.id, ps.order_id, ps.equipment_id, ps.planned_date,
                           ps.status, ps.quantity, ps.taken_at, ps.notes,
                           o.designation, o.detail_name, o.quantity as order_quantity,
                           e.name as equipment_name,
                           op.name as operation_name
                    FROM production_schedule ps
                    LEFT JOIN orders o ON ps.order_id = o.id
                    LEFT JOIN equipment e ON ps.equipment_id = e.id
                    LEFT JOIN route_operations ro ON ps.route_operation_id = ro.id
                    LEFT JOIN operation_types op ON ro.operation_type_id = op.id
                    WHERE ps.id IN (
                        SELECT schedule_id FROM schedule_events 
                        WHERE event_type = 'otk_pending'
                    )
                    AND ps.id NOT IN (
                        SELECT schedule_id FROM schedule_events 
                        WHERE event_type = 'first_piece_checked'
                    )
                    AND ps.status IN ('in_progress', 'planned')
                    ORDER BY ps.planned_date DESC
                """)
                )
                rows = result.fetchall()
                return [
                    {
                        "id": r[0],
                        "order_id": r[1],
                        "equipment_id": r[2],
                        "planned_date": str(r[3]) if r[3] else None,
                        "status": r[4],
                        "quantity": r[5],
                        "taken_at": str(r[6]) if r[6] else None,
                        "notes": r[7],
                        "designation": r[8],
                        "detail_name": r[9],
                        "order_quantity": r[10],
                        "equipment_name": r[11],
                        "operation_name": r[12],
                    }
                    for r in rows
                ]
        except Exception as e:
            logger.error(f"Get OTK pending tasks error: {e}")
            return []

    def create_otk_event(
        self, schedule_id: int, event_type: str, username: str, comment: str = None
    ) -> bool:
        """Создать событие ОТК (otk_pending, otk_approved, otk_rejected)"""
        try:
            with self.get_session() as session:
                session.execute(
                    text("""
                    INSERT INTO schedule_events (schedule_id, event_type, created_by, created_at)
                    VALUES (:schedule_id, :event_type, :username, CURRENT_TIMESTAMP)
                    """),
                    {
                        "schedule_id": schedule_id,
                        "event_type": event_type,
                        "username": username,
                    },
                )

                if comment and event_type == "otk_rejected":
                    session.execute(
                        text("""
                        UPDATE production_schedule 
                        SET notes = COALESCE(notes, '') || :comment
                        WHERE id = :schedule_id
                        """),
                        {"comment": f"\n[ОТК] {comment}", "schedule_id": schedule_id},
                    )

                session.commit()
                return True
        except Exception as e:
            logger.error(f"Create OTK event error: {e}")
            return False

    def get_schedule_item(self, schedule_id: int) -> dict:
        """Получить одну задачу по ID"""
        try:
            with self.get_session() as session:
                result = session.execute(
                    text("""
                    SELECT ps.id, ps.order_id, ps.equipment_id, ps.planned_date,
                           ps.status, ps.quantity, ps.taken_at, ps.completed_at,
                           ps.notes, o.designation, o.detail_name,
                           e.name as equipment_name
                    FROM production_schedule ps
                    LEFT JOIN orders o ON ps.order_id = o.id
                    LEFT JOIN equipment e ON ps.equipment_id = e.id
                    WHERE ps.id = :id
                """),
                    {"id": schedule_id},
                )
                row = result.fetchone()
                if not row:
                    return None
                return {
                    "id": row[0],
                    "order_id": row[1],
                    "equipment_id": row[2],
                    "planned_date": str(row[3]) if row[3] else None,
                    "status": row[4],
                    "quantity": row[5],
                    "taken_at": str(row[6]) if row[6] else None,
                    "completed_at": str(row[7]) if row[7] else None,
                    "notes": row[8],
                    "designation": row[9],
                    "detail_name": row[10],
                    "equipment_name": row[11],
                }
        except Exception as e:
            logger.error(f"Get schedule item error: {e}")
            return None

    def complete_task_with_recalc(
        self, schedule_id: int, actual_quantity: int, user: str
    ) -> dict:
        """Завершить задачу с перерасчётом остатков

        Returns:
            dict: {"success": bool, "message": str, "remainder": int}
        """
        try:
            with self.get_session() as session:
                # 1. Получить данные задачи
                result = session.execute(
                    text("""
                    SELECT id, order_id, route_operation_id, equipment_id, planned_date,
                           quantity, priority, duration_minutes, status
                    FROM production_schedule
                    WHERE id = :id
                    """),
                    {"id": schedule_id},
                )
                row = result.fetchone()
                if not row:
                    return {"success": False, "message": "Задача не найдена"}

                (
                    sched_id,
                    order_id,
                    route_op_id,
                    equip_id,
                    planned_date,
                    planned_qty,
                    priority,
                    duration,
                    _status,
                ) = row

                # 2. Обновить: actual_quantity, completed_at, completed_by, status
                if actual_quantity >= planned_qty:
                    new_status = "completed"
                else:
                    new_status = "delayed"

                session.execute(
                    text("""
                    UPDATE production_schedule
                    SET completed_at = CURRENT_TIMESTAMP,
                        completed_by = :user,
                        status = :status
                    WHERE id = :id
                    """),
                    {
                        "id": schedule_id,
                        "user": user,
                        "status": new_status,
                    },
                )
                session.commit()

                # 3. Перерасчёт остатков
                # Сколько НЕ сделали (если actual < planned, то undone > 0)
                undone = planned_qty - actual_quantity  # 7 - 5 = 2

                if undone != 0:
                    # Определяем дату planned_date
                    planned_date_val = planned_date
                    if hasattr(planned_date_val, "date"):
                        planned_date_val = planned_date_val.date()

                    # Ищем следующее задание: то же оборудование, операция, заказ
                    next_result = session.execute(
                        text("""
                        SELECT id, quantity, planned_date
                        FROM production_schedule
                        WHERE equipment_id = :eq
                          AND route_operation_id = :rop
                          AND order_id = :oid
                          AND planned_date > :pdate
                          AND status != 'completed'
                        ORDER BY planned_date ASC
                        LIMIT 1
                        """),
                        {
                            "eq": equip_id,
                            "rop": route_op_id,
                            "oid": order_id,
                            "pdate": str(planned_date_val),
                        },
                    )
                    next_row = next_result.fetchone()

                    if next_row:
                        next_id, next_qty, _next_date = next_row
                        # Прибавляем недоделанные к следующему дню
                        new_next_qty = next_qty + undone
                        if new_next_qty <= 0:
                            # Полностью закрыли
                            session.execute(
                                text("""
                                UPDATE production_schedule
                                SET quantity = 0, status = 'completed'
                                WHERE id = :id
                                """),
                                {"id": next_id},
                            )
                        else:
                            session.execute(
                                text("""
                                UPDATE production_schedule
                                SET quantity = :qty
                                WHERE id = :id
                                """),
                                {"id": next_id, "qty": new_next_qty},
                            )
                        session.commit()
                    else:
                        # Следующего дня нет — создаём если не доделал
                        if remainder < 0:
                            from datetime import timedelta

                            next_day = planned_date_val
                            if isinstance(next_day, str):
                                from datetime import datetime

                                next_day = datetime.strptime(
                                    next_day, "%Y-%m-%d"
                                ).date()

                            found = False
                            for i in range(1, 30):  # Ищем до 30 дней вперёд
                                candidate = next_day + timedelta(days=i)
                                if candidate.weekday() < 5:  # Пн-Пт
                                    next_day = candidate
                                    found = True
                                    break

                            if found:
                                session.execute(
                                    text("""
                                    INSERT INTO production_schedule
                                        (order_id, route_operation_id, equipment_id, planned_date,
                                         quantity, priority, duration_minutes, status, created_at)
                                    VALUES
                                        (:oid, :rop, :eq, :pdate, :qty, :pri, :dur, 'planned', CURRENT_TIMESTAMP)
                                    """),
                                    {
                                        "oid": order_id,
                                        "rop": route_op_id,
                                        "eq": equip_id,
                                        "pdate": next_day.isoformat(),
                                        "qty": abs(remainder),
                                        "pri": priority,
                                        "dur": duration,
                                    },
                                )
                                session.commit()

                return {
                    "success": True,
                    "message": "Задача завершена",
                    "remainder": -undone,  # отрицательное = недоделка
                }
        except Exception as e:
            logger.error(f"Complete task with recalc error: {e}")
            import traceback

            traceback.print_exc()
            return {"success": False, "message": str(e)}

    # ==================== Order Priority ====================

    def set_order_priority(
        self, order_id: int, priority: int, deadline: datetime = None, notes: str = None
    ) -> bool:
        """Установить приоритет заказа"""
        try:
            with self.get_session() as session:
                if deadline:
                    deadline_val = (
                        deadline.date() if isinstance(deadline, datetime) else deadline
                    )
                else:
                    deadline_val = None

                session.execute(
                    text("""
                    INSERT INTO order_priorities (order_id, priority, deadline, notes)
                    VALUES (:order_id, :priority, :deadline, :notes)
                    ON CONFLICT (order_id) 
                    DO UPDATE SET priority = :priority, deadline = :deadline, notes = :notes
                """),
                    {
                        "order_id": order_id,
                        "priority": priority,
                        "deadline": deadline_val,
                        "notes": notes,
                    },
                )
                session.commit()
                return True
        except Exception as e:
            logger.error(f"Set order priority error: {e}")
            return False

    def get_order_priority(self, order_id: int) -> dict:
        """Получить приоритет заказа"""
        with self.get_session() as session:
            result = session.execute(
                text("""
                SELECT op.id, op.order_id, op.priority, op.deadline, op.notes
                FROM order_priorities op
                WHERE op.order_id = :order_id
            """),
                {"order_id": order_id},
            )
            row = result.fetchone()
            return dict(row._mapping) if row else None

    def get_all_order_priorities(self) -> List[dict]:
        """Получить все приоритеты заказов"""
        with self.get_session() as session:
            result = session.execute(
                text("""
                SELECT op.id, op.order_id, op.priority, op.deadline, op.notes,
                       o.designation, o.detail_name, o.quantity
                FROM order_priorities op
                JOIN orders o ON op.order_id = o.id
                ORDER BY op.priority DESC, op.deadline ASC
            """)
            )
            return [dict(row._mapping) for row in result]

    def delete_order_priority(self, order_id: int) -> bool:
        """Удалить приоритет заказа"""
        try:
            with self.get_session() as session:
                session.execute(
                    text("DELETE FROM order_priorities WHERE order_id = :order_id"),
                    {"order_id": order_id},
                )
                session.commit()
                return True
        except Exception as e:
            logger.error(f"Delete order priority error: {e}")
            return False

    def update_order_priority(self, order_id: int, priority: int) -> bool:
        """Обновить приоритет заказа (upsert в order_priorities)"""
        try:
            with self.get_session() as session:
                session.execute(
                    text("""
                    INSERT INTO order_priorities (order_id, priority, deadline, notes)
                    VALUES (:order_id, :priority, NULL, NULL)
                    ON CONFLICT (order_id)
                    DO UPDATE SET priority = :priority
                """),
                    {"order_id": order_id, "priority": priority},
                )
                session.commit()
                return True
        except Exception as e:
            logger.error(f"Update order priority error: {e}")
            return False

    def get_unplanned_orders(self) -> List[dict]:
        """Получить все заказы, у которых нет записей в production_schedule"""
        try:
            with self.get_session() as session:
                result = session.execute(
                    text("""
                    SELECT o.id, o.route_id, o.quantity, o.blanks_needed, o.route_quantity,
                           o.start_date, o.end_date, o.created_at,
                           o.production_type, o.batch_number,
                           dr.designation, dr.detail_name,
                           mi.mark_name, mi.sortament_name,
                           COALESCE(op_prio.priority, 5) as priority
                    FROM orders o
                    LEFT JOIN detail_routes dr ON o.route_id = dr.id
                    LEFT JOIN material_instances mi ON dr.material_instance_id = mi.id
                    LEFT JOIN order_priorities op_prio ON o.id = op_prio.order_id
                    WHERE o.id NOT IN (
                        SELECT DISTINCT order_id FROM production_schedule WHERE order_id IS NOT NULL
                    )
                    ORDER BY COALESCE(op_prio.priority, 5) ASC, o.created_at ASC
                """)
                )
                return [dict(row._mapping) for row in result]
        except Exception as e:
            logger.error(f"Get unplanned orders error: {e}")
            return []

    def get_schedule_by_id(self, schedule_id: int) -> Optional[dict]:
        """Получить элемент расписания по ID"""
        try:
            with self.get_session() as session:
                result = session.execute(
                    text("""
                    SELECT ps.id, ps.order_id, ps.route_operation_id, ps.equipment_id,
                           ps.planned_date, ps.actual_date, ps.status, ps.priority,
                           ps.quantity, ps.duration_minutes, ps.notes, ps.is_manual_override,
                           ps.taken_at, ps.completed_at, ps.taken_by, ps.completed_by,
                           e.name as equipment_name,
                           dr.designation, dr.detail_name, o.quantity as order_quantity,
                           o.production_type, o.batch_number,
                           ot.name as operation_name,
                           ro.sequence_number, ro.operation_type_id, ro.total_time,
                           mi.mark_name, mi.sortament_name
                    FROM production_schedule ps
                    JOIN orders o ON ps.order_id = o.id
                    LEFT JOIN detail_routes dr ON o.route_id = dr.id
                    LEFT JOIN material_instances mi ON dr.material_instance_id = mi.id
                    LEFT JOIN equipment e ON ps.equipment_id = e.id
                    LEFT JOIN route_operations ro ON ps.route_operation_id = ro.id
                    LEFT JOIN operation_types ot ON ro.operation_type_id = ot.id
                    WHERE ps.id = :schedule_id
                """),
                    {"schedule_id": schedule_id},
                )
                row = result.fetchone()
                return dict(row._mapping) if row else None
        except Exception as e:
            logger.error(f"Get schedule by ID error: {e}")
            return None

    def set_equipment_calendar_day(
        self,
        equipment_id: int,
        date,
        is_working: bool,
        working_hours: int = 8,
        notes: str = None,
    ) -> bool:
        """Установить рабочий/нерабочий день для станка (upsert)"""
        try:
            date_val = date.date() if isinstance(date, datetime) else date
            with self.get_session() as session:
                session.execute(
                    text("""
                    INSERT INTO equipment_calendar (equipment_id, date, is_working, working_hours, notes)
                    VALUES (:equipment_id, :date, :is_working, :working_hours, :notes)
                    ON CONFLICT (equipment_id, date)
                    DO UPDATE SET is_working = :is_working, working_hours = :working_hours, notes = :notes
                """),
                    {
                        "equipment_id": equipment_id,
                        "date": date_val,
                        "is_working": is_working,
                        "working_hours": working_hours,
                        "notes": notes,
                    },
                )
                session.commit()
                return True
        except Exception as e:
            logger.error(f"Set equipment calendar day error: {e}")
            return False

    def calculate_equipment_load(
        self, date_from: datetime, date_to: datetime, equipment_id: int = None
    ) -> List[dict]:
        """Рассчитать загрузку оборудования за период"""
        try:
            with self.get_session() as session:
                params = {
                    "date_from": date_from.date()
                    if isinstance(date_from, datetime)
                    else date_from,
                    "date_to": date_to.date()
                    if isinstance(date_to, datetime)
                    else date_to,
                }
                eq_filter = (
                    "AND ps.equipment_id = :equipment_id" if equipment_id else ""
                )
                if equipment_id:
                    params["equipment_id"] = equipment_id

                result = session.execute(
                    text(f"""
                    SELECT
                        e.id as equipment_id,
                        e.name as equipment_name,
                        e.equipment_type,
                        COALESCE(SUM(ps.duration_minutes * ps.quantity), 0) as total_minutes,
                        COUNT(ps.id) as operations_count,
                        COUNT(DISTINCT ps.order_id) as orders_count,
                        COUNT(DISTINCT ps.planned_date) as working_days
                    FROM equipment e
                    LEFT JOIN production_schedule ps ON e.id = ps.equipment_id
                        AND ps.planned_date >= :date_from
                        AND ps.planned_date <= :date_to
                        {eq_filter}
                    WHERE e.is_active = true
                    GROUP BY e.id, e.name, e.equipment_type
                    ORDER BY total_minutes DESC
                """),
                    params,
                )
                rows = [dict(row._mapping) for row in result]

                # Рассчитываем процент загрузки (8 часов = 480 минут в день)
                for row in rows:
                    total_possible_minutes = (
                        row["working_days"] * 480 if row["working_days"] > 0 else 480
                    )
                    row["utilization_percent"] = (
                        round((row["total_minutes"] / total_possible_minutes) * 100, 1)
                        if total_possible_minutes > 0
                        else 0
                    )

                return rows
        except Exception as e:
            logger.error(f"Calculate equipment load error: {e}")
            return []

    # ==================== Routes (Маршруты обработки) ====================

    def create_route(
        self,
        detail_name: str,
        designation: str = None,
        material_instance_id: int = None,
        pdf_file: str = None,
        created_by: str = None,
        quantity: int = 1,
        preprocessing_data: str = None,
    ) -> dict:
        """Создание маршрута обработки детали"""
        try:
            with self.get_session() as session:
                result = session.execute(
                    text("""
                    INSERT INTO detail_routes (detail_name, designation, material_instance_id, pdf_file, created_by, quantity, preprocessing_data)
                    VALUES (:detail_name, :designation, :material_instance_id, :pdf_file, :created_by, :quantity, :preprocessing_data)
                    RETURNING id
                """),
                    {
                        "detail_name": detail_name,
                        "designation": designation,
                        "material_instance_id": material_instance_id,
                        "pdf_file": pdf_file,
                        "created_by": created_by,
                        "quantity": quantity,
                        "preprocessing_data": preprocessing_data,
                    },
                )
                route_id = result.scalar()
                session.commit()
                return {"id": route_id, "detail_name": detail_name}
        except Exception as e:
            logger.error(f"Create route error: {e}")
            return None

    def add_route_operation(
        self,
        route_id: int,
        operation_type_id: int = None,
        equipment_id: int = None,
        sequence_number: int = 1,
        duration_minutes: int = None,
        prep_time: int = 0,
        control_time: int = 0,
        parts_count: int = 1,
        notes: str = None,
        workshop_id: int = None,
        is_cooperation: bool = False,
        coop_company_id: int = None,
        coop_duration_days: int = 0,
        coop_position: str = "start",
    ) -> dict:
        """Добавление операции в маршрут"""
        try:
            total_time = (
                (duration_minutes or 0) + (prep_time or 0) + (control_time or 0)
            )

            with self.get_session() as session:
                session.execute(
                    text("""
                    INSERT INTO route_operations (
                        route_id, operation_type_id, equipment_id, sequence_number,
                        duration_minutes, prep_time, control_time, total_time,
                        parts_count, notes, workshop_id, is_cooperation, coop_company_id,
                        coop_duration_days, coop_position
                    )
                    VALUES (
                        :route_id, :operation_type_id, :equipment_id, :sequence_number,
                        :duration_minutes, :prep_time, :control_time, :total_time,
                        :parts_count, :notes, :workshop_id, :is_cooperation, :coop_company_id,
                        :coop_duration_days, :coop_position
                    )
                """),
                    {
                        "route_id": route_id,
                        "operation_type_id": operation_type_id,
                        "equipment_id": equipment_id,
                        "sequence_number": sequence_number,
                        "duration_minutes": duration_minutes,
                        "prep_time": prep_time,
                        "control_time": control_time,
                        "total_time": total_time,
                        "parts_count": parts_count,
                        "notes": notes,
                        "workshop_id": workshop_id,
                        "is_cooperation": is_cooperation,
                        "coop_company_id": coop_company_id,
                        "coop_duration_days": coop_duration_days,
                        "coop_position": coop_position,
                    },
                )
                session.commit()
                return {"success": True}
        except Exception as e:
            logger.error(f"Add route operation error: {e}")
            return None

    def get_all_routes(self) -> List[dict]:
        """Получение всех маршрутов"""
        with self.get_session() as session:
            result = session.execute(
                text("""
                SELECT dr.id, dr.detail_name, dr.designation, dr.version, dr.status, dr.created_at,
                       dr.quantity, dr.dimension1 as length, dr.dimension2, dr.preprocessing_data, dr.approved, dr.created_by, 
                       dr.pdf_path, mi.mark_name, mi.sortament_name
                FROM detail_routes dr
                LEFT JOIN material_instances mi ON dr.material_instance_id = mi.id
                ORDER BY dr.created_at DESC
            """)
            )
            return [dict(row._mapping) for row in result]

    def get_route_operations(self, route_id: int) -> List[dict]:
        """Получение операций маршрута"""
        with self.get_session() as session:
            result = session.execute(
                text("""
                SELECT ro.id, ro.operation_type_id, ro.workshop_id, ro.sequence_number, ro.duration_minutes, ro.prep_time,
                       ro.control_time, ro.total_time, ro.parts_count, ro.notes,
                       ro.equipment_id, ro.is_cooperation, ro.coop_company_id, ro.cost_operation,
                       ro.cost_logistics, ro.coop_duration_days, ro.coop_position,
                       ot.name as operation_name,
                       e.name as equipment_name,
                       c.name as coop_company_name
                FROM route_operations ro
                LEFT JOIN operation_types ot ON ro.operation_type_id = ot.id
                LEFT JOIN equipment e ON ro.equipment_id = e.id
                LEFT JOIN cooperatives c ON ro.coop_company_id = c.id
                WHERE ro.route_id = :route_id
                ORDER BY ro.sequence_number
            """),
                {"route_id": route_id},
            )
            return [dict(row._mapping) for row in result]

    def get_route_by_id(self, route_id: int) -> Optional[dict]:
        """Получение маршрута по ID"""
        with self.get_session() as session:
            result = session.execute(
                text("""
                SELECT dr.id, dr.detail_id, dr.detail_name, dr.designation, dr.version, dr.status, dr.created_at,
                       dr.quantity,
                       COALESCE(dr.length, dr.dimension1) as length,
                       COALESCE(dr.diameter, dr.dimension2) as diameter,
                       dr.dimension1, dr.dimension2,
                       dr.parts_per_blank, dr.waste_percent, dr.preprocessing, dr.preprocessing_data,
                       dr.primitive_form_id, dr.prim_dim1, dr.prim_dim2, dr.prim_dim3,
                       dr.lot_size, dr.volume, dr.calculated_mass, dr.blank_cost,
                       dr.manual_mass_input, dr.material_cost, dr.unit_cost, dr.labor_cost,
                       dr.depreciation_cost, dr.utility_cost, dr.dimensions, dr.preprocessing_dimensions,
                       dr.approved, dr.created_by, dr.pdf_path, dr.material_instance_id,
                       mi.mark_name, mi.sortament_name
                FROM detail_routes dr
                LEFT JOIN material_instances mi ON dr.material_instance_id = mi.id
                WHERE dr.id = :route_id
                """),
                {"route_id": route_id},
            )
            row = result.fetchone()
            if not row:
                return None
            route = dict(row._mapping)

            # Загружаем операции
            ops_result = session.execute(
                text("""
                SELECT ro.id, ro.operation_type_id, ro.equipment_id, ro.sequence_number,
                       ro.duration_minutes, ro.prep_time, ro.control_time, ro.total_time,
                       ro.parts_count, ro.notes, ro.workshop_id, ro.is_cooperation,
                       ro.coop_company_id,
                       ot.name as operation_name,
                       e.name as equipment_name
                FROM route_operations ro
                LEFT JOIN operation_types ot ON ro.operation_type_id = ot.id
                LEFT JOIN equipment e ON ro.equipment_id = e.id
                WHERE ro.route_id = :route_id
                ORDER BY ro.sequence_number
                """),
                {"route_id": route_id},
            )
            route["operations"] = [dict(op._mapping) for op in ops_result]
            return route

    def update_route(self, route_id: int, **kwargs) -> bool:
        """Обновление маршрута"""
        try:
            allowed_fields = {
                "detail_id",
                "detail_name",
                "designation",
                "version",
                "material_instance_id",
                "quantity",
                "dimension1",
                "dimension2",
                "parts_per_blank",
                "waste_percent",
                "preprocessing",
                "preprocessing_data",
                "primitive_form_id",
                "prim_dim1",
                "prim_dim2",
                "prim_dim3",
                "lot_size",
                "volume",
                "calculated_mass",
                "blank_cost",
                "manual_mass_input",
                "material_cost",
                "unit_cost",
                "labor_cost",
                "depreciation_cost",
                "utility_cost",
                "dimensions",
                "preprocessing_dimensions",
                "status",
            }
            updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
            if not updates:
                return False

            set_clause = ", ".join(f"{k} = :{k}" for k in updates)
            updates["route_id"] = route_id

            with self.get_session() as session:
                session.execute(
                    text(f"""
                    UPDATE detail_routes SET {set_clause}, updated_at = NOW()
                    WHERE id = :route_id
                    """),
                    updates,
                )
                session.commit()
                return True
        except Exception as e:
            logger.error(f"Update route error: {e}")
            return False

    def update_route_operation(self, op_id: int, **kwargs) -> bool:
        """Обновление отдельной операции маршрута"""
        try:
            allowed_fields = {
                "sequence_number",
                "duration_minutes",
                "prep_time",
                "control_time",
                "parts_count",
                "notes",
                "operation_type_id",
                "equipment_id",
                "workshop_id",
                "is_cooperation",
                "coop_company_id",
                "coop_duration_days",
                "coop_position",
            }
            updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
            if not updates:
                return False

            set_clause = ", ".join(f"{k} = :{k}" for k in updates)
            updates["op_id"] = op_id

            with self.get_session() as session:
                session.execute(
                    text(f"""
                    UPDATE route_operations SET {set_clause}
                    WHERE id = :op_id
                    """),
                    updates,
                )
                session.commit()
                return True
        except Exception as e:
            logger.error(f"Update route operation error: {e}")
            return False

    def delete_route_operations(self, route_id: int) -> bool:
        """Удаление всех операций маршрута"""
        try:
            with self.get_session() as session:
                session.execute(
                    text("DELETE FROM route_operations WHERE route_id = :route_id"),
                    {"route_id": route_id},
                )
                session.commit()
                return True
        except Exception as e:
            logger.error(f"Delete route operations error: {e}")
            return False

    def delete_route_operation(self, op_id: int) -> bool:
        """Удаление одной операции маршрута"""
        try:
            with self.get_session() as session:
                session.execute(
                    text("DELETE FROM route_operations WHERE id = :op_id"),
                    {"op_id": op_id},
                )
                session.commit()
                return True
        except Exception as e:
            logger.error(f"Delete route operation error: {e}")
            return False

    def delete_route(self, route_id: int) -> bool:
        """Удаление маршрута"""
        try:
            with self.get_session() as session:
                session.execute(
                    text("DELETE FROM route_operations WHERE route_id = :route_id"),
                    {"route_id": route_id},
                )
                session.execute(
                    text("DELETE FROM detail_routes WHERE id = :route_id"),
                    {"route_id": route_id},
                )
                session.commit()
                return True
        except Exception as e:
            logger.error(f"Delete route error: {e}")
            return False

    def get_next_batch_number(self, production_type: str = "piece") -> str:
        """Получить следующий номер партии

        Args:
            production_type: 'piece' - штучное (Ш), 'batch' - партийное (П)

        Returns:
            str: номер партии, например 'Ш001', 'П001'
        """
        prefix = "Ш" if production_type == "piece" else "П"
        try:
            with self.engine.connect() as conn:
                # Получаем текущий счётчик для данного prefix
                result = conn.execute(
                    text(
                        "SELECT last_number FROM batch_counter WHERE prefix = :prefix"
                    ),
                    {"prefix": prefix},
                )
                row = result.fetchone()

                if row:
                    last_number = row[0]
                else:
                    # Если счётчика нет для этого prefix, создаём
                    conn.execute(
                        text(
                            "INSERT INTO batch_counter (prefix, last_number) VALUES (:prefix, 0)"
                        ),
                        {"prefix": prefix},
                    )
                    last_number = 0

                # Инкрементируем
                new_number = last_number + 1
                conn.execute(
                    text(
                        "UPDATE batch_counter SET last_number = :num WHERE prefix = :prefix"
                    ),
                    {"num": new_number, "prefix": prefix},
                )
                conn.commit()

                # Формируем номер партии
                return f"{prefix}{new_number:03d}"
        except Exception as e:
            logger.error(f"Get next batch number error: {e}")
            return f"{prefix}ERR"

    def reset_batch_counter(self, production_type: str = None):
        """Сбросить счётчик партий

        Args:
            production_type: 'piece' сбросит Ш, 'batch' сбросит П, None - оба
        """
        try:
            with self.engine.connect() as conn:
                if production_type == "piece" or production_type is None:
                    conn.execute(
                        text(
                            "UPDATE batch_counter SET last_number = 0 WHERE prefix = 'Ш'"
                        )
                    )
                if production_type == "batch" or production_type is None:
                    conn.execute(
                        text(
                            "UPDATE batch_counter SET last_number = 0 WHERE prefix = 'П'"
                        )
                    )
                conn.commit()
        except Exception as e:
            logger.error(f"Reset batch counter error: {e}")

    def create_order(
        self,
        route_id: int,
        quantity: int,
        blanks_needed: int,
        route_quantity: int = None,
        created_by: str = None,
        production_type: str = "piece",
        batch_number: str = None,
    ) -> dict:
        """Создание заказа - данные берутся из detail_routes и material_instances через JOIN

        Args:
            production_type: 'piece' - штучное, 'batch' - партийное
            batch_number: номер партии (если не указан - генерируется автоматически)
        """
        try:
            # Генерируем номер партии если не указан
            if batch_number is None:
                batch_number = self.get_next_batch_number(production_type)

            with self.get_session() as session:
                result = session.execute(
                    text("""
                    INSERT INTO orders (route_id, quantity, blanks_needed, route_quantity, created_by, production_type, batch_number)
                    VALUES (:route_id, :quantity, :blanks_needed, :route_quantity, :created_by, :production_type, :batch_number)
                    RETURNING id
                """),
                    {
                        "route_id": route_id,
                        "quantity": quantity,
                        "blanks_needed": blanks_needed,
                        "route_quantity": route_quantity,
                        "created_by": created_by,
                        "production_type": production_type,
                        "batch_number": batch_number,
                    },
                )
                row = result.fetchone()
                session.commit()
                return (
                    {"id": row.id, "batch_number": batch_number, "success": True}
                    if row
                    else None
                )
        except Exception as e:
            logger.error(f"Create order error: {e}")
            return None

    def get_all_orders(self) -> List[dict]:
        """Получение всех заказов"""
        try:
            with self.get_session() as session:
                result = session.execute(
                    text("""
                    SELECT o.id, o.route_id, o.quantity, o.blanks_needed, o.route_quantity,
                           o.pdf_path, o.start_date, o.end_date, o.created_by, o.created_at,
                           o.app_id, o.id_1c, o.order_number, o.lot_size, o.file, o.status,
                           o.in_progress, o.blanks_quantity, o.blank_size, o.preprocessing_size,
                           o.production_type, o.batch_number,
                           o.manual_detail_name, o.manual_quantity, o.route_card_data,
                           COALESCE(dr.designation, o.manual_detail_name, 'Без маршрута') as designation,
                           COALESCE(dr.detail_name, '') as detail_name,
                           mi.mark_name, mi.sortament_name,
                           COALESCE(op_prio.priority, 5) as priority
                    FROM orders o
                    LEFT JOIN detail_routes dr ON o.route_id = dr.id
                    LEFT JOIN material_instances mi ON dr.material_instance_id = mi.id
                    LEFT JOIN order_priorities op_prio ON o.id = op_prio.order_id
                    ORDER BY o.created_at DESC
                """)
                )
                return [dict(row._mapping) for row in result]
        except Exception as e:
            logger.error(f"Get all orders error: {e}")
            return []

    def get_order(self, order_id: int) -> dict:
        """Получение заказа по ID"""
        try:
            with self.get_session() as session:
                result = session.execute(
                    text("""
                    SELECT o.id, o.route_id, o.quantity, o.blanks_needed, o.route_quantity,
                           o.pdf_path, o.start_date, o.end_date, o.created_by, o.created_at,
                           o.app_id, o.id_1c, o.order_number, o.lot_size, o.file, o.status,
                           o.in_progress, o.blanks_quantity, o.blank_size, o.preprocessing_size,
                           o.production_type, o.batch_number,
                           o.manual_detail_name, o.manual_quantity, o.route_card_data,
                           COALESCE(dr.designation, o.manual_detail_name, 'Без маршрута') as designation,
                           COALESCE(dr.detail_name, '') as detail_name,
                           mi.mark_name, mi.sortament_name,
                           COALESCE(op_prio.priority, 5) as priority
                    FROM orders o
                    LEFT JOIN detail_routes dr ON o.route_id = dr.id
                    LEFT JOIN material_instances mi ON dr.material_instance_id = mi.id
                    LEFT JOIN order_priorities op_prio ON o.id = op_prio.order_id
                    WHERE o.id = :order_id
                """),
                    {"order_id": order_id},
                )
                row = result.fetchone()
                return dict(row._mapping) if row else None
        except Exception as e:
            logger.error(f"Get order error: {e}")
            return None

    def update_order_pdf_path(self, order_id: int, pdf_path: str) -> bool:
        """Обновление пути к PDF заказа"""
        try:
            with self.get_session() as session:
                session.execute(
                    text("UPDATE orders SET pdf_path = :pdf_path WHERE id = :id"),
                    {"pdf_path": pdf_path, "id": order_id},
                )
                session.commit()
                return True
        except Exception as e:
            logger.error(f"Update order pdf path error: {e}")
            return False

    def update_order_card_data(self, order_id: int, card_data: dict) -> bool:
        """Обновление данных ЭМК (route_card_data) для заказа"""
        try:
            with self.get_session() as session:
                session.execute(
                    text(
                        "UPDATE orders SET route_card_data = :card_data WHERE id = :id"
                    ),
                    {"card_data": json.dumps(card_data), "id": order_id},
                )
                session.commit()
                return True
        except Exception as e:
            logger.error(f"Update order card data error: {e}")
            return False

    def delete_order(self, order_id: int) -> bool:
        """Удаление заказа. При удалении также очищается ЭМК (route_card_data)."""
        try:
            with self.get_session() as session:
                # Получаем информацию о заказе перед удалением
                result = session.execute(
                    text(
                        "SELECT production_type, batch_number FROM orders WHERE id = :id"
                    ),
                    {"id": order_id},
                )
                order_row = result.fetchone()

                if not order_row:
                    return False

                production_type = order_row[0]
                batch_number = order_row[1]

                # Очищаем route_card_data перед удалением заказа
                session.execute(
                    text("UPDATE orders SET route_card_data = NULL WHERE id = :id"),
                    {"id": order_id},
                )

                # Удаляем заказ
                session.execute(
                    text("DELETE FROM orders WHERE id = :id"), {"id": order_id}
                )
                session.commit()

                # Проверяем остались ли ещё заказы с таким же типом производства
                result = session.execute(
                    text("SELECT COUNT(*) FROM orders WHERE production_type = :pt"),
                    {"pt": production_type},
                )
                count_row = result.fetchone()
                remaining_count = count_row[0] if count_row else 0

                # Если это был последний заказ с таким типом - сбрасываем счётчик
                if remaining_count == 0:
                    self.reset_batch_counter(production_type)
                    logger.info(f"Сброшен счётчик для типа: {production_type}")

                return True
        except Exception as e:
            logger.error(f"Delete order error: {e}")
            return False

    def update_order_dates(self, order_id: int, start_date: str, end_date: str) -> bool:
        """Обновление дат производства заказа"""
        try:
            with self.get_session() as session:
                session.execute(
                    text("""
                    UPDATE orders SET start_date = :start_date, end_date = :end_date 
                    WHERE id = :id
                """),
                    {"start_date": start_date, "end_date": end_date, "id": order_id},
                )
                session.commit()
                return True
        except Exception as e:
            logger.error(f"Update order dates error: {e}")
            return False

    def get_user_available_tools(
        self, user_id: int, search: str = None, equipment_id: int = None
    ) -> List[Dict[str, Any]]:
        """Получить доступные инструменты для пользователя со всех источников или конкретного станка"""
        import json
        from models import Item, User, WorkshopInventory, UserItems, Equipment

        tools = []

        # Для поиска
        search_lower = search.lower() if search else None

        with self.get_session() as session:
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                return tools

            # 1. Основной склад (всегда показываем)
            items = session.query(Item).filter(Item.quantity > 0).all()
            for item in items:
                if search_lower and search_lower not in item.name.lower():
                    continue
                tools.append(
                    {
                        "item_id": item.item_id,
                        "item_name": item.name,
                        "quantity": item.quantity,
                        "source": "main",
                        "source_name": "Основной склад",
                        "available": item.quantity,
                    }
                )

            # 2. Склад станка - ВСЕГДА показываем все станки пользователя
            target_equipment_ids = []

            # Проверяем все станки пользователя
            user_workstations = []
            if user.workstation:
                user_workstations.append(user.workstation)
            if user.workstations:
                try:
                    ws = json.loads(user.workstations)
                    if isinstance(ws, list):
                        user_workstations.extend(ws)
                except:
                    pass

            logger.info(
                f"get_user_available_tools: user_workstations = {user_workstations}"
            )

            for ws_name in user_workstations:
                    # Fuzzy matching - ищем по частичному совпадению
                    ws_lower = ws_name.lower().strip() if ws_name else ""
                    eq = None

                    # Сначала точное совпадение
                    eq = (
                        session.query(Equipment)
                        .filter(Equipment.name == ws_name)
                        .first()
                    )

                    # Если не найден - ищем fuzzy matching
                    if not eq:
                        all_equipment = session.query(Equipment).all()
                        for e in all_equipment:
                            e_name_lower = e.name.lower() if e.name else ""
                            if ws_lower in e_name_lower or e_name_lower in ws_lower:
                                eq = e
                                logger.info(
                                    f"get_user_available_tools: fuzzy match found - {ws_name} -> {e.name} (id={e.id})"
                                )
                                break

                    if eq and eq.id not in target_equipment_ids:
                        target_equipment_ids.append(eq.id)

            # Получаем инструменты для целевых станков
            for eq_id in target_equipment_ids:
                eq = session.query(Equipment).filter(Equipment.id == eq_id).first()
                if not eq:
                    continue

                logger.info(
                    f"get_user_available_tools: looking at equipment_id={eq.id}, name={eq.name}"
                )
                ws_inventory = (
                    session.query(WorkshopInventory)
                    .filter(
                        WorkshopInventory.equipment_id == eq.id,
                        WorkshopInventory.quantity > 0,
                    )
                    .all()
                )
                logger.info(
                    f"get_user_available_tools: found {len(ws_inventory)} items in workshop inventory for {eq.name}"
                )
                for ws_item in ws_inventory:
                    item_name = ws_item.item.name if ws_item.item else ""
                    if search_lower and search_lower not in item_name.lower():
                        continue
                    tool_data = {
                        "item_id": ws_item.item.item_id if ws_item.item else "",
                        "item_name": item_name,
                        "quantity": ws_item.quantity,
                        "source": "workshop",
                        "source_name": eq.name,
                        "available": ws_item.quantity,
                        "equipment_id": eq.id,
                    }
                    logger.info(f"get_user_available_tools: adding tool: {tool_data}")
                    tools.append(tool_data)

            # 3. Инструменты на руках
            user_items = (
                session.query(UserItems).filter(UserItems.user_id == user_id).all()
            )
            for ui in user_items:
                item_name = ui.item.name if ui.item else ""
                if search_lower and search_lower not in item_name.lower():
                    continue
                tools.append(
                    {
                        "item_id": ui.item.item_id if ui.item else "",
                        "item_name": item_name,
                        "quantity": ui.quantity,
                        "source": "user",
                        "source_name": "У меня",
                        "available": ui.quantity,
                    }
                )

        return tools

    def get_order_tools(self, order_id: int) -> List[Dict[str, Any]]:
        """Получить список инструментов для заказа из route_card_data"""
        import json
        from models import Order

        tools = []
        try:
            with self.get_session() as session:
                order = session.query(Order).filter(Order.id == order_id).first()
                if order and order.route_card_data:
                    try:
                        # Проверяем: если это уже dict - используем как есть, если строка - парсим
                        if isinstance(order.route_card_data, dict):
                            route_card_data = order.route_card_data
                        else:
                            route_card_data = json.loads(order.route_card_data)
                        tools = route_card_data.get("tools", [])
                        logger.info(f"get_order_tools: found {len(tools)} tools for order {order_id}")
                    except Exception as e:
                        logger.error(f"get_order_tools: error parsing route_card_data: {e}")
        except Exception as e:
            logger.error(f"get_order_tools: error: {e}")
        return tools

    def take_tools_for_order(
        self, order_id: int, tools: List[Dict[str, Any]], user_id: int
    ) -> bool:
        """Взять инструменты для заказа"""
        import json
        from models import Item, WorkshopInventory, UserItems, Order, User, Equipment

        try:
            with self.get_session() as session:
                order = session.query(Order).filter(Order.id == order_id).first()
                if not order:
                    return False

                # Десериализуем JSON
                route_card_data = {}
                if order.route_card_data:
                    try:
                        route_card_data = json.loads(order.route_card_data)
                    except:
                        pass
                existing_tools = route_card_data.get("tools", [])

                for tool in tools:
                    item_id = tool.get("item_id")
                    quantity = tool.get("quantity", 1)
                    source = tool.get("source")

                    if source == "main":
                        item = (
                            session.query(Item).filter(Item.item_id == item_id).first()
                        )
                        if item and item.quantity >= quantity:
                            item.quantity -= quantity
                    elif source == "workshop":
                        equipment_id = tool.get("equipment_id")
                        ws_item_query = session.query(WorkshopInventory).filter(
                            WorkshopInventory.equipment_id == equipment_id
                        )
                        if item_id:
                            ws_item = ws_item_query.filter(
                                WorkshopInventory.item_id == item.id
                            ).first()
                        else:
                            ws_item = None
                        if ws_item and ws_item.quantity >= quantity:
                            ws_item.quantity -= quantity
                    elif source == "user":
                        ui = (
                            session.query(UserItems)
                            .filter(
                                UserItems.user_id == user_id,
                                UserItems.item_id == item.id,
                            )
                            .first()
                        )
                        if ui and ui.quantity >= quantity:
                            ui.quantity -= quantity
                            if ui.quantity <= 0:
                                session.delete(ui)

                    existing_tools.append(
                        {
                            "item_id": item_id,
                            "item_name": tool.get("item_name", item_id),
                            "quantity": quantity,
                            "source": source,
                            "source_name": tool.get("source_name"),
                            "status": "in_work",
                        }
                    )

                route_card_data["tools"] = existing_tools
                order.route_card_data = json.dumps(route_card_data)
                session.commit()
                return True
        except Exception as e:
            logger.error(f"Error taking tools for order: {e}")
            return False

    def complete_tools_for_order(
        self, order_id: int, tools: List[Dict[str, Any]], user_id: int
    ) -> bool:
        """Завершить инструменты заказа (списать или вернуть)"""
        import json
        from models import Item, WorkshopInventory, UserItems, Order, User, Equipment

        try:
            with self.get_session() as session:
                order = session.query(Order).filter(Order.id == order_id).first()
                if not order:
                    return False

                user = session.query(User).filter(User.id == user_id).first()
                if not user or not user.workstation:
                    return False

                equipment = (
                    session.query(Equipment)
                    .filter(Equipment.name == user.workstation)
                    .first()
                )
                if not equipment:
                    return False

                # Десериализуем JSON
                route_card_data = {}
                if order.route_card_data:
                    try:
                        route_card_data = json.loads(order.route_card_data)
                    except:
                        pass
                existing_tools = route_card_data.get("tools", [])

                for tool in tools:
                    item_id = tool.get("item_id")
                    quantity = tool.get("quantity", 1)
                    action = tool.get("action")

                    if action == "writeoff":
                        existing_tools = [
                            t for t in existing_tools if t.get("item_id") != item_id
                        ]
                    elif action == "return":
                        item = (
                            session.query(Item).filter(Item.item_id == item_id).first()
                        )
                        if item:
                            ws_item = (
                                session.query(WorkshopInventory)
                                .filter(
                                    WorkshopInventory.equipment_id == equipment.id,
                                    WorkshopInventory.item_id == item.id,
                                )
                                .first()
                            )

                            if ws_item:
                                ws_item.quantity += quantity
                            else:
                                ws_item = WorkshopInventory(
                                    equipment_id=equipment.id,
                                    item_id=item.id,
                                    quantity=quantity,
                                )
                                session.add(ws_item)

                        for t in existing_tools:
                            if t.get("item_id") == item_id:
                                t["status"] = "returned"

                route_card_data["tools"] = existing_tools
                order.route_card_data = json.dumps(route_card_data)
                session.commit()
                return True
        except Exception as e:
            logger.error(f"Error completing tools for order: {e}")
            return False

    # ==================== Details (ДСЕ) ====================

    def get_all_details(self) -> List[dict]:
        """Получение всех деталей из справочника"""
        with self.get_session() as session:
            result = session.execute(
                text("""
                SELECT d.id, d.detail_id, d.lotzman_id, d.detail_type, d.designation, 
                       d.name, d.version, d.is_actual, d.drawing, d.correct_designation,
                       d.creator_id, u.username as creator_name, d.created_at
                FROM details d
                LEFT JOIN users u ON d.creator_id = u.id
                ORDER BY d.designation, d.name
            """)
            )
            return [dict(row._mapping) for row in result]

    def get_detail_by_id(self, detail_id: int) -> Optional[dict]:
        """Получение детали по ID"""
        with self.get_session() as session:
            result = session.execute(
                text("""
                SELECT d.id, d.detail_id, d.lotzman_id, d.detail_type, d.designation, 
                       d.name, d.version, d.is_actual, d.drawing, d.correct_designation,
                       d.creator_id, u.username as creator_name, d.created_at
                FROM details d
                LEFT JOIN users u ON d.creator_id = u.id
                WHERE d.id = :id
            """),
                {"id": detail_id},
            )
            row = result.fetchone()
            return dict(row._mapping) if row else None

    def get_detail_by_designation(self, designation: str) -> Optional[dict]:
        """Получение детали по обозначению"""
        with self.get_session() as session:
            result = session.execute(
                text("""
                SELECT d.id, d.detail_id, d.lotzman_id, d.detail_type, d.designation, 
                       d.name, d.version, d.is_actual, d.drawing, d.correct_designation,
                       d.creator_id, u.username as creator_name, d.created_at
                FROM details d
                LEFT JOIN users u ON d.creator_id = u.id
                WHERE d.designation = :designation
            """),
                {"designation": designation},
            )
            row = result.fetchone()
            return dict(row._mapping) if row else None

    def create_detail(
        self,
        designation: str,
        name: str,
        detail_type: str = "Деталь",
        creator_id: int = None,
        lotzman_id: str = None,
        version: float = 1.0,
    ) -> Optional[dict]:
        """Создание новой детали"""
        import uuid

        # Проверяем, существует ли пользователь
        if creator_id:
            with self.get_session() as session:
                user_exists = session.execute(
                    text("SELECT 1 FROM users WHERE id = :id"), {"id": creator_id}
                ).fetchone()
                if not user_exists:
                    creator_id = None

        try:
            with self.get_session() as session:
                detail_id = str(uuid.uuid4())
                result = session.execute(
                    text("""
                    INSERT INTO details (detail_id, lotzman_id, detail_type, designation, name, 
                                        version, is_actual, correct_designation, creator_id)
                    VALUES (:detail_id, :lotzman_id, :detail_type, :designation, :name, 
                            :version, true, true, :creator_id)
                    RETURNING id
                """),
                    {
                        "detail_id": detail_id,
                        "lotzman_id": lotzman_id,
                        "detail_type": detail_type,
                        "designation": designation,
                        "name": name,
                        "version": version,
                        "creator_id": creator_id,
                    },
                )
                new_id = result.scalar()
                session.commit()

                return self.get_detail_by_id(new_id)
        except Exception as e:
            logger.error(f"Create detail error: {e}")
            return None

    def delete_detail(self, detail_id: int) -> bool:
        """Удаление детали"""
        try:
            with self.get_session() as session:
                session.execute(
                    text("DELETE FROM details WHERE id = :id"), {"id": detail_id}
                )
                session.commit()
                return True
        except Exception as e:
            logger.error(f"Delete detail error: {e}")
            return False

    def get_calendar_config(
        self, user_id: int, config_key: str = "default"
    ) -> Optional[Dict]:
        """Получить настройки календаря пользователя"""
        try:
            from models import CalendarConfig

            with self.get_session() as session:
                config = (
                    session.query(CalendarConfig)
                    .filter(
                        CalendarConfig.user_id == user_id,
                        CalendarConfig.config_key == config_key,
                    )
                    .first()
                )
                return config.to_dict() if config else None
        except Exception as e:
            logger.error(f"Get calendar config error: {e}")
            return None

    def save_calendar_config(
        self,
        user_id: int,
        visible_equipment: List[int],
        equipment_order: List[int],
        panel_visible: bool = True,
        config_key: str = "default",
    ) -> bool:
        """Сохранить настройки календаря пользователя"""
        try:
            import json
            from sqlalchemy import text
            from models import CalendarConfig

            with self.get_session() as session:
                # Сначала проверяем что пользователь существует
                user_exists = session.execute(
                    text("SELECT 1 FROM users WHERE id = :user_id"),
                    {"user_id": user_id},
                ).fetchone()

                if not user_exists:
                    logger.warning(
                        f"User {user_id} not found, skipping calendar config save"
                    )
                    return False

                config = (
                    session.query(CalendarConfig)
                    .filter(
                        CalendarConfig.user_id == user_id,
                        CalendarConfig.config_key == config_key,
                    )
                    .first()
                )

                if config:
                    config.visible_equipment = json.dumps(visible_equipment)
                    config.equipment_order = json.dumps(equipment_order)
                    config.panel_visible = panel_visible
                else:
                    config = CalendarConfig(
                        user_id=user_id,
                        config_key=config_key,
                        visible_equipment=json.dumps(visible_equipment),
                        equipment_order=json.dumps(equipment_order),
                        panel_visible=panel_visible,
                    )
                    session.add(config)

                session.commit()
                return True
        except Exception as e:
            logger.error(f"Save calendar config error: {e}")
            return False

    def update_calendar_visible_equipment(
        self, user_id: int, visible_equipment: List[int], config_key: str = "default"
    ) -> bool:
        """Обновить только видимость станков"""
        try:
            import json
            from models import CalendarConfig

            with self.get_session() as session:
                config = (
                    session.query(CalendarConfig)
                    .filter(
                        CalendarConfig.user_id == user_id,
                        CalendarConfig.config_key == config_key,
                    )
                    .first()
                )

                if config:
                    config.visible_equipment = json.dumps(visible_equipment)
                else:
                    config = CalendarConfig(
                        user_id=user_id,
                        config_key=config_key,
                        visible_equipment=json.dumps(visible_equipment),
                        equipment_order=json.dumps([]),
                        panel_visible=True,
                    )
                    session.add(config)

                session.commit()
                return True
        except Exception as e:
            logger.error(f"Update calendar visible equipment error: {e}")
            return False

    def update_calendar_equipment_order(
        self, user_id: int, equipment_order: List[int], config_key: str = "default"
    ) -> bool:
        """Обновить только порядок станков"""
        try:
            import json
            from models import CalendarConfig

            with self.get_session() as session:
                config = (
                    session.query(CalendarConfig)
                    .filter(
                        CalendarConfig.user_id == user_id,
                        CalendarConfig.config_key == config_key,
                    )
                    .first()
                )

                if config:
                    config.equipment_order = json.dumps(equipment_order)
                else:
                    config = CalendarConfig(
                        user_id=user_id,
                        config_key=config_key,
                        visible_equipment=json.dumps([]),
                        equipment_order=json.dumps(equipment_order),
                        panel_visible=True,
                    )
                    session.add(config)

                session.commit()
                return True
        except Exception as e:
            logger.error(f"Update calendar equipment order error: {e}")
            return False

    def get_all_tables_data(self) -> Dict[str, List[Dict]]:
        """
        Получить данные из всех таблиц БД.
        Использует raw SQL (SELECT *) вместо ORM-моделей, чтобы
        избежать ошибок при несоответствии моделей реальной схеме БД.
        Каждая таблица читается в отдельной транзакции.

        Returns:
            Dict[str, List[Dict]]: {table_name: [list_of_row_dicts]}
        """
        from models import Base

        result = {}
        for table in Base.metadata.sorted_tables:
            try:
                with self.get_session() as session:
                    query = text(f'SELECT * FROM "{table.name}"')
                    db_result = session.execute(query)
                    columns = list(db_result.keys())
                    rows = db_result.fetchall()

                    table_data = []
                    for row in rows:
                        row_dict = {}
                        for col_name in columns:
                            val = dict(zip(columns, row))[col_name]
                            if hasattr(val, "isoformat"):
                                val = val.isoformat()
                            elif isinstance(val, bytes):
                                val = val.decode("utf-8", errors="replace")
                            row_dict[col_name] = val
                        table_data.append(row_dict)

                    result[table.name] = table_data
                    logger.info(f"Exported {len(table_data)} rows from {table.name}")
            except Exception as e:
                logger.warning(f"Could not export table {table.name}: {e}")
                result[table.name] = []

        return result

    def toggle_route_approve(self, route_id: int, approved: bool) -> bool:
        """Утвердить или отозвать маршрут"""
        try:
            with self.get_session() as session:
                session.execute(
                    text(
                        "UPDATE detail_routes SET approved = :approved WHERE id = :id"
                    ),
                    {"approved": approved, "id": route_id},
                )
                session.commit()
                return True
        except Exception as e:
            logger.error(f"Toggle route approve error: {e}")
            return False

    def copy_route_with_operations(self, route_id: int, created_by: str = None) -> dict:
        """Копирование маршрута с увеличением версии"""
        try:
            with self.get_session() as session:
                # Получаем исходный маршрут
                result = session.execute(
                    text("SELECT * FROM detail_routes WHERE id = :id"),
                    {"id": route_id},
                )
                route = result.fetchone()
                if not route:
                    return None

                route_dict = dict(route._mapping)

                # Увеличиваем версию
                current_version = route_dict.get("version") or "1.0"
                try:
                    # Пробуем увеличить как float (1.0 -> 2.0, 1.5 -> 2.5)
                    version_float = float(current_version)
                    new_version = str(int(version_float) + 1)
                except (ValueError, TypeError):
                    new_version = "2.0"

                # Создаём копию маршрута
                insert_result = session.execute(
                    text("""
                    INSERT INTO detail_routes (
                        app_id, lotzman_id, detail_id, detail_name, designation, version, is_actual,
                        material_instance_id, pdf_file, pdf_path, pdf_data,
                        created_by, quantity, preprocessing_data, approved, status,
                        dimension1, dimension2, parts_per_blank, waste_percent, preprocessing,
                        primitive_form_id, prim_dim1, prim_dim2, prim_dim3, lot_size, file, change_indicator,
                        volume, calculated_mass, blank_cost, manual_mass_input, material_cost,
                        unit_cost, labor_cost, depreciation_cost, utility_cost,
                        dimensions, preprocessing_dimensions
                    ) VALUES (
                        :app_id, :lotzman_id, :detail_id, :detail_name, :designation, :version, true,
                        :material_instance_id, :pdf_file, :pdf_path, :pdf_data,
                        :created_by, :quantity, :preprocessing_data, false, 'active',
                        :dimension1, :dimension2, :parts_per_blank, :waste_percent, :preprocessing,
                        :primitive_form_id, :prim_dim1, :prim_dim2, :prim_dim3, :lot_size, :file, false,
                        :volume, :calculated_mass, :blank_cost, :manual_mass_input, :material_cost,
                        :unit_cost, :labor_cost, :depreciation_cost, :utility_cost,
                        :dimensions, :preprocessing_dimensions
                    ) RETURNING id
                    """),
                    {
                        "app_id": route_dict.get("app_id"),
                        "lotzman_id": route_dict.get("lotzman_id"),
                        "detail_id": route_dict.get("detail_id"),
                        "detail_name": route_dict.get("detail_name"),
                        "designation": route_dict.get("designation"),
                        "version": new_version,
                        "material_instance_id": route_dict.get("material_instance_id"),
                        "pdf_file": route_dict.get("pdf_file"),
                        "pdf_path": route_dict.get("pdf_path"),
                        "pdf_data": route_dict.get("pdf_data"),
                        "created_by": created_by,
                        "quantity": route_dict.get("quantity", 1),
                        "preprocessing_data": route_dict.get("preprocessing_data"),
                        "dimension1": route_dict.get("dimension1"),
                        "dimension2": route_dict.get("dimension2"),
                        "parts_per_blank": route_dict.get("parts_per_blank"),
                        "waste_percent": route_dict.get("waste_percent"),
                        "preprocessing": route_dict.get("preprocessing"),
                        "primitive_form_id": route_dict.get("primitive_form_id"),
                        "prim_dim1": route_dict.get("prim_dim1"),
                        "prim_dim2": route_dict.get("prim_dim2"),
                        "prim_dim3": route_dict.get("prim_dim3"),
                        "lot_size": route_dict.get("lot_size"),
                        "file": route_dict.get("file"),
                        "volume": route_dict.get("volume"),
                        "calculated_mass": route_dict.get("calculated_mass"),
                        "blank_cost": route_dict.get("blank_cost"),
                        "manual_mass_input": route_dict.get("manual_mass_input"),
                        "material_cost": route_dict.get("material_cost"),
                        "unit_cost": route_dict.get("unit_cost"),
                        "labor_cost": route_dict.get("labor_cost"),
                        "depreciation_cost": route_dict.get("depreciation_cost"),
                        "utility_cost": route_dict.get("utility_cost"),
                        "dimensions": route_dict.get("dimensions"),
                        "preprocessing_dimensions": route_dict.get(
                            "preprocessing_dimensions"
                        ),
                    },
                )
                new_route_id = insert_result.scalar()
                session.commit()

                # Копируем операции
                ops_result = session.execute(
                    text("SELECT * FROM route_operations WHERE route_id = :route_id"),
                    {"route_id": route_id},
                )
                operations = ops_result.fetchall()

                for op in operations:
                    op_dict = dict(op._mapping)
                    session.execute(
                        text("""
                        INSERT INTO route_operations (
                            route_id, app_id, operation_type_id, equipment_id, sequence_number,
                            duration_minutes, prep_time, control_time, parts_count, is_cooperation,
                            coop_company_id, workshop_id, workshop_area_id, equipment_instance_id,
                            fixture_id, cost_logistics, cost_operation, notes
                        ) VALUES (
                            :route_id, :app_id, :operation_type_id, :equipment_id, :sequence_number,
                            :duration_minutes, :prep_time, :control_time, :parts_count, :is_cooperation,
                            :coop_company_id, :workshop_id, :workshop_area_id, :equipment_instance_id,
                            :fixture_id, :cost_logistics, :cost_operation, :notes
                        )
                        """),
                        {
                            "route_id": new_route_id,
                            "app_id": op_dict.get("app_id"),
                            "operation_type_id": op_dict.get("operation_type_id"),
                            "equipment_id": op_dict.get("equipment_id"),
                            "sequence_number": op_dict.get("sequence_number"),
                            "duration_minutes": op_dict.get("duration_minutes"),
                            "prep_time": op_dict.get("prep_time", 0),
                            "control_time": op_dict.get("control_time", 0),
                            "parts_count": op_dict.get("parts_count", 1),
                            "is_cooperation": op_dict.get("is_cooperation", False),
                            "coop_company_id": op_dict.get("coop_company_id"),
                            "workshop_id": op_dict.get("workshop_id"),
                            "workshop_area_id": op_dict.get("workshop_area_id"),
                            "equipment_instance_id": op_dict.get(
                                "equipment_instance_id"
                            ),
                            "fixture_id": op_dict.get("fixture_id"),
                            "cost_logistics": op_dict.get("cost_logistics"),
                            "cost_operation": op_dict.get("cost_operation"),
                            "notes": op_dict.get("notes"),
                        },
                    )

                session.commit()
                return {"id": new_route_id, "version": new_version, "success": True}
        except Exception as e:
            logger.error(f"Copy route error: {e}")
            return None

    def create_order_from_route(
        self,
        route_id: int,
        quantity: int,
        blanks_needed: int,
        route_quantity: int = None,
        created_by: str = None,
        production_type: str = "piece",
    ) -> dict:
        """Создание заказа из маршрута"""
        try:
            batch_number = self.get_next_batch_number(production_type)

            with self.get_session() as session:
                route = session.execute(
                    text(
                        "SELECT designation, detail_name FROM detail_routes WHERE id = :id"
                    ),
                    {"id": route_id},
                ).fetchone()

                result = session.execute(
                    text("""
                    INSERT INTO orders (
                        route_id, quantity, blanks_needed, route_quantity, created_by,
                        production_type, batch_number, designation, detail_name
                    ) VALUES (
                        :route_id, :quantity, :blanks_needed, :route_quantity, :created_by,
                        :production_type, :batch_number, :designation, :detail_name
                    ) RETURNING id
                    """),
                    {
                        "route_id": route_id,
                        "quantity": quantity,
                        "blanks_needed": blanks_needed,
                        "route_quantity": route_quantity,
                        "created_by": created_by,
                        "production_type": production_type,
                        "batch_number": batch_number,
                        "designation": route[0] if route else None,
                        "detail_name": route[1] if route else None,
                    },
                )
                row = result.fetchone()
                session.commit()
                return (
                    {"id": row.id, "batch_number": batch_number, "success": True}
                    if row
                    else None
                )
        except Exception as e:
            logger.error(f"Create order from route error: {e}")
            return None
