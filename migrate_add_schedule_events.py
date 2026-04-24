"""Миграция: добавление таблицы schedule_events и поля actual_quantity"""
import sys
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(__file__))
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://sklad_user:sklad_pass@localhost:5432/sklad_db")

engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    # 1. Таблица schedule_events
    conn.execute(text("""
    CREATE TABLE IF NOT EXISTS schedule_events (
        id SERIAL PRIMARY KEY,
        schedule_id INTEGER NOT NULL REFERENCES production_schedule(id) ON DELETE CASCADE,
        event_type VARCHAR(30) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_by VARCHAR(100)
    )
    """))

    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_se_schedule ON schedule_events(schedule_id)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_se_type ON schedule_events(event_type)"))

    # 2. Поле actual_quantity в production_schedule
    try:
        conn.execute(text("ALTER TABLE production_schedule ADD COLUMN actual_quantity INTEGER"))
    except Exception:
        pass  # Уже существует

    conn.commit()

print("✅ Миграция выполнена: schedule_events + actual_quantity")
