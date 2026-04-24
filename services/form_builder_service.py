"""
Визуальный конструктор форм - как в AppSheet
"""
from enum import Enum
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime


class FieldType(Enum):
    TEXT = "text"
    NUMBER = "number"
    EMAIL = "email"
    PHONE = "phone"
    DATE = "date"
    DATETIME = "datetime"
    DROPDOWN = "dropdown"
    MULTISELECT = "multiselect"
    CHECKBOX = "checkbox"
    SWITCH = "switch"
    TEXTAREA = "textarea"
    FILE = "file"
    IMAGE = "image"
    BARCODE = "barcode"
    SIGNATURE = "signature"
    TABLE = "table"
    REF = "ref"


class ValidationType(Enum):
    REQUIRED = "required"
    MIN_LENGTH = "min_length"
    MAX_LENGTH = "max_length"
    MIN_VALUE = "min_value"
    MAX_VALUE = "max_value"
    PATTERN = "pattern"
    EMAIL_FORMAT = "email_format"
    PHONE_FORMAT = "phone_format"


@dataclass
class ValidationRule:
    type: ValidationType
    value: Any = None
    message: str = ""


@dataclass
class ConditionalRule:
    field: str
    operator: str
    value: Any
    action: str


@dataclass
class FormField:
    id: str
    type: FieldType
    label: str
    key: str
    placeholder: str = ""
    default_value: Any = None
    required: bool = False
    readonly: bool = False
    visible: bool = True
    width: int = 100
    options: List[Dict[str, str]] = field(default_factory=list)
    validations: List[ValidationRule] = field(default_factory=list)
    conditions: List[ConditionalRule] = field(default_factory=list)
    ref_table: str = ""
    ref_display: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FormSection:
    id: str
    title: str
    fields: List[FormField] = field(default_factory=list)
    visible: bool = True
    collapsible: bool = False


@dataclass
class FormLayout:
    name: str
    id: Optional[int] = None
    description: str = ""
    table_name: str = ""
    sections: List[FormSection] = field(default_factory=list)
    actions: List[Dict[str, Any]] = field(default_factory=list)
    permissions: Dict[str, bool] = field(default_factory=lambda: {"create": True, "read": True, "update": True, "delete": True})
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


FIELD_TYPE_LABELS = {
    FieldType.TEXT: "Текст",
    FieldType.NUMBER: "Число",
    FieldType.EMAIL: "Email",
    FieldType.PHONE: "Телефон",
    FieldType.DATE: "Дата",
    FieldType.DATETIME: "Дата и время",
    FieldType.DROPDOWN: "Выбор из списка",
    FieldType.MULTISELECT: "Множественный выбор",
    FieldType.CHECKBOX: "Флажок",
    FieldType.SWITCH: "Переключатель",
    FieldType.TEXTAREA: "Многострочный текст",
    FieldType.FILE: "Файл",
    FieldType.IMAGE: "Изображение",
    FieldType.BARCODE: "Штрихкод",
    FieldType.SIGNATURE: "Подпись",
    FieldType.TABLE: "Таблица",
    FieldType.REF: "Ссылка",
}


class FormBuilderService:
    """Сервис для создания и управления формами"""
    
    def __init__(self, db=None):
        self.db = db
        self._forms: Dict[str, FormLayout] = {}
        self._field_validators: Dict[FieldType, Callable] = {
            FieldType.EMAIL: self._validate_email,
            FieldType.PHONE: self._validate_phone,
            FieldType.NUMBER: self._validate_number,
        }
    
    def register_form(self, form: FormLayout):
        """Регистрация формы"""
        self._forms[form.name] = form
    
    def get_form(self, name: str) -> Optional[FormLayout]:
        """Получение формы по имени"""
        return self._forms.get(name)
    
    def get_all_forms(self) -> List[FormLayout]:
        """Получение всех форм"""
        return list(self._forms.values())
    
    def create_field(
        self,
        field_id: str,
        field_type: FieldType,
        label: str,
        key: str,
        **kwargs
    ) -> FormField:
        """Создание поля формы"""
        return FormField(
            id=field_id,
            type=field_type,
            label=label,
            key=key,
            **kwargs
        )
    
    def add_validation(self, field: FormField, validation_type: ValidationType, value: Any = None, message: str = ""):
        """Добавление валидации к полю"""
        field.validations.append(ValidationRule(
            type=validation_type,
            value=value,
            message=message or self._get_default_message(validation_type, value)
        ))
    
    def add_condition(
        self,
        field: FormField,
        condition_field: str,
        operator: str,
        value: Any,
        action: str = "show"
    ):
        """Добавление условия видимости/доступности поля"""
        field.conditions.append(ConditionalRule(
            field=condition_field,
            operator=operator,
            value=value,
            action=action
        ))
    
    def validate_field(self, field: FormField, value: Any) -> Dict[str, Any]:
        """Валидация поля"""
        errors = []
        
        for validation in field.validations:
            validator = self._field_validators.get(field.type)
            if validator:
                error = validator(field, value, validation)
                if error:
                    errors.append(error)
        
        return {"valid": len(errors) == 0, "errors": errors}
    
    def validate_form(self, form: FormLayout, values: Dict[str, Any]) -> Dict[str, Any]:
        """Валидация всей формы"""
        all_errors = {}
        
        for section in form.sections:
            for field in section.fields:
                if field.visible and not field.readonly:
                    value = values.get(field.key)
                    result = self.validate_field(field, value)
                    if not result["valid"]:
                        all_errors[field.key] = result["errors"]
        
        return {"valid": len(all_errors) == 0, "errors": all_errors}
    
    def evaluate_conditions(self, form: FormLayout, values: Dict[str, Any]) -> Dict[str, bool]:
        """Вычисление видимости полей на основе условий"""
        visibility = {}

        for section in form.sections:
            for field in section.fields:
                visible = True
                for condition in field.conditions:
                    field_value = values.get(condition.field)
                    condition_met = self._check_condition(condition.operator, field_value, condition.value)
                    if condition.action == "show":
                        visible = visible and condition_met
                    elif condition.action == "hide":
                        visible = visible and not condition_met
                visibility[field.id] = visible
        
        return visibility
    
    def _check_condition(self, operator: str, value: Any, condition_value: Any) -> bool:
        """Проверка условия"""
        operators = {
            "eq": lambda v, c: v == c,
            "neq": lambda v, c: v != c,
            "gt": lambda v, c: v > c,
            "gte": lambda v, c: v >= c,
            "lt": lambda v, c: v < c,
            "lte": lambda v, c: v <= c,
            "contains": lambda v, c: c in (v or ""),
            "startswith": lambda v, c: (v or "").startswith(c),
            "endswith": lambda v, c: (v or "").endswith(c),
            "isempty": lambda v, c: not v,
            "isnotempty": lambda v, c: bool(v),
        }
        return operators.get(operator, lambda v, c: False)(value, condition_value)
    
    def _validate_email(self, field: FormField, value: Any, validation: ValidationRule) -> Optional[str]:
        if value and "@" not in str(value):
            return validation.message or "Некорректный email"
        return None
    
    def _validate_phone(self, field: FormField, value: Any, validation: ValidationRule) -> Optional[str]:
        if value and len(str(value)) < 10:
            return validation.message or "Некорректный номер телефона"
        return None
    
    def _validate_number(self, field: FormField, value: Any, validation: ValidationRule) -> Optional[str]:
        try:
            num = float(value) if value else 0
            if validation.type == ValidationType.MIN_VALUE and num < validation.value:
                return validation.message or f"Минимальное значение: {validation.value}"
            if validation.type == ValidationType.MAX_VALUE and num > validation.value:
                return validation.message or f"Максимальное значение: {validation.value}"
        except:
            return "Должно быть числом"
        return None
    
    def _get_default_message(self, validation_type: ValidationType, value: Any) -> str:
        messages = {
            ValidationType.REQUIRED: "Обязательное поле",
            ValidationType.MIN_LENGTH: f"Минимум {value} символов",
            ValidationType.MAX_LENGTH: f"Максимум {value} символов",
            ValidationType.MIN_VALUE: f"Минимум {value}",
            ValidationType.MAX_VALUE: f"Максимум {value}",
            ValidationType.PATTERN: "Неверный формат",
            ValidationType.EMAIL_FORMAT: "Некорректный email",
            ValidationType.PHONE_FORMAT: "Некорректный телефон",
        }
        return messages.get(validation_type, "Неверное значение")


def create_inventory_form() -> FormLayout:
    """Создание формы для склада"""
    form = FormLayout(
        name="inventory_form",
        description="Форма управления складом",
        table_name="items"
    )
    
    section1 = FormSection(id="main", title="Основные данные")
    
    field1 = FormField(
        id="item_id",
        type=FieldType.TEXT,
        label="ID",
        key="item_id",
        required=True,
        readonly=True
    )
    section1.fields.append(field1)
    
    field2 = FormField(
        id="name",
        type=FieldType.TEXT,
        label="Наименование",
        key="name",
        required=True,
        placeholder="Введите наименование"
    )
    section2 = FormBuilderService()
    section2.add_validation(field2, ValidationType.REQUIRED)
    section2.add_validation(field2, ValidationType.MIN_LENGTH, 2)
    section1.fields.append(field2)
    
    field3 = FormField(
        id="quantity",
        type=FieldType.NUMBER,
        label="Количество",
        key="quantity",
        required=True,
        default_value=0
    )
    section2.add_validation(field3, ValidationType.REQUIRED)
    section2.add_validation(field3, ValidationType.MIN_VALUE, 0)
    section1.fields.append(field3)
    
    field4 = FormField(
        id="min_stock",
        type=FieldType.NUMBER,
        label="Минимальный остаток",
        key="min_stock",
        default_value=1
    )
    section2.add_validation(field4, ValidationType.MIN_VALUE, 0)
    section1.fields.append(field4)
    
    field5 = FormField(
        id="category",
        type=FieldType.DROPDOWN,
        label="Категория",
        key="category",
        options=[
            {"key": "tools", "value": "Инструменты"},
            {"key": "materials", "value": "Материалы"},
            {"key": "consumables", "value": "Расходники"},
        ]
    )
    section1.fields.append(field5)
    
    field6 = FormField(
        id="location",
        type=FieldType.TEXT,
        label="Местоположение",
        key="location",
        placeholder="Стеллаж, полка"
    )
    section1.fields.append(field6)
    
    form.sections.append(section1)
    
    return form
