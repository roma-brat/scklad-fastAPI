"""API роуты для импорта/экспорта"""
import os
import uuid
import logging
from fastapi import APIRouter, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from main import get_db, get_user
from services.excel_import_service import ExcelImportService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/import", tags=["import"])
templates = Jinja2Templates(directory="templates")

# Временная директория для загрузки файлов
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.get("/excel", response_class=HTMLResponse)
async def excel_import_page(request: Request):
    """Страница импорта из Excel"""
    user = get_user(request)
    if not user or user.get("role") != "admin":
        return RedirectResponse(url="/dashboard", status_code=303)
    return templates.TemplateResponse("import/excel.html", {
        "request": request,
        "current_user": user
    })


@router.post("/excel/upload")
async def excel_upload(
    request: Request,
    file: UploadFile = File(...)
):
    """Загрузка и парсинг Excel файла"""
    user = get_user(request)
    if not user or user.get("role") != "admin":
        return JSONResponse({"error": "Unauthorized"}, status_code=403)
    
    # Валидация файла
    if not file.filename or not file.filename.endswith(('.xlsx', '.xls')):
        return JSONResponse({"error": "Поддерживаются только .xlsx и .xls файлы"}, status_code=400)
    
    try:
        # Сохраняем временный файл
        file_id = str(uuid.uuid4())
        file_ext = os.path.splitext(file.filename)[1]
        temp_path = os.path.join(UPLOAD_DIR, f"{file_id}{file_ext}")
        
        content = await file.read()
        if len(content) > 10 * 1024 * 1024:  # 10MB limit
            return JSONResponse({"error": "Файл слишком большой (макс. 10MB)"}, status_code=400)
        
        with open(temp_path, 'wb') as f:
            f.write(content)
        
        # Парсим файл
        service = ExcelImportService()
        result = service.parse_excel_file(temp_path)
        
        if 'error' in result:
            return JSONResponse({"error": result['error']}, status_code=400)
        
        # Автоматический маппинг
        mapping = service.auto_detect_mapping()
        
        # Сохраняем service в session для последующего импорта
        request.session[f'import_{file_id}'] = {
            'file_path': temp_path,
            'mapping': mapping,
            'headers': result['headers'],
            'row_count': result['row_count']
        }
        
        return JSONResponse({
            'file_id': file_id,
            'sheets': result['sheets'],
            'headers': result['headers'],
            'row_count': result['row_count'],
            'preview': result['data'][:10],  # Первые 10 строк для превью
            'mapping': mapping
        })
        
    except Exception as e:
        logger.error(f"Excel upload error: {e}")
        return JSONResponse({"error": f"Ошибка загрузки: {str(e)}"}, status_code=500)


@router.post("/excel/preview")
async def excel_preview(
    request: Request,
    file_id: str = Form(...),
    page: int = Form(1),
    page_size: int = Form(50)
):
    """Превью данных с пагинацией"""
    user = get_user(request)
    if not user or user.get("role") != "admin":
        return JSONResponse({"error": "Unauthorized"}, status_code=403)
    
    import_data = request.session.get(f'import_{file_id}')
    if not import_data:
        return JSONResponse({"error": "Данные не найдены. Загрузите файл заново."}, status_code=404)
    
    # Перечитываем файл для превью
    service = ExcelImportService()
    result = service.parse_excel_file(import_data['file_path'])
    
    if 'error' in result:
        return JSONResponse({"error": result['error']}, status_code=400)
    
    # Пагинация
    data = result['data']
    total = len(data)
    start = (page - 1) * page_size
    end = start + page_size
    
    return JSONResponse({
        'preview': data[start:end],
        'page': page,
        'total_pages': (total + page_size - 1) // page_size,
        'total': total,
        'mapping': import_data['mapping']
    })


@router.post("/excel/import")
async def excel_execute_import(
    request: Request,
    file_id: str = Form(...),
    update_duplicates: bool = Form(False),
    column_mapping: str = Form(None)  # JSON string
):
    """Выполнение импорта в БД"""
    user = get_user(request)
    if not user or user.get("role") != "admin":
        return JSONResponse({"error": "Unauthorized"}, status_code=403)
    
    import_data = request.session.get(f'import_{file_id}')
    if not import_data:
        return JSONResponse({"error": "Данные не найдены. Загрузите файл заново."}, status_code=404)
    
    try:
        db = get_db()
        
        # Парсим файл заново
        service = ExcelImportService()
        result = service.parse_excel_file(import_data['file_path'])
        
        if 'error' in result:
            return JSONResponse({"error": result['error']}, status_code=400)
        
        # Используем маппинг из сессии или переданный
        mapping = import_data.get('mapping', {})
        if column_mapping:
            import json
            mapping.update(json.loads(column_mapping))
        
        # Получаем существующие item_id для проверки дубликатов
        existing_items = db.get_all_items(use_cache=False)
        existing_ids = {item.get('item_id') for item in existing_items if isinstance(item, dict)}
        
        # Валидация и маппинг
        validation = service.validate_and_map_data(mapping, existing_ids)
        
        if not validation['valid_items']:
            return JSONResponse({
                'error': 'Нет валидных данных для импорта',
                'errors': validation['errors'][:20]  # Первые 20 ошибок
            }, status_code=400)
        
        # Выполняем импорт
        import_result = service.execute_import(
            db,
            validation['valid_items'],
            update_duplicates=update_duplicates
        )
        
        # Очищаем сессию
        if f'import_{file_id}' in request.session:
            del request.session[f'import_{file_id}']
        
        # Удаляем временный файл
        if os.path.exists(import_data['file_path']):
            os.remove(import_data['file_path'])
        
        return JSONResponse({
            'success': True,
            'created': import_result['created'],
            'updated': import_result['updated'],
            'skipped': import_result['skipped'],
            'errors': import_result['errors'][:20],  # Первые 20 ошибок
            'validation_errors': validation['errors'][:20],
            'stats': validation['stats']
        })
        
    except Exception as e:
        logger.error(f"Excel import error: {e}")
        return JSONResponse({"error": f"Ошибка импорта: {str(e)}"}, status_code=500)


@router.get("/db-compare", response_class=HTMLResponse)
async def db_compare_page(request: Request):
    """Страница сравнительного импорта"""
    user = get_user(request)
    if not user or user.get("role") != "admin":
        return RedirectResponse(url="/dashboard", status_code=303)
    
    # Получаем список доступных таблиц
    from services.db_import_service import DbImportService
    db = get_db()
    import_service = DbImportService(db)
    
    try:
        available_tables = import_service.get_available_tables()
    except Exception as e:
        logger.error(f"Get tables error: {e}")
        available_tables = []
    
    return templates.TemplateResponse("import/db_compare.html", {
        "request": request,
        "current_user": user,
        "available_tables": available_tables
    })


@router.post("/db-compare/upload")
async def db_compare_upload(
    request: Request,
    file: UploadFile = File(...)
):
    """Загрузка Excel для сравнительного импорта"""
    user = get_user(request)
    if not user or user.get("role") != "admin":
        return JSONResponse({"error": "Unauthorized"}, status_code=403)

    if not file.filename or not file.filename.endswith(('.xlsx', '.xls')):
        return JSONResponse({"error": "Поддерживаются только .xlsx и .xls файлы"}, status_code=400)

    try:
        # Сохраняем временный файл
        file_id = str(uuid.uuid4())
        file_ext = os.path.splitext(file.filename)[1]
        temp_path = os.path.join(UPLOAD_DIR, f"{file_id}{file_ext}")

        content = await file.read()
        if len(content) > 10 * 1024 * 1024:
            return JSONResponse({"error": "Файл слишком большой (макс. 10MB)"}, status_code=400)

        with open(temp_path, 'wb') as f:
            f.write(content)

        # Читаем Excel
        db = get_db()
        from services.db_import_service import DbImportService
        import_service = DbImportService(db)
        
        sheets = import_service.read_excel_sheets(temp_path)
        
        # Сохраняем в session
        request.session[f'db_import_{file_id}'] = {
            'file_path': temp_path,
            'sheets': list(sheets.keys())
        }

        return JSONResponse({
            'file_id': file_id,
            'sheets': list(sheets.keys()),
            'sheet_info': {name: {'rows': len(df), 'cols': list(df.columns)} 
                          for name, df in sheets.items()}
        })

    except Exception as e:
        logger.error(f"DB compare upload error: {e}")
        return JSONResponse({"error": f"Ошибка загрузки: {str(e)}"}, status_code=500)


@router.post("/db-compare/analyze")
async def db_compare_analyze(
    request: Request,
    file_id: str = Form(...),
    table_name: str = Form(...)
):
    """Анализ различий между Excel и БД"""
    user = get_user(request)
    if not user or user.get("role") != "admin":
        return JSONResponse({"error": "Unauthorized"}, status_code=403)

    import_data = request.session.get(f'db_import_{file_id}')
    if not import_data:
        return JSONResponse({"error": "Данные не найдены"}, status_code=404)

    try:
        db = get_db()
        from services.db_import_service import DbImportService
        import_service = DbImportService(db)
        
        # Читаем Excel
        sheets = import_service.read_excel_sheets(import_data['file_path'])
        
        if table_name not in sheets:
            return JSONResponse({"error": f"Лист '{table_name}' не найден в файле"}, status_code=404)
        
        # Сравниваем с БД
        df = sheets[table_name]
        comparison = import_service.compare_with_database(table_name, df)
        
        return JSONResponse({
            'comparison': comparison,
            'table_name': table_name
        })

    except Exception as e:
        logger.error(f"DB compare analyze error: {e}")
        return JSONResponse({"error": f"Ошибка анализа: {str(e)}"}, status_code=500)


@router.post("/db-compare/import")
async def db_compare_import(
    request: Request,
    file_id: str = Form(...),
    table_name: str = Form(...),
    update_existing: bool = Form(True),
    insert_new: bool = Form(True)
):
    """Выполнение импорта после сравнения"""
    user = get_user(request)
    if not user or user.get("role") != "admin":
        return JSONResponse({"error": "Unauthorized"}, status_code=403)

    import_data = request.session.get(f'db_import_{file_id}')
    if not import_data:
        return JSONResponse({"error": "Данные не найдены"}, status_code=404)

    try:
        db = get_db()
        from services.db_import_service import DbImportService
        import_service = DbImportService(db)
        
        # Читаем Excel
        sheets = import_service.read_excel_sheets(import_data['file_path'])
        df = sheets.get(table_name)
        
        if df is None:
            return JSONResponse({"error": "Данные не найдены"}, status_code=404)
        
        # Выполняем импорт
        result = import_service.import_to_database(table_name, df, 
                                                   update_existing=update_existing,
                                                   insert_new=insert_new)
        
        # Очищаем session
        request.session.pop(f'db_import_{file_id}', None)
        
        # Удаляем временный файл
        if os.path.exists(import_data['file_path']):
            os.remove(import_data['file_path'])

        return JSONResponse({
            'success': True,
            'result': result
        })

    except Exception as e:
        logger.error(f"DB compare import error: {e}")
        return JSONResponse({"error": f"Ошибка импорта: {str(e)}"}, status_code=500)
