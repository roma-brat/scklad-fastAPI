"""API роуты для оборудования и инвентаря цеха"""
import logging
from fastapi import APIRouter, Request, Query, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from main import get_db, get_user
from typing import Optional

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/equipment", tags=["equipment"])
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def equipment_list(request: Request, search: Optional[str] = Query(None)):
    """Список оборудования"""
    user = get_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    db = get_db()
    try:
        equipment = db.get_all_equipment()
    except Exception:
        equipment = []

    if search:
        equipment = [e for e in equipment if search.lower() in e.get('name', '').lower()]

    return templates.TemplateResponse("equipment/list.html", {
        "request": request,
        "current_user": user,
        "equipment": equipment,
        "search": search
    })


@router.get("/workshop", response_class=HTMLResponse)
async def workshop_inventory_page(request: Request):
    """Страница инвентаря цеха"""
    user = get_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    db = get_db()
    try:
        equipment = db.get_equipment_with_storage()
        inventory = db.get_all_workshops_inventory()
        all_items = db.get_items_dict_list()
    except Exception as e:
        logger.error(f"Workshop inventory load error: {e}")
        equipment = []
        inventory = []
        all_items = []
    
    # Группируем инвентарь по equipment_id
    inventory_by_eq = {}
    for inv in inventory:
        eq_id = inv.get('equipment_id')
        if eq_id not in inventory_by_eq:
            inventory_by_eq[eq_id] = []
        inventory_by_eq[eq_id].append(inv)
    
    return templates.TemplateResponse("equipment/workshop_inventory.html", {
        "request": request,
        "current_user": user,
        "equipment": equipment,
        "inventory_by_eq": inventory_by_eq,
        "all_items": all_items
    })


# ========== API Endpoints для Workshop Inventory ==========

@router.get("/api/users-with-items")
async def get_users_with_items(request: Request):
    """Получить всех пользователей с их инструментами"""
    user = get_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=403)
    
    db = get_db()
    try:
        users = db.get_all_users()
        all_user_items = db.get_all_user_items()
        
        # Группируем инструменты по user_id
        items_by_user = {}
        for item in all_user_items:
            uid = item.get('user_id')
            if uid not in items_by_user:
                items_by_user[uid] = []
            items_by_user[uid].append(item)
        
        # Формируем ответ
        result = []
        for u in users:
            user_id = u.get('id')
            user_items = items_by_user.get(user_id, [])
            total_qty = sum(i.get('quantity', 0) for i in user_items)
            
            result.append({
                'id': user_id,
                'username': u.get('username'),
                'workstation': u.get('workstation'),
                'items': user_items,
                'total_items': len(user_items),
                'total_quantity': total_qty
            })
        
        return JSONResponse({'users': result})
    except Exception as e:
        logger.error(f"Get users with items error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/api/workshop/inventory")
async def get_workshop_inventory_api(request: Request):
    """Получить весь инвентарь цеха"""
    user = get_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=403)
    
    db = get_db()
    try:
        inventory = db.get_all_workshops_inventory()
        equipment = db.get_equipment_with_storage()
        
        # Группируем по equipment_id
        inventory_by_eq = {}
        for inv in inventory:
            eq_id = inv.get('equipment_id')
            if eq_id not in inventory_by_eq:
                inventory_by_eq[eq_id] = []
            inventory_by_eq[eq_id].append(inv)
        
        return JSONResponse({
            'inventory': inventory_by_eq,
            'equipment': equipment
        })
    except Exception as e:
        logger.error(f"Get workshop inventory error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/api/workshop/add")
async def add_to_workshop(
    request: Request,
    equipment_id: int = Form(...),
    item_id: str = Form(...),
    quantity: int = Form(1)
):
    """Добавить инструмент на станок"""
    user = get_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=403)
    
    db = get_db()
    try:
        success = db.add_to_workshop_inventory(item_id, equipment_id, quantity)
        if success:
            return JSONResponse({"success": True, "message": "Инструмент добавлен"})
        else:
            return JSONResponse({"error": "Ошибка добавления"}, status_code=500)
    except Exception as e:
        logger.error(f"Add to workshop error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/api/workshop/remove")
async def remove_from_workshop(
    request: Request,
    inventory_id: int = Form(...),
    quantity: int = Form(1)
):
    """Уменьшить количество инструмента на станке"""
    user = get_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=403)
    
    db = get_db()
    try:
        success = db.remove_from_workshop_inventory_by_id(inventory_id, quantity)
        if success:
            return JSONResponse({"success": True, "message": "Инструмент удален"})
        else:
            return JSONResponse({"error": "Ошибка удаления"}, status_code=500)
    except Exception as e:
        logger.error(f"Remove from workshop error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.delete("/api/workshop/items/{inventory_id}")
async def delete_workshop_item(request: Request, inventory_id: int):
    """Удалить запись инвентаря полностью"""
    user = get_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=403)
    
    db = get_db()
    try:
        success = db.delete_workshop_inventory_item(inventory_id)
        if success:
            return JSONResponse({"success": True, "message": "Запись удалена"})
        else:
            return JSONResponse({"error": "Ошибка удаления"}, status_code=500)
    except Exception as e:
        logger.error(f"Delete workshop item error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)
