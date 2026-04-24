-- Миграция: добавить колонку pdf_file для хранения PDF файла маршрута
-- Выполнить: psql -U postgres -d sklad_db -f migrate_add_route_pdf.sql

-- Проверяем существование колонки и добавляем если нет
DO $$
BEGIN
    -- Проверяем, есть ли колонка pdf_file в таблице detail_routes
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'detail_routes' AND column_name = 'pdf_file'
    ) THEN
        ALTER TABLE detail_routes ADD COLUMN pdf_file VARCHAR(500);
        RAISE NOTICE 'Колонка pdf_file добавлена в таблицу detail_routes';
    ELSE
        RAISE NOTICE 'Колонка pdf_file уже существует в таблице detail_routes';
    END IF;
    
    -- Проверяем существование колонки pdf_path
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'detail_routes' AND column_name = 'pdf_path'
    ) THEN
        ALTER TABLE detail_routes ADD COLUMN pdf_path VARCHAR(500);
        RAISE NOTICE 'Колонка pdf_path добавлена в таблицу detail_routes';
    END IF;
    
    -- Проверяем существование колонки pdf_data
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'detail_routes' AND column_name = 'pdf_data'
    ) THEN
        ALTER TABLE detail_routes ADD COLUMN pdf_data TEXT;
        RAISE NOTICE 'Колонка pdf_data добавлена в таблицу detail_routes';
    END IF;
END $$;