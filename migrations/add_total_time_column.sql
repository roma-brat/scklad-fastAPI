-- Миграция: добавление колонки total_time в таблицу route_operations
-- total_time = duration_minutes + prep_time + control_time (для планирования)

-- Добавляем колонку
ALTER TABLE route_operations ADD COLUMN IF NOT EXISTS total_time INTEGER DEFAULT 0;

-- Заполняем существующие записи
UPDATE route_operations 
SET total_time = COALESCE(duration_minutes, 0) + COALESCE(prep_time, 0) + COALESCE(control_time, 0)
WHERE total_time = 0;

-- Индекс для быстрого поиска
CREATE INDEX IF NOT EXISTS idx_route_operations_total_time ON route_operations(total_time);
