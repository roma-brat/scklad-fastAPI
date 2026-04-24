# models.py
"""
SQLAlchemy модели данных
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Boolean,
    Text,
    Float,
)
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime
import bcrypt

Base = declarative_base()


class User(Base):
    """Модель пользователя"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    login = Column(String(50), unique=True, nullable=False, index=True)
    username = Column(String(100), nullable=False)  # Отображаемое имя (Фамилия Имя)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="user", server_default="user")
    workstation = Column(String(100))
    workstations = Column(String(500))
    screen_permissions = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, server_default="true")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    transactions = relationship(
        "Transaction", back_populates="user", cascade="all, delete-orphan"
    )
    inventory_changes = relationship(
        "InventoryChange", back_populates="user", cascade="all, delete-orphan"
    )
    audit_logs = relationship(
        "AuditLog", back_populates="user", cascade="all, delete-orphan"
    )
    details = relationship(
        "Detail", back_populates="creator", cascade="all, delete-orphan"
    )

    def set_password(self, password: str):
        """Хэширование пароля с bcrypt"""
        salt = bcrypt.gensalt(rounds=12)
        self.password_hash = bcrypt.hashpw(password.encode("utf-8"), salt).decode(
            "utf-8"
        )

    def check_password(self, password: str) -> bool:
        """Проверка пароля"""
        return bcrypt.checkpw(
            password.encode("utf-8"), self.password_hash.encode("utf-8")
        )

    def to_dict(self):
        return {
            "id": self.id,
            "login": self.login,
            "username": self.username,
            "role": self.role,
            "workstation": self.workstation,
            "workstations": self.workstations,
            "is_active": self.is_active,
            "screen_permissions": self.screen_permissions,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<User {self.username} (role={self.role})>"


class Item(Base):
    """Модель товара/инструмента"""

    __tablename__ = "items"

    id = Column(Integer, primary_key=True)
    item_id = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    quantity = Column(Integer, nullable=False, default=0)
    min_stock = Column(Integer, nullable=False, default=1)
    category = Column(String(100))
    location = Column(String(100))
    image_url = Column(String(500))
    shop_url = Column(String(500))
    specifications = Column(Text)  # JSON string for item specifications
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    transactions = relationship(
        "Transaction", back_populates="item", cascade="all, delete-orphan"
    )
    inventory_changes = relationship(
        "InventoryChange", back_populates="item", cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "item_id": self.item_id,
            "name": self.name,
            "quantity": self.quantity,
            "min_stock": self.min_stock,
            "category": self.category,
            "location": self.location,
            "image_url": self.image_url,
            "shop_url": self.shop_url,
            "specifications": self.specifications,
            "low_stock": self.quantity <= self.min_stock,
        }

    def __repr__(self):
        return f"<Item {self.name} (ID={self.item_id}, qty={self.quantity})>"


class Workshop(Base):
    """Модель цеха"""

    __tablename__ = "workshops"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(String(255))
    is_active = Column(Boolean, default=True, server_default="true")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<Workshop {self.name}>"


class Material(Base):
    """Модель марки материала (Марка)"""

    __tablename__ = "materials"

    id = Column(Integer, primary_key=True)
    app_id = Column(String(50), unique=True, index=True)
    lotzman_id = Column(String(50), index=True)
    name = Column(String(100), nullable=False, index=True)
    density = Column(Float)  # Удельный вес, тн/м³
    description = Column(String(255))
    unit = Column(String(20), default="шт")
    is_active = Column(Boolean, default=True, server_default="true")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "app_id": self.app_id,
            "lotzman_id": self.lotzman_id,
            "name": self.name,
            "density": self.density,
            "description": self.description,
            "unit": self.unit,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<Material {self.name}>"


class OperationType(Base):
    """Модель типа операции"""

    __tablename__ = "operation_types"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(String(255))
    default_duration = Column(Integer, default=60)  # длительность в минутах
    is_active = Column(Boolean, default=True, server_default="true")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "default_duration": self.default_duration,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<OperationType {self.name}>"


class Transaction(Base):
    """Модель транзакции (приход/расход)"""

    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), index=True)
    item_id = Column(Integer, ForeignKey("items.id", ondelete="CASCADE"), index=True)
    quantity = Column(Integer, nullable=False)
    operation_type = Column(String(20), nullable=False, server_default="income")
    detail = Column(String(255))
    reason = Column(String(255))
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    user = relationship("User", back_populates="transactions")
    item = relationship("Item", back_populates="transactions")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "item_id": self.item_id,
            "quantity": self.quantity,
            "operation_type": self.operation_type,
            "detail": self.detail,
            "reason": self.reason,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }

    def __repr__(self):
        return f"<Transaction {self.operation_type} item={self.item_id} qty={self.quantity}>"


class InventoryChange(Base):
    """Модель изменения остатков"""

    __tablename__ = "inventory_changes"

    id = Column(Integer, primary_key=True)
    item_id = Column(Integer, ForeignKey("items.id", ondelete="CASCADE"), index=True)
    old_quantity = Column(Integer, nullable=False)
    new_quantity = Column(Integer, nullable=False)
    changed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    item = relationship("Item", back_populates="inventory_changes")
    user = relationship("User", back_populates="inventory_changes")

    def to_dict(self):
        return {
            "id": self.id,
            "item_id": self.item_id,
            "old_quantity": self.old_quantity,
            "new_quantity": self.new_quantity,
            "changed_by": self.changed_by,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }

    def __repr__(self):
        return f"<InventoryChange item={self.item_id} {self.old_quantity}->{self.new_quantity}>"


class AuditLog(Base):
    """Модель аудита действий"""

    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), index=True)
    action = Column(String(100), nullable=False, index=True)
    entity_type = Column(String(50))
    entity_id = Column(Integer)
    old_values = Column(Text)  # JSON строка
    new_values = Column(Text)  # JSON строка
    ip_address = Column(String(45))
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    user = relationship("User", back_populates="audit_logs")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "action": self.action,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }

    def __repr__(self):
        return f"<AuditLog {self.action} by user={self.user_id}>"


class Geometry(Base):
    """Модель геометрии"""

    __tablename__ = "geometry"

    id = Column(Integer, primary_key=True)
    app_id = Column(String(50), unique=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    primitive = Column(Boolean, default=False)
    prefix = Column(String(20))
    unit = Column(String(20))
    dimension1 = Column(String(50))
    dimension2 = Column(String(50))
    dimension3 = Column(String(50))
    for_volume = Column(Boolean)
    sketch = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "app_id": self.app_id,
            "name": self.name,
            "primitive": self.primitive,
            "prefix": self.prefix,
            "unit": self.unit,
            "dimension1": self.dimension1,
            "dimension2": self.dimension2,
            "dimension3": self.dimension3,
            "for_volume": self.for_volume,
            "sketch": self.sketch,
        }


class Sortament(Base):
    """Модель сортамента"""

    __tablename__ = "sortament"

    id = Column(Integer, primary_key=True)
    app_id = Column(String(50), unique=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    gost = Column(String(100))
    geometry_id = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "app_id": self.app_id,
            "name": self.name,
            "gost": self.gost,
            "geometry_id": self.geometry_id,
        }


class Equipment(Base):
    """Модель оборудования"""

    __tablename__ = "equipment"

    id = Column(Integer, primary_key=True)
    app_id = Column(String(50), unique=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    inventory_number = Column(String(50))
    is_universal = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True, server_default="true")
    has_workshop_inventory = Column(Boolean, default=False, server_default="false")
    default_working_hours = Column(Integer, default=7)
    operation_types = Column(String(500))
    wage_with_taxes = Column(Float)
    multi_operational = Column(Integer)
    power = Column(Float)
    cost = Column(Float)
    spi = Column(Float)
    tool_cost = Column(Float)
    tooling_cost = Column(Float)
    maintenance_cost = Column(Float)
    setup_cost = Column(Float)
    operator_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "app_id": self.app_id,
            "name": self.name,
            "inventory_number": self.inventory_number,
            "is_universal": self.is_universal,
            "is_active": self.is_active,
            "has_workshop_inventory": self.has_workshop_inventory,
            "default_working_hours": self.default_working_hours,
            "operation_types": self.operation_types,
            "power": self.power,
            "cost": self.cost,
        }


class MaterialInstance(Base):
    """Модель экземпляра сортамента (конкретный материал с размерами)"""

    __tablename__ = "material_instances"

    id = Column(Integer, primary_key=True)
    app_id = Column(String(50), unique=True, index=True)
    lotzman_id = Column(String(50), index=True)
    mark_id = Column(String(50), index=True)
    mark_name = Column(String(100))
    mark_gost = Column(String(100))
    sortament_id = Column(String(50), index=True)
    sortament_name = Column(String(100))
    sortament_gost = Column(String(100))
    dimension1 = Column(Float)
    dimension2 = Column(Float)
    dimension3 = Column(Float)
    price_per_ton = Column(Float)  # Цена за тонну, руб без НДС
    price_per_piece = Column(Float)  # Цена за штуку, руб без НДС
    # Дополнительные поля для расчетов
    volume_argument = Column(String(10))  # Аргумент для объема: V, S, L
    volume_value = Column(Float)  # Значение аргумента для объема
    price_per_kg = Column(Float)  # Цена за кг
    type_size = Column(String(100))  # Типоразмер
    dimensions = Column(String(200))  # Размеры (текстовое поле)
    created_by = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "app_id": self.app_id,
            "lotzman_id": self.lotzman_id,
            "mark_id": self.mark_id,
            "mark_name": self.mark_name,
            "mark_gost": self.mark_gost,
            "sortament_id": self.sortament_id,
            "sortament_name": self.sortament_name,
            "sortament_gost": self.sortament_gost,
            "dimension1": self.dimension1,
            "dimension2": self.dimension2,
            "dimension3": self.dimension3,
            "price_per_ton": self.price_per_ton,
            "price_per_piece": self.price_per_piece,
            "volume_argument": self.volume_argument,
            "volume_value": self.volume_value,
            "price_per_kg": self.price_per_kg,
            "type_size": self.type_size,
            "dimensions": self.dimensions,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class WorkshopInventory(Base):
    """Модель инвентаря на складе станка"""

    __tablename__ = "workshop_inventory"

    id = Column(Integer, primary_key=True)
    equipment_id = Column(
        Integer, ForeignKey("equipment.id"), nullable=False, index=True
    )
    item_id = Column(Integer, ForeignKey("items.id", ondelete="CASCADE"), index=True)
    quantity = Column(Integer, nullable=False, default=1)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    equipment = relationship("Equipment", backref="workshop_inventory")
    item = relationship("Item", backref="workshop_inventory")

    def to_dict(self):
        return {
            "id": self.id,
            "equipment_id": self.equipment_id,
            "equipment_name": self.equipment.name if self.equipment else None,
            "item_id": self.item_id,
            "item_name": self.item.name if self.item else None,
            "item_code": self.item.item_id if self.item else None,
            "quantity": self.quantity,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class UserItems(Base):
    """Модель инструментов на руках у пользователей"""

    __tablename__ = "user_items"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    item_id = Column(Integer, ForeignKey("items.id", ondelete="CASCADE"), index=True)
    quantity = Column(Integer, nullable=False, default=1)
    taken_at = Column(DateTime, default=datetime.utcnow)

    item = relationship("Item", backref="user_items")
    user = relationship("User", backref="user_items")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "user_name": self.user.username if self.user else None,
            "item_id": self.item_id,
            "item_name": self.item.name if self.item else None,
            "item_code": self.item.item_id if self.item else None,
            "quantity": self.quantity,
            "taken_at": self.taken_at.isoformat() if self.taken_at else None,
        }


class Detail(Base):
    """Модель детали (ДСЕ)"""

    __tablename__ = "details"

    id = Column(Integer, primary_key=True)
    detail_id = Column(String(50), unique=True, nullable=False, index=True)
    lotzman_id = Column(String(50), index=True)
    detail_type = Column(String(50))
    designation = Column(String(100), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    version = Column(Float, default=1.0)
    is_actual = Column(Boolean, default=True)
    drawing = Column(String(500))
    correct_designation = Column(Boolean, default=True)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    creator = relationship("User", back_populates="details")

    def to_dict(self):
        return {
            "id": self.id,
            "detail_id": self.detail_id,
            "lotzman_id": self.lotzman_id,
            "detail_type": self.detail_type,
            "designation": self.designation,
            "name": self.name,
            "version": self.version,
            "is_actual": self.is_actual,
            "drawing": self.drawing,
            "correct_designation": self.correct_designation,
            "creator_id": self.creator_id,
            "creator_name": self.creator.username if self.creator else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class DetailRoute(Base):
    """Модель маршрута обработки детали"""

    __tablename__ = "detail_routes"

    id = Column(Integer, primary_key=True)
    app_id = Column(String(50), unique=True, index=True)
    lotzman_id = Column(String(50), index=True)
    designation = Column(String(100))  # Обозначение (из ДСЕ + " МЕХ")
    name = Column(String(255))  # Наименование
    version = Column(String(20), default="0.0")  # Версия
    is_actual = Column(Boolean, default=True)  # Актуальная
    detail_id = Column(Integer, ForeignKey("details.id"))  # Ссылка на ДСЕ
    material_instance_id = Column(
        Integer, ForeignKey("material_instances.id")
    )  # Экземпляр сортамента

    # Размеры детали
    dimension1 = Column(Float)  # Размер1
    dimension2 = Column(Float)  # Размер2
    parts_per_blank = Column(Integer, default=1)  # Деталей в заготовке
    waste_percent = Column(Float, default=0)  # Возвратные отходы (%)
    preprocessing = Column(Boolean, default=False)  # Предварительная обработка

    # Форма примитива (для предобработки)
    primitive_form_id = Column(String(50))  # Ссылка на Geometry
    prim_dim1 = Column(Float)  # РазмПрим1
    prim_dim2 = Column(Float)  # РазмПрим2
    prim_dim3 = Column(Float)  # РазмПрим3

    lot_size = Column(Integer, default=1)  # Величина партии

    # Файлы
    file = Column(String(500))  # Файл маршрута
    change_indicator = Column(Boolean, default=False)  # Изменение

    # Расчетные поля
    volume = Column(Float)  # Объем
    calculated_mass = Column(Float)  # Масса расчетная
    blank_cost = Column(Float)  # Стоимость заготовки
    manual_mass_input = Column(Boolean, default=False)  # Ручной ввод массы
    material_cost = Column(Float)  # Затраты на материал

    # Себестоимость
    unit_cost = Column(Float)  # Себестоимость одного изделия
    labor_cost = Column(Float)  # Затраты на ЗП
    depreciation_cost = Column(Float)  # Затраты на Аморт
    utility_cost = Column(Float)  # Затраты на ЭЭ и обслуживание

    # Габариты
    dimensions = Column(String(100))  # Габариты (текст)
    preprocessing_dimensions = Column(String(200))  # ПредвОбработкаГабариты

    pdf_file = Column(String(500))
    pdf_path = Column(String(500))
    pdf_data = Column(Text)
    created_by = Column(String(100))
    quantity = Column(Integer, default=1)
    status = Column(String(50), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    detail = relationship("Detail", backref="routes")
    material_instance = relationship("MaterialInstance", backref="routes")

    def to_dict(self):
        return {
            "id": self.id,
            "app_id": self.app_id,
            "lotzman_id": self.lotzman_id,
            "designation": self.designation,
            "name": self.name,
            "version": self.version,
            "is_actual": self.is_actual,
            "detail_id": self.detail_id,
            "material_instance_id": self.material_instance_id,
            "dimension1": self.dimension1,
            "dimension2": self.dimension2,
            "parts_per_blank": self.parts_per_blank,
            "waste_percent": self.waste_percent,
            "preprocessing": self.preprocessing,
            "primitive_form_id": self.primitive_form_id,
            "prim_dim1": self.prim_dim1,
            "prim_dim2": self.prim_dim2,
            "prim_dim3": self.prim_dim3,
            "lot_size": self.lot_size,
            "file": self.file,
            "change_indicator": self.change_indicator,
            "volume": self.volume,
            "calculated_mass": self.calculated_mass,
            "blank_cost": self.blank_cost,
            "manual_mass_input": self.manual_mass_input,
            "material_cost": self.material_cost,
            "unit_cost": self.unit_cost,
            "labor_cost": self.labor_cost,
            "depreciation_cost": self.depreciation_cost,
            "utility_cost": self.utility_cost,
            "dimensions": self.dimensions,
            "preprocessing_dimensions": self.preprocessing_dimensions,
            "quantity": self.quantity,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class RouteOperation(Base):
    """Модель операции маршрута"""

    __tablename__ = "route_operations"

    id = Column(Integer, primary_key=True)
    app_id = Column(String(50), unique=True, index=True)
    route_id = Column(
        Integer, ForeignKey("detail_routes.id", ondelete="CASCADE"), nullable=False
    )
    operation_type_id = Column(Integer, ForeignKey("operation_types.id"))
    equipment_id = Column(Integer, ForeignKey("equipment.id"))

    # Номер операции
    sequence_number = Column(Integer, nullable=False)

    # Время
    duration_minutes = Column(Integer, default=0)  # Время штучное (Тшт)
    prep_time = Column(Integer, default=0)  # Время подготовительное (Тпз)
    control_time = Column(Integer, default=0)  # Время на контрольные измерения (Тконтр)
    total_time = Column(Integer, default=0)  # Сумма всех трёх времён (для планирования)

    # Количество
    parts_count = Column(Integer, default=1)  # Кол-во деталей за установ

    # Кооперация
    is_cooperation = Column(Boolean, default=False)
    coop_company_id = Column(Integer, ForeignKey("cooperatives.id"))

    # Ссылки на цех и участок
    workshop_id = Column(Integer, ForeignKey("workshops.id"))
    workshop_area_id = Column(Integer)  # ID участка

    # Оборудование (экземпляр)
    equipment_instance_id = Column(String(50))  # ID Экз.оборудования

    # Приспособление
    fixture_id = Column(String(50))  # ID приспособления

    # Стоимость
    cost_logistics = Column(Float)  # Стоимость логистики
    cost_operation = Column(Float)  # Стоимость операции

    # Кооперация - дни и позиция
    coop_duration_days = Column(
        Integer, nullable=True
    )  # Количество дней для операции кооперации
    coop_position = Column(
        String(20), nullable=True
    )  # Позиция: 'start', 'end', 'middle'

    # Предыдущая/следующая операция (связь)
    previous_operation_id = Column(String(50))  # ID Предыдущая
    next_operation_id = Column(String(50))  # ID Следующая

    notes = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "app_id": self.app_id,
            "route_id": self.route_id,
            "operation_type_id": self.operation_type_id,
            "equipment_id": self.equipment_id,
            "sequence_number": self.sequence_number,
            "duration_minutes": self.duration_minutes,
            "prep_time": self.prep_time,
            "control_time": self.control_time,
            "total_time": self.total_time,
            "parts_count": self.parts_count,
            "is_cooperation": self.is_cooperation,
            "coop_company_id": self.coop_company_id,
            "coop_duration_days": self.coop_duration_days,
            "coop_position": self.coop_position,
            "workshop_id": self.workshop_id,
            "workshop_area_id": self.workshop_area_id,
            "equipment_instance_id": self.equipment_instance_id,
            "fixture_id": self.fixture_id,
            "cost_logistics": self.cost_logistics,
            "cost_operation": self.cost_operation,
            "previous_operation_id": self.previous_operation_id,
            "next_operation_id": self.next_operation_id,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Cooperative(Base):
    """Модель предприятия кооперации"""

    __tablename__ = "cooperatives"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(String(500))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "is_active": self.is_active,
        }


class Order(Base):
    """Модель заказа/наряда"""

    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    app_id = Column(String(50), unique=True, index=True)
    route_id = Column(
        Integer, ForeignKey("detail_routes.id", ondelete="SET NULL"), nullable=True
    )

    # Данные ЭМК (JSON) - инструменты, история и т.д.
    route_card_data = Column(Text)  # JSON: {tools: [...], history: [...]}

    # Поля из Excel
    id_1c = Column(String(50))  # ID 1С
    order_number = Column(Integer)  # Номер заказа
    lot_size = Column(Integer)  # Размер партии
    file = Column(String(500))  # Файл
    status = Column(String(50), default="новый")  # Статус: новый, в работе, выполнен
    in_progress = Column(Boolean, default=False)  # В_Процессе

    # Дополнительные поля
    designation = Column(String(100))
    detail_name = Column(String(255))
    mark_name = Column(String(100))
    sortament_name = Column(String(100))
    quantity = Column(Integer, nullable=False)
    blanks_needed = Column(Integer, nullable=False)  # Количество заготовок
    blanks_quantity = Column(Integer)  # Количество заготовок (дубликат)
    blank_size = Column(String(100))  # Размер заготовки
    preprocessing_size = Column(String(200))  # ПредвОбработкаГабариты
    route_quantity = Column(Integer)
    pdf_path = Column(String(500))
    start_date = Column(String(20))
    end_date = Column(String(20))
    created_by = Column(String(100))
    production_type = Column(
        String(20), default="piece"
    )  # 'piece' - штучное, 'batch' - партийное
    batch_number = Column(String(50))  # Номер партии: Ш001, П001

    # Поля для ручных записей (без маршрута)
    manual_detail_name = Column(String(255))  # Название детали вручную
    manual_quantity = Column(Integer)  # Количество вручную

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "app_id": self.app_id,
            "route_id": self.route_id,
            "id_1c": self.id_1c,
            "order_number": self.order_number,
            "lot_size": self.lot_size,
            "file": self.file,
            "status": self.status,
            "in_progress": self.in_progress,
            "designation": self.designation,
            "detail_name": self.detail_name,
            "mark_name": self.mark_name,
            "sortament_name": self.sortament_name,
            "quantity": self.quantity,
            "blanks_needed": self.blanks_needed,
            "blanks_quantity": self.blanks_quantity,
            "blank_size": self.blank_size,
            "preprocessing_size": self.preprocessing_size,
            "route_quantity": self.route_quantity,
            "pdf_path": self.pdf_path,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "created_by": self.created_by,
            "production_type": self.production_type,
            "batch_number": self.batch_number,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class EquipmentCalendar(Base):
    """График работы станков - настройка рабочих дней"""

    __tablename__ = "equipment_calendar"

    id = Column(Integer, primary_key=True)
    equipment_id = Column(
        Integer,
        ForeignKey("equipment.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    date = Column(DateTime, nullable=False, index=True)
    working_hours = Column(Integer, default=7)
    is_working = Column(Boolean, default=True)
    notes = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    equipment = relationship("Equipment", backref="calendar_entries")

    def to_dict(self):
        return {
            "id": self.id,
            "equipment_id": self.equipment_id,
            "equipment_name": self.equipment.name if self.equipment else None,
            "date": self.date.strftime("%Y-%m-%d") if self.date else None,
            "working_hours": self.working_hours,
            "is_working": self.is_working,
            "notes": self.notes,
        }


class ProductionSchedule(Base):
    """Производственный план - основная таблица планирования"""

    __tablename__ = "production_schedule"

    id = Column(Integer, primary_key=True)
    order_id = Column(
        Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    route_operation_id = Column(
        Integer, ForeignKey("route_operations.id", ondelete="CASCADE")
    )
    equipment_id = Column(Integer, ForeignKey("equipment.id", ondelete="SET NULL"))

    planned_date = Column(DateTime, index=True)
    actual_date = Column(DateTime)

    status = Column(String(20), default="planned", index=True)
    priority = Column(Integer, default=5)
    quantity = Column(Integer, default=1)
    duration_minutes = Column(Integer)

    notes = Column(String(500))
    is_manual_override = Column(Boolean, default=False)

    # Отслеживание выполнения
    taken_at = Column(DateTime)  # Когда взяли в работу
    completed_at = Column(DateTime)  # Когда завершили
    taken_by = Column(String(100))  # Кто взял
    completed_by = Column(String(100))  # Кто завершил

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    order = relationship("Order", backref="schedule_items")
    route_operation = relationship("RouteOperation", backref="schedule_items")
    equipment = relationship("Equipment", backref="schedule_items")

    def to_dict(self):
        return {
            "id": self.id,
            "order_id": self.order_id,
            "route_operation_id": self.route_operation_id,
            "equipment_id": self.equipment_id,
            "equipment_name": self.equipment.name if self.equipment else None,
            "planned_date": self.planned_date.strftime("%Y-%m-%d")
            if self.planned_date
            else None,
            "actual_date": self.actual_date.strftime("%Y-%m-%d")
            if self.actual_date
            else None,
            "status": self.status,
            "priority": self.priority,
            "quantity": self.quantity,
            "duration_minutes": self.duration_minutes,
            "notes": self.notes,
            "is_manual_override": self.is_manual_override,
            "taken_at": self.taken_at.isoformat() if self.taken_at else None,
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
            "taken_by": self.taken_by,
            "completed_by": self.completed_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ScheduleEvent(Base):
    """События-флаги для задач производства"""

    __tablename__ = "schedule_events"

    id = Column(Integer, primary_key=True)
    schedule_id = Column(
        Integer,
        ForeignKey("production_schedule.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type = Column(
        String(30), nullable=False
    )  # no_drawing, no_nc_program, first_piece_checked
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String(100))

    schedule = relationship("ProductionSchedule", backref="events")

    def to_dict(self):
        return {
            "id": self.id,
            "schedule_id": self.schedule_id,
            "event_type": self.event_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by": self.created_by,
        }


class OrderPriority(Base):
    """Приоритеты заказов"""

    __tablename__ = "order_priorities"

    id = Column(Integer, primary_key=True)
    order_id = Column(
        Integer,
        ForeignKey("orders.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    priority = Column(Integer, default=5)
    deadline = Column(DateTime)
    notes = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    order = relationship("Order", backref="priority")

    def to_dict(self):
        return {
            "id": self.id,
            "order_id": self.order_id,
            "priority": self.priority,
            "deadline": self.deadline.strftime("%Y-%m-%d") if self.deadline else None,
            "notes": self.notes,
        }


class WorkshopArea(Base):
    """Модель участка (подразделение внутри цеха)"""

    __tablename__ = "workshop_areas"

    id = Column(Integer, primary_key=True)
    app_id = Column(String(50), unique=True, index=True)
    lotzman_id = Column(String(50), index=True)
    workshop_id = Column(Integer, ForeignKey("workshops.id"))  # ID Цеха
    designation = Column(String(50))  # Обозначение
    name = Column(String(100))  # Название
    created_by = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    workshop = relationship("Workshop", backref="areas")

    def to_dict(self):
        return {
            "id": self.id,
            "app_id": self.app_id,
            "lotzman_id": self.lotzman_id,
            "workshop_id": self.workshop_id,
            "designation": self.designation,
            "name": self.name,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class EquipmentInstance(Base):
    """Модель экземпляра оборудования (конкретный станок)"""

    __tablename__ = "equipment_instances"

    id = Column(Integer, primary_key=True)
    app_id = Column(String(50), unique=True, index=True)
    equipment_id = Column(String(50))  # ID Оборудования (ссылка на таблицу equipment)
    lotzman_id = Column(String(50), index=True)
    number = Column(String(50))  # Номер
    operator_id = Column(Integer, ForeignKey("users.id"))  # Оператор
    notes = Column(String(500))  # Примечание
    created_by = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    operator = relationship("User", backref="equipment_instances")

    def to_dict(self):
        return {
            "id": self.id,
            "app_id": self.app_id,
            "equipment_id": self.equipment_id,
            "lotzman_id": self.lotzman_id,
            "number": self.number,
            "operator_id": self.operator_id,
            "operator_name": self.operator.username if self.operator else None,
            "notes": self.notes,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class SystemParameter(Base):
    """Модель системных параметров (Параметры)"""

    __tablename__ = "system_parameters"

    id = Column(Integer, primary_key=True)
    app_id = Column(String(50), unique=True, index=True)
    name = Column(String(100), nullable=False)  # Название параметра
    value = Column(Text)  # Значение
    description = Column(String(255))  # Описание
    param_type = Column(String(50))  # Тип параметра
    created_by = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "app_id": self.app_id,
            "name": self.name,
            "value": self.value,
            "description": self.description,
            "param_type": self.param_type,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Task(Base):
    """Модель задания (Задание) - планирование операций"""

    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True)
    app_id = Column(String(50), unique=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"))  # ID Заказа
    operation_id = Column(String(50))  # ID Операции (ссылка на route_operations)

    # Кооперация
    is_cooperation = Column(Boolean, default=False)
    coop_company_id = Column(Integer, ForeignKey("cooperatives.id"))

    # Цех и участок
    workshop_id = Column(Integer, ForeignKey("workshops.id"))
    workshop_area_id = Column(Integer)  # ID Участка

    # Номер операции
    sequence_number = Column(Integer)

    # Тип операции
    operation_type_id = Column(Integer, ForeignKey("operation_types.id"))

    # Экземпляр оборудования
    equipment_instance_id = Column(String(50))  # ID Экз.оборудования

    # Время
    prep_time = Column(Integer)  # Тпз
    duration_minutes = Column(Integer)  # Тшт
    control_time = Column(Integer)  # Тконтр

    # Количество
    parts_count = Column(Integer, default=1)  # Кол-во одновр. обраб. деталей

    # Комментарий
    notes = Column(String(500))

    # Статус и даты
    status = Column(String(50), default="planned")
    planned_date = Column(DateTime)
    actual_date = Column(DateTime)

    created_by = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    order = relationship("Order", backref="tasks")
    workshop = relationship("Workshop", backref="tasks")
    operation_type = relationship("OperationType", backref="tasks")

    def to_dict(self):
        return {
            "id": self.id,
            "app_id": self.app_id,
            "order_id": self.order_id,
            "operation_id": self.operation_id,
            "is_cooperation": self.is_cooperation,
            "coop_company_id": self.coop_company_id,
            "workshop_id": self.workshop_id,
            "workshop_area_id": self.workshop_area_id,
            "sequence_number": self.sequence_number,
            "operation_type_id": self.operation_type_id,
            "equipment_instance_id": self.equipment_instance_id,
            "prep_time": self.prep_time,
            "duration_minutes": self.duration_minutes,
            "control_time": self.control_time,
            "parts_count": self.parts_count,
            "notes": self.notes,
            "status": self.status,
            "planned_date": self.planned_date.isoformat()
            if self.planned_date
            else None,
            "actual_date": self.actual_date.isoformat() if self.actual_date else None,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class CalendarConfig(Base):
    """Настройки календаря пользователя (видимость и порядок станков)"""

    __tablename__ = "calendar_configs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    config_key = Column(String(50), nullable=False, default="default")
    visible_equipment = Column(Text)  # JSON: список ID видимых станков
    equipment_order = Column(Text)  # JSON: порядок станков
    panel_visible = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        import json

        return {
            "id": self.id,
            "user_id": self.user_id,
            "config_key": self.config_key,
            "visible_equipment": json.loads(self.visible_equipment)
            if self.visible_equipment
            else [],
            "equipment_order": json.loads(self.equipment_order)
            if self.equipment_order
            else [],
            "panel_visible": self.panel_visible,
        }
