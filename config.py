"""
Конфигурация приложения Склад Инструментов
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Database - используем существующую БД sklad_db
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://sklad_user:sklad_pass@localhost:5432/sklad_db"
)

# Application
APP_PORT = int(os.getenv("APP_PORT", "8551"))
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_ENV = os.getenv("APP_ENV", "development")  # development, production

# Security
SECRET_KEY = os.getenv("SECRET_KEY", "sklad-secret-key-change-in-production-2024")
SESSION_MAX_AGE = int(os.getenv("SESSION_MAX_AGE", "28800"))  # 8 часов = 28800 секунд

# Google Sheets (опционально)
GOOGLE_CREDS_FILE = os.getenv("GOOGLE_CREDS_FILE", "service_account.json")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "")

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "sklad_app.log")

# File uploads
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
ITEM_IMAGES_DIR = os.getenv("ITEM_IMAGES_DIR", "item_images")
MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10"))

# QR Codes
QR_CODE_DIR = os.getenv("QR_CODE_DIR", "qr_codes")

# Exports
EXPORT_DIR = os.getenv("EXPORT_DIR", "exports")

# Backups
BACKUP_DIR = os.getenv("BACKUP_DIR", "backups")

# Forms & Templates
FORMS_DIR = os.getenv("FORMS_DIR", "forms")
ROUTE_TEMPLATE_DOCX = os.getenv("ROUTE_TEMPLATE_DOCX", "Шаблон Маршрутной карты.docx")

# Production Planning
WORKING_HOURS_PER_DAY = int(os.getenv("WORKING_HOURS_PER_DAY", "7"))
MINUTES_PER_DAY = int(os.getenv("MINUTES_PER_DAY", "420"))

# Timezone (Иркутский часовой пояс — UTC+8)
TIMEZONE = os.getenv("TIMEZONE", "Asia/Irkutsk")
