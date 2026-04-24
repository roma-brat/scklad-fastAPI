"""API роуты для управления товарами"""
from fastapi import APIRouter, Request, Query, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from main import get_db, get_user
from typing import Optional
import json, logging, os

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/items", tags=["items"])
templates = Jinja2Templates(directory="templates")
IMAGES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "item_images")


def has_image(item_id: str) -> bool:
    for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
        if os.path.exists(os.path.join(IMAGES_DIR, f"{item_id}{ext}")):
            return True
    return False


def parse_specs(form_data: dict) -> dict:
    specs = {}
    for k, v in form_data.items():
        if k.startswith('spec_key_') and v:
            idx = k.split('_')[-1]
            val = form_data.get(f'spec_val_{idx}', '')
            if val:
                specs[v] = val
    return specs


@router.get("/search-suggestions")
async def search_suggestions(request: Request, q: str = Query("")):
    """API для автодополнения поиска"""
    user = get_user(request)
    if not user:
        return JSONResponse({"suggestions": []})
    
    db = get_db()
    try:
        if not q or len(q) < 2:
            return JSONResponse({"suggestions": []})
        
        # Получаем все товары и фильтруем
        all_items = db.get_all_items()
        q_lower = q.lower()
        
        # Фильтруем по названию или ID
        matches = []
        for item in all_items[:500]:  # Ограничиваем для производительности
            name = item.get('name', '')
            item_id = item.get('item_id', '')
            category = item.get('category', '')
            
            if q_lower in name.lower() or q_lower in item_id.lower() or q_lower in category.lower():
                matches.append({
                    "id": item_id,
                    "name": name,
                    "category": category or '',
                    "quantity": item.get('quantity', 0),
                })
                
                if len(matches) >= 10:  # Максимум 10 результатов
                    break
        
        return JSONResponse({"suggestions": matches})
    except Exception as e:
        logger.error(f"Search suggestions error: {e}")
        return JSONResponse({"suggestions": []})


@router.get("/", response_class=HTMLResponse)
async def items_list(request: Request, search: Optional[str] = Query(None), category: Optional[str] = Query(None), page: int = Query(1), view: Optional[str] = Query(None)):
    user = get_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    db = get_db()
    try:
        if search:
            items = db.search_items(query=search)
            if category:
                items = [i for i in items if i.get('category') == category]
        elif category:
            all_items = db.get_all_items()
            items = [i for i in all_items if i.get('category') == category]
        else:
            items = db.get_all_items()
    except Exception as e:
        logger.error(f"Items load error: {e}")
        items = []
    
    # Сериализация — уже dict, обрабатываем specs
    serialized = []
    for d in items:
        if not isinstance(d, dict):
            continue
        d = d.copy()
        # Нормализуем категорию — всегда строка
        d['category'] = (d.get('category') or '').strip()
        
        specs_raw = d.get('specifications', '')
        if specs_raw and isinstance(specs_raw, str):
            try:
                specs_dict = json.loads(specs_raw)
                d['specifications'] = ' | '.join(f"{k}: {v}" for k, v in specs_dict.items())
                d['specs_json'] = specs_raw
            except Exception:
                d['specifications'] = ''
                d['specs_json'] = '{}'
        elif specs_raw and isinstance(specs_raw, dict):
            d['specifications'] = ' | '.join(f"{k}: {v}" for k, v in specs_raw.items())
            d['specs_json'] = json.dumps(specs_raw)
        else:
            d['specifications'] = ''
            d['specs_json'] = '{}'
        
        d['_has_image'] = has_image(d.get('item_id', ''))
        serialized.append(d)

    # Получаем категории из БД
    try:
        categories = db.get_all_categories()
    except Exception:
        categories = []

    # Нормализация + сортировка
    for d in serialized:
        d['category'] = str(d.get('category') or '').strip()
    
    def sort_key(d):
        cat = d['category']
        name = d.get('name') or ''
        if cat:
            return (0, cat.lower(), name.lower())
        else:
            return (1, '', name.lower())
    
    serialized.sort(key=sort_key)

    # Для режима "группы" — все элементы без пагинации
    # Для таблицы — с пагинацией
    view_mode = view or 'table'
    per_page = 50
    total = len(serialized)
    paginated = serialized

    if view_mode != 'grouped':
        start = (page - 1) * per_page
        paginated = serialized[start:start + per_page]

    logger.info(f"Items: {total}, categories from DB: {len(categories)}, view={view_mode}")

    return templates.TemplateResponse("items/list.html", {
        "request": request, "current_user": user, "items": paginated,
        "categories": categories, "current_category": category, "search": search,
        "page": page, "total_pages": max(1, (total + per_page - 1) // per_page),
        "total_items": total, "view_mode": view_mode, "page_size": per_page,
        "has_image": has_image,
        "all_items_json": json.dumps(serialized, ensure_ascii=False),  # Все товары для клиентского поиска
    })


@router.post("/action")
async def items_action(
    request: Request,
    action: str = Form(...),
    item_id: str = Form(None),
    original_id: str = Form(None),
    name: str = Form(None),
    quantity: int = Form(None),
    min_stock: int = Form(None),
    category: str = Form(None),
    location: str = Form(None),
    shop_url: str = Form(None),
    image_url: str = Form(None),
    detail: str = Form(None),
    reason: str = Form(None),
):
    user = get_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    db = get_db()
    
    # Собрать характеристики из формы
    form = await request.form()
    specs = parse_specs(dict(form))
    specs_json = json.dumps(specs) if specs else None
    
    if action == "create":
        try:
            db.create_item(item_id=item_id, name=name, quantity=quantity or 0, min_stock=min_stock or 1, category=category, location=location)
            # Обновить доп поля через отдельный метод
            if shop_url or image_url or specs_json:
                if shop_url:
                    db.update_item_field(item_id, 'shop_url', shop_url)
                if image_url:
                    db.update_item_field(item_id, 'image_url', image_url)
                if specs_json:
                    db.update_item_field(item_id, 'specifications', specs_json)
        except Exception as e:
            logger.error(f"Create error: {e}")

    elif action == "edit":
        edit_id = original_id or item_id
        try:
            if name:
                db.update_item_field(edit_id, 'name', name)
            if category is not None:
                db.update_item_field(edit_id, 'category', category)
            if quantity is not None:
                db.update_item_field(edit_id, 'quantity', quantity)
            if min_stock is not None:
                db.update_item_field(edit_id, 'min_stock', min_stock)
            if location is not None:
                db.update_item_field(edit_id, 'location', location)
            if shop_url is not None:
                db.update_item_field(edit_id, 'shop_url', shop_url)
            if image_url is not None:
                db.update_item_field(edit_id, 'image_url', image_url)
            if specs_json:
                db.update_item_field(edit_id, 'specifications', specs_json)
        except Exception as e:
            logger.error(f"Edit error: {e}")
    
    elif action == "income":
        try:
            # Получаем текущее количество и добавляем
            current_item = db.get_item_by_id(item_id)
            if current_item:
                new_qty = (current_item.get('quantity', 0) or 0) + (quantity or 0)
                db.update_item_quantity(
                    item_id=item_id, 
                    new_quantity=new_qty, 
                    changed_by=user["id"], 
                    operation_type="income", 
                    detail=detail
                )
        except Exception as e:
            logger.error(f"Income error: {e}")

    elif action == "expense":
        try:
            # Получаем текущее количество и вычитаем
            current_item = db.get_item_by_id(item_id)
            if current_item:
                current_qty = current_item.get('quantity', 0) or 0
                new_qty = max(0, current_qty - (quantity or 0))  # Не уходим в минус
                db.update_item_quantity(
                    item_id=item_id, 
                    new_quantity=new_qty, 
                    changed_by=user["id"], 
                    operation_type="expense", 
                    reason=reason
                )
        except Exception as e:
            logger.error(f"Expense error: {e}")
    
    return RedirectResponse(url="/items/", status_code=303)
