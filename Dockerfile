# ============================================
# Dockerfile — Склад Инструментов (FastAPI)
# ============================================
# Использование:
#   docker build -t sklad-app .
#   docker run -p 8551:8551 sklad-app
#
# Или через docker-compose:
#   docker-compose up -d
# ============================================

# Базовый образ
FROM python:3.11-slim

# Рабочая директория
WORKDIR /app

# ============================================
# Системные зависимости
# ============================================
RUN apt-get update && apt-get install -y \
    # Для psycopg2 (PostgreSQL)
    libpq-dev \
    # GCC для компиляции C-расширений
    gcc \
    # Для проверки здоровья контейнера
    curl \
    # Для работы с русскими шрифтами в PDF (reportlab)
    fonts-noto-cyrillic \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get autoremove -y

# ============================================
# Python зависимости
# ============================================
COPY requirements.txt .

# Кэшируем зависимости для ускорения пересборок
RUN pip install --no-cache-dir pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# ============================================
# Код приложения
# ============================================
COPY . .

# ============================================
# Создание служебных директорий
# ============================================
RUN mkdir -p /app/uploads \
             /app/item_images \
             /app/qr_codes \
             /app/exports \
             /app/backups \
             /app/logs

# ============================================
# Создание пользователя (не запускаем от root)
# ============================================
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

# ============================================
# Переменные окружения
# ============================================
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_ENV=production

# Порт приложения
EXPOSE 8551

# ============================================
# Запуск приложения
# ============================================
# В Docker запускаем напрямую main:app (не run.py, т.к. run.py для локальной разработки)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8551"]
