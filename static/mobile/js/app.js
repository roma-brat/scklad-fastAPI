/**
 * JavaScript для мобильного веб-приложения склада.
 * Работает с FastAPI API endpoints.
 */

// ======================== SEARCH ========================

let searchTimer = null;

function debounceSearch(query) {
    if (searchTimer) clearTimeout(searchTimer);
    searchTimer = setTimeout(() => performSearch(query), 300);
}

async function performSearch(query) {
    const resultsContainer = document.getElementById('search-results');
    
    if (!query || query.length < 1) {
        resultsContainer.style.display = 'none';
        return;
    }
    
    try {
        const formData = new FormData();
        formData.append('query', query);
        
        const response = await fetch('/mobile/api/search', {
            method: 'POST',
            body: formData,
        });
        
        const data = await response.json();
        
        if (data.success && data.results.length > 0) {
            resultsContainer.innerHTML = data.results.map(item => `
                <div class="card" onclick="showItemCard('${item.item_id}', '${escapeHtml(item.name)}', ${item.quantity}, '${escapeHtml(item.location || '')}', '${escapeHtml(item.category || '')}')">
                    <div class="card-title">${escapeHtml(item.name)}</div>
                    <div class="card-subtitle">Код: ${item.item_id}</div>
                    <div class="card-row">
                        <span>${item.location ? '📍 ' + escapeHtml(item.location) : ''}</span>
                        <span class="quantity ${item.quantity > 0 ? 'in-stock' : 'out-of-stock'}">
                            Кол-во: ${item.quantity}
                        </span>
                    </div>
                </div>
            `).join('');
            resultsContainer.style.display = 'block';
        } else {
            resultsContainer.innerHTML = '<div class="empty-state">Ничего не найдено</div>';
            resultsContainer.style.display = 'block';
        }
    } catch (error) {
        console.error('Search error:', error);
    }
}

async function searchByCode() {
    const codeInput = document.getElementById('manual-code');
    const code = codeInput.value.trim();
    
    if (!code) {
        showMessage('Введите код товара', 'warning');
        return;
    }
    
    try {
        const response = await fetch(`/mobile/api/item/${encodeURIComponent(code)}`);
        const data = await response.json();
        
        if (data.success && data.item) {
            const item = data.item;
            showItemCard(item.item_id, item.name, item.quantity, item.location || '', item.category || '');
        } else {
            showMessage(`Товар '${code}' не найден`, 'error');
        }
    } catch (error) {
        console.error('Search by code error:', error);
        showMessage('Ошибка поиска', 'error');
    }
}

// ======================== ITEM CARD ========================

function showItemCard(itemId, name, quantity, location, category) {
    const cardContainer = document.getElementById('item-card');
    
    // Получаем станки пользователя
    const workstations = getUserWorkstations();
    const hasMultipleWorkshops = workstations && workstations.length > 1;
    
    let workshopSelector = '';
    if (hasMultipleWorkshops) {
        workshopSelector = `
            <div class="form-group">
                <label>Выберите станок:</label>
                <select id="take-workshop" class="form-control">
                    ${workstations.map(ws => `<option value="${escapeHtml(ws)}">${escapeHtml(ws)}</option>`).join('')}
                </select>
            </div>
        `;
    }
    
    cardContainer.innerHTML = `
        <div class="item-card-content">
            <h3>${escapeHtml(name)}</h3>
            <div class="card-subtitle">Код: ${itemId}</div>
            ${location ? `<div class="card-subtitle">📍 ${escapeHtml(location)}</div>` : ''}
            ${category ? `<div class="card-subtitle">📁 ${escapeHtml(category)}</div>` : ''}
            
            <div class="quantity-display ${quantity > 0 ? 'in-stock' : 'out-of-stock'}">
                Количество: ${quantity}
            </div>
            
            ${workshopSelector}
            <div class="action-row">
                <input 
                    type="number" 
                    id="take-quantity" 
                    value="1" 
                    min="1" 
                    max="${quantity}"
                    class="quantity-input"
                >
                <button 
                    class="btn-take" 
                    onclick="takeItem('${itemId}', ${quantity})"
                    ${quantity <= 0 ? 'disabled' : ''}
                >
                    Взять
                </button>
            </div>
            
            <button class="btn-close" onclick="closeItemCard()">Закрыть</button>
        </div>
    `;
    
    cardContainer.style.display = 'block';
    cardContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function closeItemCard() {
    document.getElementById('item-card').style.display = 'none';
}

// ======================== TAKE ITEM ========================

async function takeItem(itemId, maxQuantity) {
    const qtyInput = document.getElementById('take-quantity');
    const workshopSelect = document.getElementById('take-workshop');
    const selectedWorkshop = workshopSelect ? workshopSelect.value : null;
    const quantity = parseInt(qtyInput.value);
    
    if (!quantity || quantity <= 0) {
        showMessage('Введите корректное количество', 'warning');
        return;
    }
    
    if (quantity > maxQuantity) {
        showMessage(`На складе только ${maxQuantity} шт.`, 'warning');
        return;
    }
    
    try {
        const formData = new FormData();
        formData.append('item_id', itemId);
        formData.append('quantity', quantity);
        if (selectedWorkshop) {
            formData.append('equipment_name', selectedWorkshop);
        }
        
        const response = await fetch('/mobile/api/take_item', {
            method: 'POST',
            body: formData,
        });
        
        const data = await response.json();
        
        if (data.success) {
            showMessage(`✅ Выдано: ${quantity} шт.`, 'success');
            closeItemCard();
            document.getElementById('search-input').value = '';
            document.getElementById('search-results').style.display = 'none';
            // Обновляем склад станков
            loadWorkshopInventory();
        } else {
            showMessage(data.message || 'Ошибка', 'error');
        }
    } catch (error) {
        console.error('Take item error:', error);
        showMessage('Ошибка сети', 'error');
    }
}

// ======================== MY ITEMS ========================

async function loadMyItems() {
    try {
        const response = await fetch('/mobile/api/user_items');
        const data = await response.json();
        
        const container = document.getElementById('my-items');
        
        if (data.success && data.items.length > 0) {
            container.innerHTML = data.items.map(item => `
                <div class="card">
                    <div class="card-title">${escapeHtml(item.item_name)}</div>
                    <div class="card-subtitle">Код: ${item.item_code}</div>
                    <div class="card-row">
                        <span class="quantity in-stock">×${item.quantity}</span>
                        <div class="action-buttons">
                            <button class="btn-move" onclick="showMoveToWorkshopDialog('${item.item_code}', '${escapeHtml(item.item_name)}', ${item.quantity})">
                                🏭 Переместить
                            </button>
                            <button class="btn-return" onclick="showReturnDialog('${item.item_code}', '${escapeHtml(item.item_name)}', ${item.quantity})">
                                ↩️ Вернуть
                            </button>
                            <button class="btn-writeoff" onclick="showWriteoffDialog('${item.item_code}', '${escapeHtml(item.item_name)}', ${item.quantity})">
                                🗑 Списать
                            </button>
                        </div>
                    </div>
                </div>
            `).join('');
        } else {
            container.innerHTML = '<div class="empty-state">Нет взятых инструментов</div>';
        }
    } catch (error) {
        console.error('Load my items error:', error);
    }
}

// ======================== RETURN ITEM ========================

function showReturnDialog(itemCode, itemName, quantity) {
    const overlay = document.getElementById('dialog-overlay');
    const content = document.getElementById('dialog-content');
    
    const user = currentUser;
    const hasWorkshop = user.workstation;
    
    content.innerHTML = `
        <h3>Возврат инструмента</h3>
        <div class="dialog-info">
            <div><strong>${escapeHtml(itemName)}</strong></div>
            <div>Количество: ${quantity}</div>
        </div>
        <div class="dialog-question">Куда вернуть?</div>
        <div class="dialog-buttons">
            <button class="btn-primary" onclick="returnItem('${itemCode}', ${quantity}, false)">
                🏢 На основной склад
            </button>
            ${hasWorkshop ? `
                <button class="btn-success" onclick="returnItem('${itemCode}', ${quantity}, true)">
                    🏭 На склад (${escapeHtml(hasWorkshop)})
                </button>
            ` : ''}
        </div>
        <button class="btn-close" onclick="closeDialog()">Отмена</button>
    `;
    
    overlay.style.display = 'flex';
}

async function returnItem(itemCode, quantity, returnToWorkshop) {
    try {
        const formData = new FormData();
        formData.append('item_code', itemCode);
        formData.append('quantity', quantity);
        formData.append('return_to_workshop', returnToWorkshop.toString());
        
        const response = await fetch('/mobile/api/return_item', {
            method: 'POST',
            body: formData,
        });
        
        const data = await response.json();
        
        if (data.success) {
            showMessage('✅ Инструмент возвращен', 'success');
            closeDialog();
            loadWorkshopInventory();
        } else {
            showMessage(data.message || 'Ошибка', 'error');
        }
    } catch (error) {
        console.error('Return item error:', error);
        showMessage('Ошибка сети', 'error');
    }
}

// ======================== WRITEOFF ITEM ========================

function showWriteoffDialog(itemCode, itemName, quantity) {
    const overlay = document.getElementById('dialog-overlay');
    const content = document.getElementById('dialog-content');
    
    content.innerHTML = `
        <h3>Списание инструмента</h3>
        <div class="dialog-info">
            <div><strong>${escapeHtml(itemName)}</strong></div>
            <div>Количество: ${quantity}</div>
        </div>
        <div class="form-group">
            <label>Причина списания</label>
            <textarea id="writeoff-reason" placeholder="Укажите причину..." rows="3"></textarea>
        </div>
        <div class="dialog-buttons">
            <button class="btn-warning" onclick="writeoffItem('${itemCode}', ${quantity})">
                Списать
            </button>
        </div>
        <button class="btn-close" onclick="closeDialog()">Отмена</button>
    `;
    
    overlay.style.display = 'flex';
}

async function writeoffItem(itemCode, quantity) {
    const reason = document.getElementById('writeoff-reason').value.trim();
    
    if (!reason) {
        showMessage('Укажите причину списания', 'warning');
        return;
    }
    
    try {
        const formData = new FormData();
        formData.append('item_code', itemCode);
        formData.append('quantity', quantity);
        formData.append('reason', reason);
        
        const response = await fetch('/mobile/api/writeoff_item', {
            method: 'POST',
            body: formData,
        });
        
        const data = await response.json();
        
        if (data.success) {
            showMessage('✅ Инструмент списан', 'success');
            closeDialog();
            loadWorkshopInventory();
        } else {
            showMessage(data.message || 'Ошибка', 'error');
        }
    } catch (error) {
        console.error('Writeoff item error:', error);
        showMessage('Ошибка сети', 'error');
    }
}

// ======================== WORKSHOP INVENTORY ========================

async function loadWorkshopInventory() {
    try {
        const response = await fetch('/mobile/api/workshop_inventory');
        const data = await response.json();
        
        const container = document.getElementById('workshop-inventory');
        
        if (data.success && data.items.length > 0) {
            container.innerHTML = data.items.map(item => `
                <div class="card">
                    <div class="card-title">${escapeHtml(item.item_name)}</div>
                    <div class="card-subtitle">Код: ${item.item_code}</div>
                    <div class="card-subtitle">📍 ${escapeHtml(item.workshop_name)}</div>
                    <div class="card-row">
                        <span class="quantity in-stock">Кол-во: ${item.quantity}</span>
                        <button class="btn-more" onclick="showWorkshopActions(${item.id}, '${item.item_code}', '${escapeHtml(item.item_name)}', ${item.quantity}, '${escapeHtml(item.workshop_name)}')">
                            ⋮
                        </button>
                    </div>
                </div>
            `).join('');
        } else {
            container.innerHTML = '<div class="empty-state">На складе станка нет инструментов</div>';
        }
    } catch (error) {
        console.error('Load workshop inventory error:', error);
    }
}

function showWorkshopActions(inventoryId, itemCode, itemName, quantity, workshopName) {
    const overlay = document.getElementById('dialog-overlay');
    const content = document.getElementById('dialog-content');

    content.innerHTML = `
        <h3>${escapeHtml(itemName)}</h3>
        <div class="dialog-info">
            <div>Код: ${itemCode}</div>
            <div>Склад: ${escapeHtml(workshopName)}</div>
            <div>Количество: ${quantity}</div>
        </div>
        <div class="dialog-buttons">
            <button class="btn-primary" onclick="returnWorkshopItem(${inventoryId}, '${itemCode}', ${quantity}, '${escapeHtml(workshopName)}')">
                ↩️ Вернуть на склад
            </button>
            <button class="btn-warning" onclick="showWorkshopWriteoffDialog(${inventoryId}, '${itemCode}', '${escapeHtml(itemName)}', ${quantity})">
                🗑 Списать
            </button>
        </div>
        <button class="btn-close" onclick="closeDialog()">Отмена</button>
    `;

    overlay.style.display = 'flex';
}

function showWorkshopWriteoffDialog(inventoryId, itemCode, itemName, quantity) {
    const overlay = document.getElementById('dialog-overlay');
    const content = document.getElementById('dialog-content');

    content.innerHTML = `
        <h3>Списание инструмента</h3>
        <div class="dialog-info">
            <div><strong>${escapeHtml(itemName)}</strong></div>
            <div>Код: ${itemCode}</div>
            <div>Количество: ${quantity}</div>
        </div>
        <div class="form-group">
            <label>Причина списания</label>
            <textarea id="writeoff-reason" placeholder="Укажите причину..." rows="3"></textarea>
        </div>
        <div class="dialog-buttons">
            <button class="btn-warning" onclick="writeoffWorkshopItem(${inventoryId}, '${itemCode}', ${quantity})">
                Списать
            </button>
        </div>
        <button class="btn-close" onclick="closeDialog()">Отмена</button>
    `;

    overlay.style.display = 'flex';
}

async function writeoffWorkshopItem(inventoryId, itemCode, quantity) {
    const reason = document.getElementById('writeoff-reason').value.trim();

    if (!reason) {
        showMessage('Укажите причину списания', 'warning');
        return;
    }

    try {
        const formData = new FormData();
        formData.append('inventory_id', inventoryId);
        formData.append('item_code', itemCode);
        formData.append('quantity', quantity);
        formData.append('reason', reason);

        const response = await fetch('/mobile/api/writeoff_workshop_item', {
            method: 'POST',
            body: formData,
        });

        const data = await response.json();

        if (data.success) {
            showMessage('✅ Инструмент списан', 'success');
            closeDialog();
            loadWorkshopInventory();
        } else {
            showMessage(data.message || 'Ошибка', 'error');
        }
    } catch (error) {
        console.error('Writeoff workshop item error:', error);
        showMessage('Ошибка сети', 'error');
    }
}

async function returnWorkshopItem(inventoryId, itemCode, quantity, workshopName) {
    try {
        const formData = new FormData();
        formData.append('inventory_id', inventoryId);
        formData.append('item_code', itemCode);
        formData.append('quantity', quantity);
        formData.append('workshop_name', workshopName);
        
        const response = await fetch('/mobile/api/return_workshop_item', {
            method: 'POST',
            body: formData,
        });
        
        const data = await response.json();
        
        if (data.success) {
            showMessage('✅ Инструмент возвращен', 'success');
            closeDialog();
            loadWorkshopInventory();
        } else {
            showMessage(data.message || 'Ошибка', 'error');
        }
    } catch (error) {
        console.error('Return workshop item error:', error);
        showMessage('Ошибка сети', 'error');
    }
}

// ======================== TASKS ========================

let currentTaskPeriod = 'today';

async function loadTasks(period = 'today') {
    currentTaskPeriod = period;
    document.querySelectorAll('.period-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.period === period);
    });

    const container = document.getElementById('tasks-list');
    container.innerHTML = '<p class="empty-state">Загрузка...</p>';

    try {
        const resp = await fetch(`/mobile/api/tasks?period=${period}`);
        console.log('Tasks API status:', resp.status);
        
        if (!resp.ok) {
            const errorText = await resp.text();
            console.error('Tasks API error:', errorText);
            container.innerHTML = `
                <div class="error-message">
                    <strong>Ошибка API (${resp.status}):</strong><br>
                    <pre style="font-size:10px;overflow:auto;">${errorText}</pre>
                </div>
            `;
            return;
        }
        
        const data = await resp.json();
        console.log('Tasks API response:', data);

        if (!data.success || !data.tasks || data.tasks.length === 0) {
            // Показываем просто сообщение без диагностики
            container.innerHTML = '<p class="empty-state">Нет задач на этот период</p>';
            return;
        }

        const priorityColors = { 1: '#ef4444', 2: '#f97316', 3: '#eab308', 4: '#22c55e', 5: '#3b82f6' };
        const statusBorderColors = {
            'planned': '#3b82f6',
            'in_progress': '#f59e0b',
            'completed': '#22c55e',
            'delayed': '#ef4444',
        };

        const html = data.tasks.map(task => {
            // console.log('Task data:', task);
            const borderColor = statusBorderColors[task.status] || '#3b82f6';
            const isInProgress = task.status === 'in_progress';
            const isPlanned = task.status === 'planned';

            // Форматируем время начала
            let timeStarted = '';
            if (task.taken_at) {
                try {
                    const d = new Date(task.taken_at);
                    timeStarted = `В работе с: ${d.getHours().toString().padStart(2,'0')}:${d.getMinutes().toString().padStart(2,'0')}`;
                } catch(e) {}
            }
            
            // Кто взял в работу
            let takenBy = '';
            if (task.taken_by) {
                takenBy = `<span class="badge badge-info">👤 ${escapeHtml(task.taken_by)}</span> `;
            }

            // Бейджи
            let badges = '';
            if (task.has_no_drawing) badges += '<span class="badge badge-warning">📄 Нет чертежа</span> ';
            if (task.has_no_nc_program) badges += '<span class="badge badge-warning">💻 Нет УП</span> ';
            if (task.has_otk_pending) badges += '<span class="badge badge-warning">⏳ На ОТК</span> ';
            if (task.has_otk_rejected) badges += '<span class="badge badge-error">❌ Есть замечание</span> ';
            if (task.has_first_piece_checked) badges += '<span class="badge badge-success">✅ Первая проверена</span> ';

            // Кнопки
            let buttons = '';
            if (isPlanned) {
                buttons = `
                    <button class="btn-take-task" onclick="takeTask(${task.id}, ${task.order_id})">Взять в работу</button>
                    <div class="task-flag-buttons">
                        <button class="btn-flag" onclick="flagNoDrawing(${task.id})">Нет чертежа</button>
                        <button class="btn-flag" onclick="flagNoNcProgram(${task.id})">Нет УП</button>
                    </div>
                `;
            } else if (isInProgress) {
                // Если уже отправлено на ОТК - показываем кнопку "Исправить замечание" если есть замечание
                const canComplete = !task.has_otk_pending || task.has_first_piece_checked;
                buttons = `
                    ${!task.has_otk_pending ? `<button class="btn-first-piece-full" onclick="sendToOtk(${task.id})">Проверить первую деталь</button>` : ''}
                    ${task.has_otk_pending && !task.has_first_piece_checked ? `<button class="btn-flag btn-warning" onclick="showCompleteDialog(${task.id}, ${task.quantity}, ${task.order_id})" disabled>Ожидает ОТК</button>` : ''}
                    ${task.has_first_piece_checked ? `<button class="btn-complete-full" onclick="showCompleteDialog(${task.id}, ${task.quantity}, ${task.order_id})">Завершить работу</button>` : ''}
                    <div class="task-flag-buttons">
                        <button class="btn-flag" onclick="showAddToolDialog(${task.id}, ${task.order_id}, ${task.equipment_id || 0})">🔧 Инструмент</button>
                        <button class="btn-flag" onclick="flagNoDrawing(${task.id})">Нет чертежа</button>
                        <button class="btn-flag" onclick="flagNoNcProgram(${task.id})">Нет УП</button>
                    </div>
                `;
            }

            // Добавляем инструменты в задачу
            let toolsHtml = '';
            if (task.tools && task.tools.length > 0) {
                const toolIcons = {
                    'main': '🏭',
                    'workshop': '🏭',
                    'user': '🎒'
                };
                toolsHtml = `
                    <div class="task-tools" style="margin-top: 8px; padding: 8px; background: #f0fdf4; border-radius: 6px; border: 1px solid #bbf7d0;">
                        <div style="font-size: 12px; color: #166534; font-weight: 600; margin-bottom: 4px;">🔧 Инструменты:</div>
                        <div style="font-size: 12px;">
                            ${task.tools.map(t => `
                                <span style="display: inline-block; margin: 2px; padding: 2px 6px; background: white; border-radius: 4px; border: 1px solid #86efac;">
                                    ${toolIcons[t.source] || '🔧'} ${escapeHtml(t.item_name || t.item_id)} × ${t.quantity}
                                </span>
                            `).join('')}
                        </div>
                    </div>
                `;
            }

            return `
                <div class="task-card" style="border-left: 4px solid ${borderColor}">
                    <div class="task-header">
                        <div class="card-title">${escapeHtml(task.detail_name || task.designation || '')}</div>
                        <span class="priority-badge" style="background:${priorityColors[task.priority] || '#6b7280'}">${task.priority}</span>
                    </div>
                    <div class="card-subtitle">${escapeHtml(task.operation_name || '')}</div>
                    <div class="card-subtitle">${task.planned_date || ''} · ${escapeHtml(task.equipment_name || '')}</div>
                    <div class="card-subtitle">План: ${task.quantity} деталей</div>
                    ${timeStarted ? `<div class="card-subtitle" style="color:#f59e0b">${timeStarted}</div>` : ''}
                    ${takenBy ? `<div class="task-badges">${takenBy}${badges}</div>` : ''}
                    ${toolsHtml}
                    ${buttons}
                </div>
            `;
        }).join('');

        container.innerHTML = html;
    } catch (e) {
        document.getElementById('tasks-list').innerHTML = `<p class="empty-state">Ошибка загрузки: ${e.message}</p>`;
    }
}

let addToolScheduleId = null;
let addToolOrderId = null;
let addToolEquipmentId = null;

async function takeTask(scheduleId, orderId) {
    // Просто берем задачу в работу без инструментов
    if (!confirm('Взять задачу в работу?')) return;

    try {
        const formData = new FormData();
        formData.append('schedule_id', scheduleId);
        const resp = await fetch('/mobile/api/take_task', { method: 'POST', body: formData });
        const data = await resp.json();

        if (data.success) {
            showMessage('✅ Задача взята в работу', 'success');
            loadTasks(currentTaskPeriod);
            // Обновляем "Мои задачи в работе"
            if (typeof loadMyInProgressTasks === 'function') {
                loadMyInProgressTasks();
            }
        } else {
            showMessage(data.message || 'Ошибка', 'error');
        }
    } catch (e) {
        showMessage('Ошибка сети: ' + e.message, 'error');
    }
}

// Диалог добавления инструмента с поиском
let dialogToolsData = [];

function showAddToolDialog(scheduleId, orderId, equipmentId) {
    addToolScheduleId = scheduleId;
    addToolOrderId = orderId;
    addToolEquipmentId = equipmentId;

    // Показываем загрузку
    const overlay = document.getElementById('dialog-overlay');
    const content = document.getElementById('dialog-content');
    content.innerHTML = '<h3>🔧 Загрузка инструментов...</h3>';
    overlay.style.display = 'flex';

    // Загружаем доступные инструменты (фильтруем по станку задачи)
    let apiUrl = '/mobile/api/user/available-tools';
    if (equipmentId) {
        apiUrl += `?equipment_id=${equipmentId}`;
    }

    fetch(apiUrl)
        .then(resp => resp.json())
        .then(data => {
            console.log('Available tools API response:', data);
            console.log('API returned tools count:', data.tools?.length || 0);
            if (data.success) {
                // Не ограничиваем срезом - теперь бэкенд возвращает только нужные данные
                dialogToolsData = data.tools || [];
                console.log('Total tools loaded:', dialogToolsData.length);
            } else {
                dialogToolsData = [];
                console.log('API error:', data.message);
            }
            renderToolDialogWithDatalist();
        })
        .catch(err => {
            showMessage('Ошибка загрузки инструментов', 'error');
        });
}

function renderToolDialogWithDatalist() {
    // Фильтруем только склад станков
    const workshopStock = dialogToolsData.filter(t => t.source === 'workshop');

    const overlay = document.getElementById('dialog-overlay');
    const content = document.getElementById('dialog-content');

    // Используем select вместо datalist для лучшей совместимости
    const workshopSelectOptions = workshopStock.map(t =>
        `<option value="${escapeHtml(t.item_name)}" data-item-id="${escapeHtml(t.item_id)}" data-source="${escapeHtml(t.source)}" data-equipment-id="${t.equipment_id || ''}" data-equipment-name="${escapeHtml(t.source_name || '')}" data-available="${t.available}">${escapeHtml(t.item_name)} (${t.available})</option>`
    ).join('');

    // Заголовок зависит от того, выбран ли конкретный станок
    const title = addToolEquipmentId
        ? '🔧 Инструменты со склада станка'
        : '🔧 Инструменты со склада станков';

    // Подзаголовок с названием станка
    let subtitle = '';
    if (addToolEquipmentId && workshopStock.length > 0) {
        const firstTool = workshopStock[0];
        subtitle = `<div style="color: #666; margin-bottom: 12px; font-size: 14px;">📍 ${escapeHtml(firstTool.source_name || 'Станок')}</div>`;
    } else if (addToolEquipmentId && workshopStock.length === 0) {
        subtitle = `<div style="color: #f59e0b; margin-bottom: 12px; font-size: 14px;">ℹ️ На складе станка нет инструментов</div>`;
    }

    content.innerHTML = `
        <h3>${title}</h3>
        ${subtitle}

        <div class="add-tool-section">
            <div class="add-tool-label">🏭 ${addToolEquipmentId ? 'Склад станка' : 'Склад станков'}</div>
            <select id="dialog-workshop-stock" class="add-tool-input" style="width: 100%; padding: 10px; font-size: 14px;">
                <option value="">-- Выберите инструмент --</option>
                ${workshopSelectOptions}
            </select>
            <input type="number" id="dialog-workshop-qty" class="add-tool-qty" value="1" min="1" placeholder="Кол-во" style="margin-top: 8px;">
        </div>

        <div class="add-tool-actions">
            <button class="btn-primary btn-add" onclick="addToolToTask()">✓ Добавить</button>
            <button class="btn-cancel" onclick="closeDialog()">✕ Отмена</button>
        </div>
    `;

    overlay.style.display = 'flex';
}

async function addToolToTask() {
    const workshopSelect = document.getElementById('dialog-workshop-stock');
    const workshopQty = document.getElementById('dialog-workshop-qty');
    
    const selectedTools = [];
    
    // Обработка склада станков (теперь select)
    if (workshopSelect && workshopSelect.value) {
        const selectedOption = workshopSelect.options[workshopSelect.selectedIndex];
        const itemId = selectedOption.dataset.itemId;
        const itemName = workshopSelect.value;
        const equipmentId = selectedOption.dataset.equipmentId;
        const available = parseInt(selectedOption.dataset.available) || 1;
        
        if (itemId) {
            selectedTools.push({
                item_id: itemId,
                item_name: itemName,
                quantity: parseInt(workshopQty ? workshopQty.value : 1),
                source: 'workshop',
                source_name: 'Склад станков',
                equipment_id: equipmentId || null,
                schedule_id: addToolScheduleId,
                order_id: addToolOrderId,
                equipment_name: selectedOption.dataset.equipmentName || ''
            });
        } else {
            showMessage('Выберите инструмент из списка', 'warning');
            return;
        }
    }
    
    if (selectedTools.length === 0) {
        showMessage('Выберите инструмент', 'warning');
        return;
    }
    
    closeDialog();
    
    try {
        const formData = new FormData();
        formData.append('schedule_id', addToolScheduleId);
        formData.append('tools_json', JSON.stringify(selectedTools));
        
        const response = await fetch('/mobile/api/take_task_with_tools', {
            method: 'POST',
            body: formData,
        });
        
        const data = await response.json();
        
        if (data.success) {
            showMessage('✅ Инструмент добавлен', 'success');
            loadTasks(currentTaskPeriod);
            // Обновляем "Мои задачи в работе"
            if (typeof loadMyInProgressTasks === 'function') {
                loadMyInProgressTasks();
            }
        } else {
            showMessage(data.message || 'Ошибка', 'error');
        }
    } catch (error) {
        showMessage('Ошибка сети', 'error');
    }
}

// Диалог выбора инструментов при взятии задачи
function showToolSelectDialog(orderId, scheduleId) {
    const overlay = document.getElementById('dialog-overlay');
    const content = document.getElementById('dialog-content');
    
    content.innerHTML = `
        <h3>Выберите инструмент</h3>
        <p style="color: #666; margin-bottom: 16px;">Выберите инструмент для этой операции. Он будет закреплен за заказом.</p>
        <input type="text" id="tool-search" placeholder="Поиск инструмента..." 
               style="width: 100%; padding: 10px; margin-bottom: 12px; border: 1px solid #ddd; border-radius: 6px;"
               oninput="filterTools(this.value)">
        <div id="tool-selector-dialog" class="card-list" style="max-height: 300px; overflow-y: auto;">
            <p class="empty-state">Загрузка...</p>
        </div>
        <div style="display: flex; gap: 8px; margin-top: 16px;">
            <button class="btn-primary" style="flex:1" onclick="submitSelectedTools(${orderId}, ${scheduleId})">Сохранить</button>
            <button class="btn-secondary" style="padding: 12px;" onclick="closeDialog()">Пропустить</button>
        </div>
    `;
    
    overlay.style.display = 'flex';
    
    // Загружаем доступные инструменты
    loadToolsForSelector();
}

let allTools = [];

async function loadToolsForSelector(search = '') {
    try {
        const url = search ? `/mobile/api/user/available-tools?search=${encodeURIComponent(search)}` : '/mobile/api/user/available-tools';
        const resp = await fetch(url);
        const data = await resp.json();
        
        const container = document.getElementById('tool-selector-dialog');
        
        if (data.success && data.tools && data.tools.length > 0) {
            allTools = data.tools;
            container.innerHTML = data.tools.map(tool => `
                <div class="card tool-card" data-name="${tool.item_name.toLowerCase()}">
                    <div class="card-row">
                        <input type="checkbox" 
                               class="tool-checkbox"
                               data-item-id="${tool.item_id}"
                               data-item-name="${tool.item_name}"
                               data-source="${tool.source}"
                               data-source-name="${tool.source_name}"
                               data-equipment-id="${tool.equipment_id || ''}">
                        <div style="flex:1">
                            <div class="card-title">${escapeHtml(tool.item_name)}</div>
                            <div class="card-subtitle">${tool.source_name} (доступно: ${tool.available})</div>
                        </div>
                        <input type="number" class="tool-qty" value="1" min="1" max="${tool.available}" data-item-id="${tool.item_id}">
                    </div>
                </div>
            `).join('');
        } else {
            container.innerHTML = '<p class="empty-state">Нет доступных инструментов</p>';
        }
    } catch (e) {
        document.getElementById('tool-selector-dialog').innerHTML = '<p class="error-message">Ошибка: ' + e.message + '</p>';
    }
}

function filterTools(search) {
    const container = document.getElementById('tool-selector-dialog');
    const searchLower = search.toLowerCase();
    
    if (!allTools.length) return;
    
    const filtered = allTools.filter(tool => 
        tool.item_name.toLowerCase().includes(searchLower)
    );
    
    if (filtered.length > 0) {
        container.innerHTML = filtered.map(tool => `
            <div class="card tool-card" data-name="${tool.item_name.toLowerCase()}">
                <div class="card-row">
                    <input type="checkbox" 
                           class="tool-checkbox"
                           data-item-id="${tool.item_id}"
                           data-item-name="${tool.item_name}"
                           data-source="${tool.source}"
                           data-source-name="${tool.source_name}"
                           data-equipment-id="${tool.equipment_id || ''}">
                    <div style="flex:1">
                        <div class="card-title">${escapeHtml(tool.item_name)}</div>
                        <div class="card-subtitle">${tool.source_name} (доступно: ${tool.available})</div>
                    </div>
                    <input type="number" class="tool-qty" value="1" min="1" max="${tool.available}" data-item-id="${tool.item_id}">
                </div>
            </div>
        `).join('');
    } else {
        container.innerHTML = '<p class="empty-state">Инструменты не найдены</p>';
    }
}

async function submitSelectedTools(orderId, scheduleId) {
    // Собираем выбранные инструменты
    const checkboxes = document.querySelectorAll('#tool-selector-dialog .tool-checkbox:checked');
    const tools = [];
    
    checkboxes.forEach(cb => {
        const itemId = cb.dataset.itemId;
        const qtyInput = document.querySelector(`#tool-selector-dialog .tool-qty[data-item-id="${itemId}"]`);
        tools.push({
            item_id: itemId,
            item_name: cb.dataset.itemName,
            quantity: parseInt(qtyInput?.value || 1),
            source: cb.dataset.source,
            source_name: cb.datasetSourceName,
            equipment_id: cb.dataset.equipmentId || null
        });
    });
    
    if (tools.length === 0) {
        closeDialog();
        loadTasks(currentTaskPeriod);
        // Обновляем "Мои задачи в работе"
        if (typeof loadMyInProgressTasks === 'function') {
            loadMyInProgressTasks();
        }
        return;
    }
    
    try {
        const formData = new FormData();
        formData.append('order_id', orderId);
        formData.append('tools_json', JSON.stringify(tools));
        
        const resp = await fetch('/mobile/api/save_order_tools', { method: 'POST', body: formData });
        const data = await resp.json();
        
        if (data.success) {
            alert('✅ Инструменты сохранены');
            closeDialog();
            loadTasks(currentTaskPeriod);
            // Обновляем "Мои задачи в работе"
            if (typeof loadMyInProgressTasks === 'function') {
                loadMyInProgressTasks();
            }
        } else {
            alert('Ошибка: ' + (data.message || 'Неизвестная'));
        }
    } catch (e) {
        alert('Ошибка сети: ' + e.message);
    }
}

// ===== ФЛАГИ =====

async function flagNoDrawing(scheduleId) {
    try {
        const formData = new FormData();
        formData.append('schedule_id', scheduleId);
        const resp = await fetch('/mobile/api/flag_no_drawing', { method: 'POST', body: formData });
        const data = await resp.json();
        if (data.success) { 
            loadTasks(currentTaskPeriod); 
            if (typeof loadMyInProgressTasks === 'function') loadMyInProgressTasks();
        }
        else { alert('Ошибка: ' + (data.message || '')); }
    } catch (e) { alert('Ошибка: ' + e.message); }
}

async function flagNoNcProgram(scheduleId) {
    try {
        const formData = new FormData();
        formData.append('schedule_id', scheduleId);
        const resp = await fetch('/mobile/api/flag_no_nc_program', { method: 'POST', body: formData });
        const data = await resp.json();
        if (data.success) { 
            loadTasks(currentTaskPeriod); 
            if (typeof loadMyInProgressTasks === 'function') loadMyInProgressTasks();
        }
        else { alert('Ошибка: ' + (data.message || '')); }
    } catch (e) { alert('Ошибка: ' + e.message); }
}

async function sendToOtk(scheduleId) {
    if (!confirm('Отправить деталь на проверку ОТК?')) return;
    
    try {
        const formData = new FormData();
        formData.append('schedule_id', scheduleId);
        const resp = await fetch('/mobile/api/send_to_otk', { method: 'POST', body: formData });
        const data = await resp.json();
        
        if (data.success) {
            alert('Деталь отправлена на ОТК');
            loadTasks(currentTaskPeriod);
            if (typeof loadMyInProgressTasks === 'function') loadMyInProgressTasks();
        } else {
            alert('Ошибка: ' + (data.message || 'Неизвестная'));
        }
    } catch (e) {
        alert('Ошибка сети: ' + e.message);
    }
}

// ===== ДИАЛОГ ЗАВЕРШЕНИЯ =====

let completeTaskOrderId = null;
let completeTaskTools = [];

async function showCompleteDialog(scheduleId, plannedQty, orderId) {
    completeTaskOrderId = orderId;
    completeTaskTools = [];
    
    // Показываем загрузку инструментов
    const overlay = document.createElement('div');
    overlay.className = 'dialog-overlay';
    overlay.innerHTML = `
        <div class="complete-dialog">
            <h3>Завершить работу</h3>
            <p>План: ${plannedQty} деталей</p>
            <div style="margin: 12px 0; color: #666;">Загрузка инструментов...</div>
            <div class="qty-control">
                <button onclick="changeQty(-1)">−</button>
                <input type="number" id="complete-qty" value="${plannedQty}" min="0" max="${plannedQty * 2}">
                <button onclick="changeQty(1)">+</button>
            </div>
            <div class="dialog-actions">
                <button class="btn-cancel" onclick="closeCompleteDialog()">Отмена</button>
                <button class="btn-confirm" onclick="completeTask(${scheduleId})">Завершить</button>
            </div>
        </div>
    `;
    document.body.appendChild(overlay);
    overlay.addEventListener('click', (e) => { if (e.target === overlay) closeCompleteDialog(); });
    
    // Загружаем инструменты заказа
    if (orderId) {
        try {
            const resp = await fetch(`/mobile/api/order/tools/${orderId}`);
            const data = await resp.json();
            if (data.success && data.tools && data.tools.length > 0) {
                completeTaskTools = data.tools;
                showCompleteDialogWithTools(scheduleId, plannedQty, data.tools);
            } else {
                // Нет инструментов - показываем стандартный диалог
                showCompleteDialogWithTools(scheduleId, plannedQty, []);
            }
        } catch (e) {
            console.error('Load tools error:', e);
            showCompleteDialogWithTools(scheduleId, plannedQty, []);
        }
    } else {
        showCompleteDialogWithTools(scheduleId, plannedQty, []);
    }
}

function showCompleteDialogWithTools(scheduleId, plannedQty, tools) {
    // Удаляем старый диалог
    const oldDialog = document.querySelector('.complete-dialog');
    if (oldDialog) oldDialog.remove();
    const oldOverlay = document.querySelector('.dialog-overlay');
    if (oldOverlay) oldOverlay.remove();
    
    completeTaskTools = tools || [];
    
    // Если есть инструменты, показываем выбор списать/вернуть
    let toolsHtml = '';
    if (completeTaskTools && completeTaskTools.length > 0) {
        toolsHtml = `
            <div class="complete-tools-section">
                <div class="complete-tools-title">🔧 Инструменты (выберите действие):</div>
                <div class="complete-tools-list">
                    ${completeTaskTools.map((tool, idx) => `
                        <div class="complete-tool-item">
                            <div class="complete-tool-info">
                                <div class="complete-tool-name">${escapeHtml(tool.item_name || '')}</div>
                                <div class="complete-tool-qty">Использовано: ${tool.quantity || 1}</div>
                            </div>
                            <div class="complete-tool-actions">
                                <button class="btn-tool-action btn-writeoff" onclick="setToolAction(${idx}, 'writeoff')">🗑 Списать</button>
                                <button class="btn-tool-action btn-return" onclick="setToolAction(${idx}, 'return')">🏭 Вернуть</button>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }
    
    const overlay = document.createElement('div');
    overlay.className = 'dialog-overlay';
    overlay.innerHTML = `
        <div class="complete-dialog">
            <h3>Завершить работу</h3>
            <p>План: ${plannedQty} деталей</p>
            ${toolsHtml}
            <div class="qty-control">
                <button onclick="changeQty(-1)">−</button>
                <input type="number" id="complete-qty" value="${plannedQty}" min="0" max="${plannedQty * 2}">
                <button onclick="changeQty(1)">+</button>
            </div>
            <div class="dialog-actions">
                <button class="btn-cancel" onclick="closeCompleteDialog()">Отмена</button>
                <button class="btn-confirm" onclick="completeTaskWithTools(${scheduleId})">Завершить</button>
            </div>
        </div>
    `;
    document.body.appendChild(overlay);
    overlay.addEventListener('click', (e) => { if (e.target === overlay) closeCompleteDialog(); });
}

function setToolAction(toolIndex, action) {
    // Обновляем действие для инструмента
    if (completeTaskTools && completeTaskTools[toolIndex]) {
        completeTaskTools[toolIndex]._action = action;
        
        // Обновляем визуальное состояние кнопок
        const toolItems = document.querySelectorAll('.complete-tool-item');
        if (toolItems && toolItems[toolIndex]) {
            const item = toolItems[toolIndex];
            item.classList.remove('action-writeoff', 'action_return');
            if (action === 'writeoff') {
                item.classList.add('action-writeoff');
            } else if (action === 'return') {
                item.classList.add('action-return');
            }
        }
    }
}

function changeQty(delta) {
    const input = document.getElementById('complete-qty');
    if (input) {
        input.value = Math.max(0, parseInt(input.value || 0) + delta);
    }
}

function closeCompleteDialog() {
    const overlay = document.querySelector('.dialog-overlay');
    if (overlay) overlay.remove();
    const dialog = document.querySelector('.complete-dialog');
    if (dialog) dialog.remove();
    completeTaskTools = [];
    completeTaskOrderId = null;
}

async function completeTaskWithTools(scheduleId) {
    const qtyInput = document.getElementById('complete-qty');
    const qty = parseInt(qtyInput ? qtyInput.value : '0') || 0;

    // Собираем действия с инструментами
    const toolActions = [];
    if (completeTaskTools && completeTaskTools.length > 0) {
        for (const tool of completeTaskTools) {
            const action = tool._action || 'writeoff'; // По умолчанию списываем
            toolActions.push({
                item_id: tool.item_id,
                quantity: tool.quantity || 1,
                action: action,
                equipment_id: tool.equipment_id
            });
        }
    }

    // Закрываем диалог сразу
    const dialog = document.querySelector('.complete-dialog');
    const overlay = document.querySelector('.dialog-overlay');
    if (dialog) {
        dialog.style.display = 'none';
        dialog.remove();
    }
    if (overlay) {
        overlay.style.display = 'none';
        overlay.remove();
    }

    try {
        const formData = new FormData();
        formData.append('schedule_id', scheduleId);
        formData.append('actual_quantity', qty);
        formData.append('tools_json', JSON.stringify(toolActions));
        
        const resp = await fetch('/mobile/api/order/complete-with-tool-actions', { 
            method: 'POST', 
            body: formData 
        });
        const data = await resp.json();

        if (data.success) {
            const remainder = data.remainder || 0;
            if (remainder < 0) {
                alert(`Задача завершена. Не выполнено: ${Math.abs(remainder)} деталей — перенесено на следующий день.`);
            } else if (remainder > 0) {
                alert(`Задача завершена. Перевыполнение: ${remainder} деталей учтено.`);
            } else {
                alert('Задача завершена!');
            }
            loadTasks(currentTaskPeriod);
        } else {
            alert('Ошибка: ' + (data.message || ''));
        }
    } catch (e) {
        alert('Ошибка: ' + e.message);
    }
}

async function completeTask(scheduleId) {
    // Это обёртка для совместимости - вызываем новую функцию
    await completeTaskWithTools(scheduleId);
}

// ======================== UI HELPERS ========================

function closeDialog() {
    document.getElementById('dialog-overlay').style.display = 'none';
}

function showMessage(message, type = 'info') {
    // Create toast message
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    
    setTimeout(() => toast.classList.add('show'), 10);
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Close dialog on overlay click
document.getElementById('dialog-overlay')?.addEventListener('click', (e) => {
    if (e.target.id === 'dialog-overlay') {
        closeDialog();
    }
});

// ======================== QR SCANNER ========================

let html5QrCode = null;
let qrScannerActive = false;

/**
 * Navigate to the production QR scanner page
 * Used from the "Сканировать QR-код" button on My Page
 */
function openQRScanner() {
    window.location.href = '/mobile/qr-scanner';
}

/**
 * Legacy QR scanner for item codes (kept for backwards compatibility)
 * Opens inline modal scanner for tool/item QR codes
 */
async function openItemQRScanner() {
    const modal = document.getElementById('qr-scanner-modal');
    modal.style.display = 'flex';
    
    try {
        html5QrCode = new Html5Qrcode("qr-reader");
        
        await html5QrCode.start(
            {
                facingMode: "environment" // Задняя камера
            },
            {
                fps: 10,
                qrbox: { width: 250, height: 250 },
                aspectRatio: 1.0
            },
            (decodedText, decodedResult) => {
                // QR-код успешно распознан!
                if (qrScannerActive) return; // Защита от двойного срабатывания
                qrScannerActive = true;
                
                // Останавливаем сканер
                html5QrCode.stop().then(() => {
                    closeQRScanner();
                    handleQRScan(decodedText);
                }).catch(err => {
                    console.error("Error stopping scanner:", err);
                    closeQRScanner();
                    handleQRScan(decodedText);
                });
            },
            (errorMessage) => {
                // Ошибка сканирования (нормально когда QR не в кадре)
            }
        );
        
        console.log("QR Scanner started");
    } catch (err) {
        console.error("Error starting QR scanner:", err);
        closeQRScanner();
        
        if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
            showMessage('❌ Доступ к камере запрещён. Разрешите в настройках браузера', 'error');
        } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFound') {
            showMessage('❌ Камера не найдена на устройстве', 'error');
        } else {
            showMessage(`❌ Ошибка камеры: ${err.message}`, 'error');
        }
    }
}

function closeQRScanner() {
    const modal = document.getElementById('qr-scanner-modal');
    modal.style.display = 'none';
    qrScannerActive = false;
    
    if (html5QrCode) {
        html5QrCode.stop().catch(err => {
            // Игнорируем ошибки при остановке
        });
        html5QrCode.clear();
        html5QrCode = null;
    }
}

async function handleQRScan(code) {
    console.log("QR scanned:", code);
    showMessage('📷 QR-код распознан, поиск...', 'info');
    
    try {
        const response = await fetch(`/mobile/api/item/${encodeURIComponent(code)}`);
        const data = await response.json();
        
        if (data.success && data.item) {
            const item = data.item;
            showItemCard(item.item_id, item.name, item.quantity, 
                        item.location || '', item.category || '');
            showMessage('✅ Инструмент найден!', 'success');
        } else {
            showMessage(`❌ Инструмент с кодом '${code}' не найден`, 'error');
        }
    } catch (error) {
        console.error("QR scan error:", error);
        showMessage('❌ Ошибка поиска инструмента', 'error');
    }
}

// ======================== TOOL SELECTOR ========================

let selectedOrderId = null;
let selectedTools = [];

async function loadAvailableOrders() {
    try {
        const response = await fetch('/mobile/api/available-orders');
        const data = await response.json();
        
        const container = document.getElementById('available-orders');
        
        if (data.success && data.orders && data.orders.length > 0) {
            container.innerHTML = data.orders.map(order => `
                <div class="card" onclick="selectOrderForTools(${order.id}, '${escapeHtml(order.designation || '')}', '${escapeHtml(order.operation_name || '')}')">
                    <div class="card-title">${escapeHtml(order.designation || '')}</div>
                    <div class="card-subtitle">${escapeHtml(order.operation_name || '')}</div>
                    <div class="card-row">
                        <span>План: ${order.planned_quantity} шт.</span>
                        <span>📅 ${order.planned_date || ''}</span>
                    </div>
                </div>
            `).join('');
        } else {
            container.innerHTML = '<div class="empty-state">Нет доступных заказов</div>';
        }
    } catch (error) {
        console.error('Load orders error:', error);
    }
}

function selectOrderForTools(orderId, designation, operationName) {
    selectedOrderId = orderId;
    document.getElementById('tool-selector').style.display = 'block';
    loadAvailableTools();
}

async function loadAvailableTools() {
    try {
        const response = await fetch('/mobile/api/user/available-tools');
        const data = await response.json();
        
        const container = document.getElementById('available-tools');
        
        // Сохраняем для использования в dropdown
        window._availableTools = data.tools || [];
        const tools = window._availableTools;
        
        if (data.success && tools && tools.length > 0) {
            // Группируем по источникам
            const mainStock = tools.filter(t => t.source === 'main');
            const workshopStock = tools.filter(t => t.source === 'workshop');
            
            let mainHtml = '';
            let workshopHtml = '';
            
            if (mainStock.length > 0) {
                mainHtml = `
                    <div class="tool-source-section">
                        <div class="tool-source-header">🏢 Основной склад</div>
                        <select id="main-stock-select" class="tool-select" onchange="onMainStockChange()">
                            <option value="">-- Выберите --</option>
                            ${mainStock.map(t => `<option value="${t.item_id}" data-available="${t.available}" data-source="${t.source}" data-source-name="${escapeHtml(t.source_name)}">${escapeHtml(t.item_name)} (${t.available} шт)</option>`).join('')}
                        </select>
                        <input type="number" id="main-stock-qty" class="tool-qty-compact" value="1" min="1" placeholder="Кол-во">
                    </div>
                `;
            }
            
            if (workshopStock.length > 0) {
                workshopHtml = `
                    <div class="tool-source-section">
                        <div class="tool-source-header">🏭 Склад станков</div>
                        <select id="workshop-stock-select" class="tool-select" onchange="onWorkshopStockChange()">
                            <option value="">-- Выберите --</option>
                            ${workshopStock.map(t => `<option value="${t.item_id}" data-available="${t.available}" data-source="${t.source}" data-source-name="${escapeHtml(t.source_name)}" data-equipment-id="${t.equipment_id || ''}">${escapeHtml(t.item_name)} (${t.available} шт)</option>`).join('')}
                        </select>
                        <input type="number" id="workshop-stock-qty" class="tool-qty-compact" value="1" min="1" placeholder="Кол-во">
                    </div>
                `;
            }
            
            container.innerHTML = mainHtml + workshopHtml;
        } else {
            container.innerHTML = '<div class="empty-state">Нет доступных инструментов</div>';
        }
    } catch (error) {
        console.error('Load tools error:', error);
    }
}

function onMainStockChange() {
    const select = document.getElementById('main-stock-select');
    const qtyInput = document.getElementById('main-stock-qty');
    if (select && qtyInput) {
        const option = select.selectedOptions[0];
        if (option && option.value) {
            const max = parseInt(option.dataset.available) || 1;
            qtyInput.max = max;
            if (parseInt(qtyInput.value) > max) qtyInput.value = max;
        }
    }
    updateSelectedTools();
}

function onWorkshopStockChange() {
    const select = document.getElementById('workshop-stock-select');
    const qtyInput = document.getElementById('workshop-stock-qty');
    if (select && qtyInput) {
        const option = select.selectedOptions[0];
        if (option && option.value) {
            const max = parseInt(option.dataset.available) || 1;
            qtyInput.max = max;
            if (parseInt(qtyInput.value) > max) qtyInput.value = max;
        }
    }
    updateSelectedTools();
}

function updateSelectedTools() {
    selectedTools = [];
    
    // Основной склад
    const mainSelect = document.getElementById('main-stock-select');
    const mainQty = document.getElementById('main-stock-qty');
    if (mainSelect && mainSelect.value) {
        const option = mainSelect.selectedOptions[0];
        selectedTools.push({
            item_id: mainSelect.value,
            item_name: option ? option.text.split(' (')[0] : '',
            quantity: parseInt(mainQty ? mainQty.value : 1),
            source: 'main',
            source_name: 'Основной склад',
            equipment_id: null
        });
    }
    
    // Склад станков
    const workshopSelect = document.getElementById('workshop-stock-select');
    const workshopQty = document.getElementById('workshop-stock-qty');
    if (workshopSelect && workshopSelect.value) {
        const option = workshopSelect.selectedOptions[0];
        selectedTools.push({
            item_id: workshopSelect.value,
            item_name: option ? option.text.split(' (')[0] : '',
            quantity: parseInt(workshopQty ? workshopQty.value : 1),
            source: 'workshop',
            source_name: option ? option.dataset.sourceName : '',
            equipment_id: option ? option.dataset.equipmentId || null : null
        });
    }
}

async function takeOrderWithTools() {
    if (!selectedOrderId) {
        showMessage('Выберите заказ', 'warning');
        return;
    }
    
    if (selectedTools.length === 0) {
        showMessage('Выберите инструменты', 'warning');
        return;
    }
    
    try {
        const formData = new FormData();
        formData.append('order_id', selectedOrderId);
        formData.append('tools_json', JSON.stringify(selectedTools));
        
        const response = await fetch('/mobile/api/order/take-with-tools', {
            method: 'POST',
            body: formData,
        });
        
        const data = await response.json();
        
        if (data.success) {
            showMessage('✅ Заказ взят с инструментами', 'success');
            document.getElementById('tool-selector').style.display = 'none';
            selectedOrderId = null;
            selectedTools = [];
            loadAvailableOrders();
            loadWorkshopInventory();
        } else {
            showMessage(data.message || 'Ошибка', 'error');
        }
    } catch (error) {
        console.error('Take order error:', error);
        showMessage('Ошибка сети', 'error');
    }
}

// ======================== COMPLETE TOOLS DIALOG ========================

function showCompleteToolsDialog(orderId, tools) {
    const overlay = document.getElementById('dialog-overlay');
    const content = document.getElementById('dialog-content');
    
    if (!tools || tools.length === 0) {
        completeOrderSimple(orderId);
        return;
    }
    
    content.innerHTML = `
        <h3>Завершение работы</h3>
        <p style="color: #666; margin-bottom: 16px;">Выберите действие для каждого инструмента:</p>
        
        <div id="complete-tools-list">
            ${tools.map(tool => `
                <div class="dialog-tool" data-item-id="${tool.item_id}" data-source="${tool.source}">
                    <div style="flex: 1;">
                        <div style="font-weight: 500;">${tool.item_name}</div>
                        <div style="font-size: 12px; color: #666;">
                            ×${tool.quantity} | 
                            ${tool.source === 'workshop' ? '📍' : tool.source === 'main' ? '🏢' : '👤'}
                            ${tool.source_name}
                            ${tool.source === 'main' ? '<br><span style="color: #10b981;">↩️ При возврате: на склад станка</span>' : ''}
                        </div>
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 8px;">
                        <button class="btn-action btn-writeoff" onclick="completeToolAction('${tool.item_id}', ${tool.quantity}, 'writeoff')">
                            🗑 Списать
                        </button>
                        <button class="btn-action btn-return" onclick="completeToolAction('${tool.item_id}', ${tool.quantity}, 'return')">
                            ↩️ Вернуть
                        </button>
                    </div>
                </div>
            `).join('')}
        </div>
        
        <button class="btn-primary" style="margin-top: 16px;" onclick="submitCompleteTools(${orderId})">
            Завершить
        </button>
        <button class="btn-close" onclick="closeDialog()">Отмена</button>
    `;
    
    overlay.style.display = 'flex';
}

let completeToolsActions = {};

function completeToolAction(itemId, quantity, action) {
    completeToolsActions[itemId] = { quantity, action };
}

async function submitCompleteTools(orderId) {
    const tools = Object.entries(completeToolsActions).map(([item_id, data]) => ({
        item_id,
        ...data
    }));
    
    try {
        const formData = new FormData();
        formData.append('order_id', orderId);
        formData.append('tools_json', JSON.stringify(tools));
        
        const response = await fetch('/mobile/api/order/complete-with-tools', {
            method: 'POST',
            body: formData,
        });
        
        const data = await response.json();
        
        if (data.success) {
            showMessage('✅ Завершено', 'success');
            closeDialog();
            completeToolsActions = {};
        } else {
            showMessage(data.message || 'Ошибка', 'error');
        }
    } catch (error) {
        console.error('Complete error:', error);
        showMessage('Ошибка сети', 'error');
    }
}

async function completeOrderSimple(orderId) {
    try {
        const formData = new FormData();
        formData.append('order_id', orderId);
        
        const response = await fetch('/mobile/api/order/complete-with-tools', {
            method: 'POST',
            body: formData,
        });
        
        const data = await response.json();
        
        if (data.success) {
            showMessage('✅ Завершено', 'success');
        } else {
            showMessage(data.message || 'Ошибка', 'error');
        }
    } catch (error) {
        console.error('Complete error:', error);
        showMessage('Ошибка сети', 'error');
    }
}

// Перемещение инструмента на склад станка со страницы ЭМК
async function moveToolToWorkshop(itemId, quantity) {
    if (!confirm(`Переместить инструмент на склад станка (${quantity} шт)?`)) return;
    
    try {
        const formData = new FormData();
        formData.append('item_id', itemId);
        formData.append('quantity', quantity);
        
        const response = await fetch('/mobile/api/move-tool-to-workshop', {
            method: 'POST',
            body: formData,
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert('✅ Инструмент перемещен на склад станка');
            location.reload();
        } else {
            alert('Ошибка: ' + (data.message || 'Неизвестная'));
        }
    } catch (error) {
        alert('Ошибка сети: ' + error.message);
    }
}

// ======================== MOVE ITEM TO WORKSHOP ========================

// Получить список станков пользователя
function getUserWorkstations() {
    const ws = currentUser.workstations;
    if (!ws) return [];
    
    // Если это строка (JSON), парсим
    if (typeof ws === 'string') {
        try {
            return JSON.parse(ws);
        } catch {
            return ws.includes('[') ? [] : [ws];
        }
    }
    // Если это массив
    if (Array.isArray(ws)) {
        return ws;
    }
    return [];
}

function showMoveToWorkshopDialog(itemCode, itemName, quantity) {
    const overlay = document.getElementById('dialog-overlay');
    const content = document.getElementById('dialog-content');
    
    const workstations = getUserWorkstations();
    const hasMultipleWorkshops = workstations && workstations.length > 1;
    
    let workshopOptions = '';
    if (hasMultipleWorkshops) {
        workshopOptions = `
            <div class="form-group">
                <label>Выберите станок:</label>
                <select id="move-workshop" class="form-control">
                    ${workstations.map(ws => `<option value="${escapeHtml(ws)}">${escapeHtml(ws)}</option>`).join('')}
                </select>
            </div>
        `;
    }
    
    content.innerHTML = `
        <h3>Перемещение на склад станка</h3>
        <div class="dialog-info">
            <div><strong>${escapeHtml(itemName)}</strong></div>
            <div>Доступно: ${quantity} шт</div>
        </div>
        ${workshopOptions}
        <div class="form-group">
            <label>Количество для перемещения</label>
            <input type="number" id="move-quantity" value="${quantity}" min="1" max="${quantity}">
        </div>
        <div class="dialog-buttons">
            <button class="btn-primary" onclick="moveItemToWorkshop('${itemCode}', ${quantity})">
                🏭 Переместить
            </button>
        </div>
        <button class="btn-close" onclick="closeDialog()">Отмена</button>
    `;
    
    overlay.style.display = 'flex';
}

async function moveItemToWorkshop(itemCode, maxQuantity) {
    const qtyInput = document.getElementById('move-quantity');
    const quantity = parseInt(qtyInput?.value) || maxQuantity;
    const workshopSelect = document.getElementById('move-workshop');
    const selectedWorkshop = workshopSelect ? workshopSelect.value : null;
    
    if (quantity < 1 || quantity > maxQuantity) {
        showMessage('Укажите корректное количество', 'warning');
        return;
    }
    
    closeDialog();
    
    try {
        const formData = new FormData();
        formData.append('item_id', itemCode);
        formData.append('quantity', quantity);
        if (selectedWorkshop) {
            formData.append('equipment_name', selectedWorkshop);
        }
        
        const response = await fetch('/mobile/api/move-tool-to-workshop', {
            method: 'POST',
            body: formData,
        });
        
        const data = await response.json();
        
        if (data.success) {
            showMessage('✅ Инструмент перемещен на склад станка', 'success');
            loadWorkshopInventory();
        } else {
            showMessage('Ошибка: ' + (data.message || 'Неизвестная'), 'error');
        }
    } catch (error) {
        showMessage('Ошибка сети: ' + error.message, 'error');
    }
}

// ======================== ORDERS IN WORK ========================

async function loadOrdersInWork() {
    try {
        const response = await fetch('/mobile/api/orders-in-work');
        const data = await response.json();
        
        const container = document.getElementById('orders-in-work');
        
        if (data.success && data.orders && data.orders.length > 0) {
            container.innerHTML = data.orders.map(order => `
                <div class="card">
                    <div class="card-title">Заказ #${order.id}</div>
                    <div class="card-subtitle">
                        ${order.product_name || '—'}
                    </div>
                    <div class="card-subtitle">
                        ${order.tool_names ? '🔧 ' + order.tool_names : ''}
                    </div>
                    <div class="card-row">
                        <span class="status-badge status-in-progress">В работе</span>
                        <button class="btn-complete" onclick="showCompleteDialog(${order.id})">
                            Завершить
                        </button>
                    </div>
                </div>
            `).join('');
        } else {
            container.innerHTML = '<div class="empty-state">Нет заказов в работе</div>';
        }
    } catch (error) {
        console.error('Load orders in work error:', error);
        document.getElementById('orders-in-work').innerHTML = '<div class="empty-state">Ошибка загрузки</div>';
    }
}

function showCompleteDialog(orderId) {
    const overlay = document.getElementById('dialog-overlay');
    const content = document.getElementById('dialog-content');
    
    content.innerHTML = `
        <h3>Завершить заказ #${orderId}?</h3>
        <div class="dialog-buttons">
            <button class="btn-primary" onclick="completeOrder(${orderId})">
                Завершить
            </button>
        </div>
        <button class="btn-close" onclick="closeDialog()">Отмена</button>
    `;
    
    overlay.style.display = 'flex';
}

async function completeOrder(orderId) {
    closeDialog();
    
    try {
        const formData = new FormData();
        formData.append('order_id', orderId);
        
        const response = await fetch('/mobile/api/order/complete', {
            method: 'POST',
            body: formData,
        });
        
        const data = await response.json();
        
        if (data.success) {
            showMessage('✅ Заказ завершён', 'success');
            loadOrdersInWork();
            loadAvailableOrders();
        } else {
            showMessage(data.message || 'Ошибка', 'error');
        }
    } catch (error) {
        showMessage('Ошибка сети', 'error');
    }
}
