/**
 * Planning API JavaScript helpers
 * Functions for calling planning APIs, calendar interactions,
 * filter handlers, modal dialogs, and progress updates.
 */

// ==================== API HELPERS ====================

/**
 * Generic API call helper
 */
async function planningApiCall(url, options = {}) {
    const defaults = {
        headers: { 'Content-Type': 'application/json' },
    };
    const response = await fetch(url, { ...defaults, ...options });
    if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    return response.json();
}

/**
 * Get production schedule with filters
 */
async function getSchedule(filters = {}) {
    const params = new URLSearchParams();
    if (filters.date_from) params.set('date_from', filters.date_from);
    if (filters.date_to) params.set('date_to', filters.date_to);
    if (filters.equipment_id) params.set('equipment_id', filters.equipment_id);
    if (filters.order_id) params.set('order_id', filters.order_id);
    if (filters.status) params.set('status', filters.status);

    return planningApiCall(`/planning/api/schedule?${params}`);
}

/**
 * Calculate schedule for all unplanned orders
 */
async function calculateAllUnplanned() {
    return planningApiCall('/planning/api/calculate-all', { method: 'POST' });
}

/**
 * Update a schedule item
 */
async function updateScheduleItem(scheduleId, data) {
    return planningApiCall(`/planning/api/schedule/${scheduleId}`, {
        method: 'PUT',
        body: JSON.stringify(data),
    });
}

/**
 * Delete a schedule item
 */
async function deleteScheduleItem(scheduleId) {
    return planningApiCall(`/planning/api/schedule/${scheduleId}`, {
        method: 'DELETE',
    });
}

/**
 * Mark schedule item as taken
 */
async function takeScheduleItem(scheduleId) {
    return planningApiCall(`/planning/api/schedule/${scheduleId}/take`, {
        method: 'POST',
    });
}

/**
 * Mark schedule item as completed
 */
async function completeScheduleItem(scheduleId) {
    return planningApiCall(`/planning/api/schedule/${scheduleId}/complete`, {
        method: 'POST',
    });
}

/**
 * Get equipment calendar
 */
async function getEquipmentCalendar(equipmentId = null, dateFrom = null, dateTo = null) {
    const url = equipmentId
        ? `/planning/api/equipment-calendar/${equipmentId}?date_from=${dateFrom || ''}&date_to=${dateTo || ''}`
        : `/planning/api/equipment-calendar?date_from=${dateFrom || ''}&date_to=${dateTo || ''}`;
    return planningApiCall(url);
}

/**
 * Set equipment working/non-working day
 */
async function setEquipmentDay(equipmentId, date, isWorking, workingHours = 8) {
    return planningApiCall(`/planning/api/equipment-calendar/${equipmentId}/day`, {
        method: 'POST',
        body: JSON.stringify({ date, is_working: isWorking, working_hours: workingHours }),
    });
}

/**
 * Get equipment load
 */
async function getEquipmentLoad(dateFrom = null, dateTo = null) {
    const url = `/planning/api/equipment-load?date_from=${dateFrom || ''}&date_to=${dateTo || ''}`;
    return planningApiCall(url);
}

/**
 * Get all orders with planning status
 */
async function getPlanningOrders() {
    return planningApiCall('/planning/api/orders');
}

/**
 * Get single order with its schedule
 */
async function getPlanningOrder(orderId) {
    return planningApiCall(`/planning/api/orders/${orderId}`);
}

/**
 * Update order priority
 */
async function updateOrderPriority(orderId, priority) {
    return planningApiCall(`/planning/api/orders/${orderId}/priority`, {
        method: 'PUT',
        body: JSON.stringify({ priority }),
    });
}

/**
 * Clear order schedule
 */
async function clearOrderSchedule(orderId) {
    return planningApiCall(`/planning/api/orders/${orderId}/clear-schedule`, {
        method: 'POST',
    });
}

/**
 * Get user's calendar config
 */
async function getCalendarConfig() {
    return planningApiCall('/planning/api/calendar-config');
}

/**
 * Save user's calendar config
 */
async function saveCalendarConfig(visibleEquipment, equipmentOrder, panelVisible = true) {
    return planningApiCall('/planning/api/calendar-config', {
        method: 'POST',
        body: JSON.stringify({
            visible_equipment: visibleEquipment,
            equipment_order: equipmentOrder,
            panel_visible: panelVisible,
        }),
    });
}


// ==================== TOAST NOTIFICATIONS ====================

/**
 * Show toast notification
 */
function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    const toastMessage = document.getElementById('toast-message');
    if (!toast || !toastMessage) {
        console.log(message);
        return;
    }
    toastMessage.textContent = message;
    toast.className = `fixed bottom-4 right-4 px-6 py-3 rounded-lg shadow-lg transform transition-transform duration-300 z-50 ${type === 'error' ? 'bg-red-600' : 'bg-green-600'}`;
    toast.classList.remove('translate-y-full');
    toast.classList.add('translate-y-0');
    setTimeout(() => {
        toast.classList.remove('translate-y-0');
        toast.classList.add('translate-y-full');
    }, 3000);
}


// ==================== CALENDAR INTERACTIONS ====================

/**
 * Initialize calendar drag-and-drop
 */
function initCalendarDragAndDrop() {
    const chips = document.querySelectorAll('.operation-chip[data-draggable="true"]');
    const cells = document.querySelectorAll('.calendar-day-cell');

    chips.forEach(chip => {
        chip.setAttribute('draggable', 'true');
        chip.addEventListener('dragstart', handleDragStart);
        chip.addEventListener('dragend', handleDragEnd);
    });

    cells.forEach(cell => {
        cell.addEventListener('dragover', handleDragOver);
        cell.addEventListener('dragenter', handleDragEnter);
        cell.addEventListener('dragleave', handleDragLeave);
        cell.addEventListener('drop', handleDrop);
    });
}

let draggedItem = null;

function handleDragStart(e) {
    draggedItem = this;
    this.style.opacity = '0.4';
    e.dataTransfer.setData('text/plain', JSON.stringify({
        scheduleId: this.dataset.scheduleId,
        equipmentId: this.dataset.equipmentId,
        date: this.dataset.date,
    }));
}

function handleDragEnd(e) {
    this.style.opacity = '1';
    draggedItem = null;
    document.querySelectorAll('.calendar-day-cell').forEach(cell => {
        cell.classList.remove('drag-over');
    });
}

function handleDragOver(e) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
}

function handleDragEnter(e) {
    e.preventDefault();
    this.classList.add('drag-over');
}

function handleDragLeave(e) {
    this.classList.remove('drag-over');
}

async function handleDrop(e) {
    e.preventDefault();
    this.classList.remove('drag-over');

    try {
        const data = JSON.parse(e.dataTransfer.getData('text/plain'));
        const newEquipmentId = parseInt(this.dataset.equipmentId);
        const newDate = this.dataset.date;

        const result = await updateScheduleItem(data.scheduleId, {
            equipment_id: newEquipmentId,
            planned_date: newDate,
        });

        if (result.success) {
            showToast('Операция перемещена');
            setTimeout(() => location.reload(), 500);
        } else {
            showToast('Ошибка перемещения', 'error');
        }
    } catch (err) {
        showToast('Ошибка: ' + err.message, 'error');
    }
}


// ==================== FILTER HANDLERS ====================

/**
 * Filter orders by status and search term
 */
function filterOrders() {
    const statusFilter = document.getElementById('status-filter');
    const searchInput = document.getElementById('search-orders');
    if (!statusFilter || !searchInput) return;

    const status = statusFilter.value;
    const search = searchInput.value.toLowerCase();
    const cards = document.querySelectorAll('.order-card');

    cards.forEach(card => {
        const cardStatus = card.dataset.status;
        const detailName = card.dataset.detailName || '';
        const designation = card.dataset.designation || '';
        const matchesStatus = status === 'all' || cardStatus === status;
        const matchesSearch = !search || detailName.includes(search) || designation.includes(search);
        card.style.display = (matchesStatus && matchesSearch) ? '' : 'none';
    });
}

/**
 * Filter calendar by equipment
 */
function filterCalendarByEquipment(visibleEquipmentIds) {
    const rows = document.querySelectorAll('.calendar-grid > .calendar-equipment-cell');
    rows.forEach(cell => {
        const eqId = parseInt(cell.dataset.equipmentId || cell.querySelector('.equip-toggle')?.dataset.equipmentId);
        if (eqId && visibleEquipmentIds.length > 0) {
            const isVisible = visibleEquipmentIds.includes(eqId);
            cell.style.display = isVisible ? '' : 'none';
            // Hide corresponding day cells
            const nextElement = cell.nextElementSibling;
            if (nextElement) {
                for (let i = 0; i < 31; i++) {
                    const dayCell = nextElement.parentElement?.children[
                        Array.from(nextElement.parentElement.children).indexOf(cell) + 1 + i
                    ];
                    if (dayCell && !dayCell.classList.contains('calendar-equipment-cell') && !dayCell.classList.contains('calendar-header-cell')) {
                        dayCell.style.display = isVisible ? '' : 'none';
                    } else {
                        break;
                    }
                }
            }
        }
    });
}

/**
 * Filter calendar by detail
 */
function filterCalendarByDetail(designation, detailName, batchNumber) {
    const chips = document.querySelectorAll('.operation-chip');
    chips.forEach(chip => {
        const title = chip.getAttribute('title') || '';
        const matches = !designation ||
            title.includes(designation) ||
            title.includes(detailName);
        chip.style.display = matches ? '' : 'none';
    });
}


// ==================== VIEW MODE SWITCHING ====================

/**
 * Switch calendar view mode (month/week)
 */
function setCalendarViewMode(mode) {
    const monthBtn = document.getElementById('view-month');
    const weekBtn = document.getElementById('view-week');
    if (!monthBtn || !weekBtn) return;

    if (mode === 'month') {
        monthBtn.className = 'px-3 py-2 text-sm bg-blue-600 text-white';
        weekBtn.className = 'px-3 py-2 text-sm bg-white text-gray-700 hover:bg-gray-50';
    } else if (mode === 'week') {
        weekBtn.className = 'px-3 py-2 text-sm bg-blue-600 text-white';
        monthBtn.className = 'px-3 py-2 text-sm bg-white text-gray-700 hover:bg-gray-50';
    }
}


// ==================== MODAL DIALOG HANDLERS ====================

/**
 * Open edit dialog for a schedule item
 */
async function openEditScheduleDialog(scheduleId) {
    try {
        // Get schedule data
        const data = await getSchedule();
        const item = data.schedule.find(s => s.id === scheduleId);
        if (!item) {
            showToast('Операция не найдена', 'error');
            return;
        }

        // Populate dialog fields
        const dialog = document.getElementById('edit-dialog');
        if (!dialog) return;

        document.getElementById('edit-schedule-id').value = scheduleId;
        document.getElementById('edit-date').value = item.planned_date ? item.planned_date.substring(0, 10) : '';
        document.getElementById('edit-equipment').value = item.equipment_id || '';
        document.getElementById('edit-status').value = item.status || 'planned';
        document.getElementById('edit-notes').value = item.notes || '';

        // Show/hide action buttons based on status
        const takeBtn = document.getElementById('btn-take');
        const completeBtn = document.getElementById('btn-complete');
        if (takeBtn) takeBtn.style.display = item.status === 'planned' ? '' : 'none';
        if (completeBtn) completeBtn.style.display = (item.status === 'planned' || item.status === 'in_progress') ? '' : 'none';

        dialog.classList.remove('hidden');
    } catch (err) {
        showToast('Ошибка загрузки: ' + err.message, 'error');
    }
}

/**
 * Close edit dialog
 */
function closeEditScheduleDialog() {
    const dialog = document.getElementById('edit-dialog');
    if (dialog) dialog.classList.add('hidden');
}

/**
 * Save edited schedule item
 */
async function saveEditedSchedule() {
    const id = document.getElementById('edit-schedule-id').value;
    const body = {
        planned_date: document.getElementById('edit-date').value,
        equipment_id: parseInt(document.getElementById('edit-equipment').value),
        status: document.getElementById('edit-status').value,
        notes: document.getElementById('edit-notes').value,
    };

    try {
        const result = await updateScheduleItem(id, body);
        if (result.success) {
            showToast('Операция обновлена');
            closeEditScheduleDialog();
            setTimeout(() => location.reload(), 500);
        } else {
            showToast('Ошибка: ' + (result.message || 'Неизвестная'), 'error');
        }
    } catch (err) {
        showToast('Ошибка сети: ' + err.message, 'error');
    }
}

/**
 * Delete schedule item from edit dialog
 */
async function deleteFromEditDialog() {
    if (!confirm('Удалить эту операцию из расписания?')) return;
    const id = document.getElementById('edit-schedule-id').value;

    try {
        const result = await deleteScheduleItem(id);
        if (result.success) {
            showToast('Операция удалена');
            closeEditScheduleDialog();
            setTimeout(() => location.reload(), 500);
        }
    } catch (err) {
        showToast('Ошибка: ' + err.message, 'error');
    }
}

/**
 * Take operation into work
 */
async function takeOperationIntoWork() {
    const id = document.getElementById('edit-schedule-id').value;
    try {
        const result = await takeScheduleItem(id);
        if (result.success) {
            showToast('Операция взята в работу');
            closeEditScheduleDialog();
            setTimeout(() => location.reload(), 500);
        }
    } catch (err) {
        showToast('Ошибка: ' + err.message, 'error');
    }
}

/**
 * Complete operation
 */
async function completeOperation() {
    const id = document.getElementById('edit-schedule-id').value;
    try {
        const result = await completeScheduleItem(id);
        if (result.success) {
            showToast('Операция завершена');
            closeEditScheduleDialog();
            setTimeout(() => location.reload(), 500);
        }
    } catch (err) {
        showToast('Ошибка: ' + err.message, 'error');
    }
}


// ==================== PROGRESS BAR UPDATES ====================

/**
 * Update progress bar for equipment
 */
function updateEquipmentProgress(equipmentId, percent) {
    const progressBar = document.querySelector(`.progress-fill[data-equipment-id="${equipmentId}"]`);
    const percentText = document.querySelector(`.progress-text[data-equipment-id="${equipmentId}"]`);

    if (progressBar) {
        progressBar.style.width = `${Math.min(percent, 100)}%`;
        progressBar.className = `progress-fill ${percent >= 80 ? 'bg-red-400' : percent >= 50 ? 'bg-orange-400' : 'bg-green-400'}`;
    }
    if (percentText) {
        percentText.textContent = `${percent.toFixed(1)}%`;
        percentText.className = `progress-text ${percent >= 80 ? 'text-red-600' : percent >= 50 ? 'text-orange-600' : 'text-green-600'}`;
    }
}

/**
 * Update all progress bars from equipment load data
 */
async function refreshAllProgress(dateFrom, dateTo) {
    try {
        const data = await getEquipmentLoad(dateFrom, dateTo);
        if (data.success && data.load) {
            data.load.forEach(item => {
                updateEquipmentProgress(item.equipment_id, item.utilization_percent);
            });
        }
    } catch (err) {
        console.error('Error refreshing progress:', err);
    }
}


// ==================== UTILITY FUNCTIONS ====================

/**
 * Format date for display
 */
function formatDate(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' });
}

/**
 * Get current month/year as URL params
 */
function getCurrentMonthParams() {
    const now = new Date();
    const urlParams = new URLSearchParams(window.location.search);
    return {
        year: parseInt(urlParams.get('year') || now.getFullYear()),
        month: parseInt(urlParams.get('month') || (now.getMonth() + 1)),
    };
}

/**
 * Navigate to current month
 */
function goToCurrentMonth() {
    const now = new Date();
    const baseUrl = window.location.pathname;
    window.location.href = `${baseUrl}?year=${now.getFullYear()}&month=${now.getMonth() + 1}`;
}

/**
 * Initialize equipment filter checkboxes
 */
function initEquipmentFilter() {
    const checkboxes = document.querySelectorAll('.equipment-checkbox');
    const filterCount = document.getElementById('filter-count');

    function updateCount() {
        const checked = document.querySelectorAll('.equipment-checkbox:checked').length;
        const total = checkboxes.length;
        if (filterCount) {
            filterCount.textContent = `${checked}/${total}`;
        }
    }

    checkboxes.forEach(cb => {
        cb.addEventListener('change', updateCount);
    });

    updateCount();
}

/**
 * Toggle all equipment in a group
 */
function toggleGroupCheckboxes(checkbox) {
    const group = checkbox.dataset.group;
    const checked = checkbox.checked;
    document.querySelectorAll(`.equipment-checkbox[data-group="${group}"]`).forEach(cb => {
        cb.checked = checked;
    });
}

/**
 * Show/hide all equipment checkboxes
 */
function showAllEquipment() {
    document.querySelectorAll('.equipment-checkbox, .group-checkbox').forEach(cb => {
        cb.checked = true;
    });
    updateFilterCount();
}

function hideAllEquipment() {
    document.querySelectorAll('.equipment-checkbox, .group-checkbox').forEach(cb => {
        cb.checked = false;
    });
    updateFilterCount();
}

/**
 * Save filter and reload calendar
 */
async function saveFilterAndClose() {
    const visibleEquipment = [...document.querySelectorAll('.equipment-checkbox:checked')]
        .map(cb => parseInt(cb.value));

    try {
        await saveCalendarConfig(visibleEquipment, [], true);
        showToast('Фильтр сохранён');
        const filterPanel = document.getElementById('filter-panel');
        if (filterPanel) filterPanel.classList.add('hidden');
        setTimeout(() => location.reload(), 500);
    } catch (err) {
        showToast('Ошибка: ' + err.message, 'error');
    }
}


// ==================== INITIALIZATION ====================

/**
 * Initialize all planning page functionality
 */
function initPlanningPage() {
    // Initialize equipment filter
    initEquipmentFilter();

    // Initialize drag and drop for calendar
    initCalendarDragAndDrop();
    
    // Initialize schedule dialog buttons
    initScheduleDialogButtons();

    // Add event listeners for keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        // Escape closes dialogs
        if (e.key === 'Escape') {
            closeEditScheduleDialog();
            const addDialog = document.getElementById('add-dialog');
            if (addDialog) addDialog.classList.add('hidden');
            const priorityModal = document.getElementById('priority-modal');
            if (priorityModal) priorityModal.classList.add('hidden');
            closeScheduleDialog();
        }
    });
}

// ==================== SCHEDULE DIALOG (ДОБАВИТЬ В ПЛАН) ====================

/**
 * Initialize event listeners for all action buttons
 */
function initScheduleDialogButtons() {
    // === Кнопки "Добавить в план" ===
    const addButtons = document.querySelectorAll('.btn-add-to-plan');
    
    addButtons.forEach((btn) => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            openScheduleDialogFromButton(this);
        });
    });
    
    // === Кнопки "Убрать из плана" ===
    const clearButtons = document.querySelectorAll('.btn-clear-schedule');
    
    clearButtons.forEach((btn) => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            const orderId = this.dataset.orderId;
            clearOrderScheduleInline(orderId, this);
        });
    });
    
    // === Кнопки "Удалить заказ" ===
    const deleteButtons = document.querySelectorAll('.btn-delete-order');
    
    deleteButtons.forEach((btn) => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            const orderId = this.dataset.orderId;
            deleteOrderInline(orderId, this);
        });
    });
}

/**
 * Open schedule dialog from button click
 */
function openScheduleDialogFromButton(button) {
    console.log('=== openScheduleDialogFromButton CALLED ===');
    
    const orderId = button.dataset.orderId;
    const detailName = button.dataset.detailName || 'Деталь';
    const productionType = button.dataset.productionType || 'piece';

    if (!orderId) {
        showToast('Ошибка: orderId не найден', 'error');
        return;
    }

    openScheduleDialog(orderId, detailName, productionType);
}

/**
 * Open schedule dialog
 */
function openScheduleDialog(orderId, detailName, productionType) {
    console.log('=== openScheduleDialog called ===');

    const orderIdField = document.getElementById('schedule-order-id');
    const productionTypeField = document.getElementById('schedule-production-type');
    const orderNameField = document.getElementById('schedule-order-name');
    const startDateField = document.getElementById('schedule-start-date');
    const urgentSection = document.getElementById('urgent-section');
    const batchInfo = document.getElementById('batch-info');
    const scheduleDialog = document.getElementById('schedule-dialog');

    if (!orderIdField || !productionTypeField || !orderNameField || !startDateField || !scheduleDialog) {
        console.error('One or more dialog elements not found!');
        showToast('Ошибка: диалог не найден', 'error');
        return;
    }

    orderIdField.value = orderId;
    productionTypeField.value = productionType;
    orderNameField.textContent = `Заказ: ${detailName}`;

    // Устанавливаем сегодняшнюю дату как значение по умолчанию
    const today = new Date().toISOString().split('T')[0];
    startDateField.value = today;
    
    // Устанавливаем минимальную дату (сегодня)
    startDateField.min = today;

    // Показываем/скрываем секцию срочности в зависимости от типа производства
    if (productionType === 'piece') {
        urgentSection.classList.remove('hidden');
        batchInfo.classList.add('hidden');
    } else {
        urgentSection.classList.add('hidden');
        batchInfo.classList.remove('hidden');
    }

    // Сбрасываем чекбокс
    const urgentCheckbox = document.getElementById('schedule-is-urgent');
    if (urgentCheckbox) {
        urgentCheckbox.checked = false;
    }

    // Показываем диалог
    scheduleDialog.classList.remove('hidden');
}

/**
 * Close schedule dialog
 */
function closeScheduleDialog() {
    const dialog = document.getElementById('schedule-dialog');
    if (dialog) {
        dialog.classList.add('hidden');
    }
}

/**
 * Execute schedule calculation
 */
async function executeSchedule() {
    const orderId = document.getElementById('schedule-order-id').value;
    const productionType = document.getElementById('schedule-production-type').value;
    const startDate = document.getElementById('schedule-start-date').value;
    const isUrgent = document.getElementById('schedule-is-urgent').checked;

    // Валидация
    if (!startDate) {
        showToast('Выберите дату начала производства', 'error');
        return;
    }

    // Определяем приоритет: 1 = срочный, 5 = обычный
    let priority = 5;
    if (isUrgent) {
        priority = 1; // Срочный заказ
    }

    console.log('executeSchedule:', { orderId, startDate, isUrgent, priority });

    // Закрываем диалог
    closeScheduleDialog();

    // ШАГ 1: Проверяем конфликты перед планированием
    showToast('🔍 Проверяю конфликты...');

    try {
        const conflictResponse = await fetch(`/planning/api/check-order-conflicts/${orderId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                start_date: startDate,
                priority: priority
            })
        });
        const conflictResult = await conflictResponse.json();

        if (!conflictResult.success) {
            showToast('Ошибка проверки: ' + (conflictResult.message || 'Неизвестная'), 'error');
            return;
        }

        // Если есть конфликты - показываем диалог выбора
        if (conflictResult.has_conflicts) {
            console.log('Обнаружены конфликты:', conflictResult.conflicts);
            showConflictDialog(conflictResult.conflicts, orderId, startDate, priority);
            return;
        }

        // Конфликтов нет - планируем сразу
        await performSchedulePlanning(orderId, startDate, priority);

    } catch (e) {
        showToast('Ошибка сети: ' + e.message, 'error');
    }
}

/**
 * Выполнить планирование (после проверки конфликтов)
 */
async function performSchedulePlanning(orderId, startDate, priority, equipmentOverrides = []) {
    showToast('⏳ Рассчитываю расписание...');

    try {
        const body = {
            start_date: startDate,
            priority: priority
        };

        // Если есть замены станков - передаём их
        if (equipmentOverrides.length > 0) {
            body.equipment_overrides = equipmentOverrides;
        }

        const response = await fetch(`/planning/api/calculate/${orderId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        const result = await response.json();

        if (result.success) {
            const shiftedMsg = result.shifted_orders > 0 ? ` (сдвинуто ${result.shifted_orders} заказов)` : '';
            const overridesMsg = equipmentOverrides.length > 0 ? ` (заменено станков: ${equipmentOverrides.length})` : '';
            showToast(`✅ Заказ добавлен в план${shiftedMsg}${overridesMsg}`);
            // Перезагружаем страницу через 500мс
            setTimeout(function() {
                window.location.reload();
            }, 500);
        } else {
            showToast(result.message || 'Ошибка расчёта', 'error');
        }
    } catch (e) {
        showToast('Ошибка сети: ' + e.message, 'error');
    }
}

/**
 * Показать диалог конфликтов и предложить выбор станка для каждой операции
 */
function showConflictDialog(conflicts, orderId, startDate, priority) {
    // Группируем конфликты по операции (sequence_number + equipment_id)
    const operationsMap = new Map();

    conflicts.forEach(c => {
        const opKey = `${c.operation_sequence}-${c.equipment_id}`;
        if (!operationsMap.has(opKey)) {
            operationsMap.set(opKey, {
                seq: c.operation_sequence,
                opName: c.operation_name,
                equipmentId: c.equipment_id,
                equipmentName: c.equipment_name,
                operationTypeId: c.operation_type_id,
                conflictDates: [],
                busyOrders: []
            });
        }
        const op = operationsMap.get(opKey);
        op.conflictDates.push(c.conflict_date);
        op.busyOrders.push({
            orderId: c.busy_order_id,
            designation: c.busy_order_designation,
            detail: c.busy_order_detail,
            date: c.conflict_date,
            equipmentName: c.busy_equipment_name
        });
        if (c.alternative_equipment) {
            op.alternativeEquipment = c.alternative_equipment;
        }
    });

    const operationsList = document.getElementById('conflict-operations-list');
    if (!operationsList) {
        console.error('conflict-operations-list not found!');
        return;
    }

    // Очищаем список
    operationsList.innerHTML = '';

    const template = document.getElementById('conflict-row-template');

    // Для каждой операции создаём строку
    operationsMap.forEach((op, key) => {
        const clone = template.content.cloneNode(true);

        // Заполняем данные операции
        clone.querySelector('.conflict-seq').textContent = `Операция ${op.seq}`;
        clone.querySelector('.conflict-op-name').textContent = op.opName;

        // Форматируем информацию о конфликтах
        const uniqueDates = [...new Set(op.conflictDates)].map(d => d.slice(0, 10)).join(', ');
        clone.querySelector('.conflict-info').textContent =
            `Текущий станок: ${op.equipmentName} | Даты: ${uniqueDates}`;

        // Показываем с кем конфликт
        const uniqueBusyOrders = [...new Set(op.busyOrders.map(b => `#${b.orderId}`))].join(', ');
        clone.querySelector('.conflict-with').innerHTML =
            `<i class="fas fa-exclamation-circle mr-1"></i>Занято заказами: ${uniqueBusyOrders}`;

        // Заполняем dropdown станков
        const select = clone.querySelector('.conflict-equipment-select');
        const note = clone.querySelector('.conflict-equipment-note');

        // Опция "Оставить текущий"
        const defaultOption = document.createElement('option');
        defaultOption.value = '';
        defaultOption.textContent = `${op.equipmentName} (найти свободные дни)`;
        select.appendChild(defaultOption);

        // Альтернативные станки
        if (op.alternativeEquipment && op.alternativeEquipment.length > 0) {
            const sepOption = document.createElement('option');
            sepOption.disabled = true;
            sepOption.textContent = '── Альтернативные ──';
            select.appendChild(sepOption);

            op.alternativeEquipment.forEach(alt => {
                const opt = document.createElement('option');
                opt.value = alt.id;
                opt.textContent = `${alt.name}${alt.inventory_number ? ' (' + alt.inventory_number + ')' : ''}`;
                select.appendChild(opt);
            });
        } else {
            note.textContent = 'Альтернативные станки не найдены';
        }

        // Сохраняем данные операции в select для последующего использования
        select.dataset.opKey = key;
        select.dataset.operationSeq = op.seq;
        select.dataset.operationTypeId = op.operationTypeId || '';
        select.dataset.currentEquipmentId = op.equipmentId;

        operationsList.appendChild(clone);
    });

    // Сохраняем данные для последующего использования
    window._conflictData = {
        orderId,
        startDate,
        priority,
        conflicts,
        operationsMap: Array.from(operationsMap.values())
    };

    // Показываем диалог
    const conflictDialog = document.getElementById('conflict-dialog');
    if (conflictDialog) {
        conflictDialog.classList.remove('hidden');
    }
}

/**
 * Закрыть диалог конфликтов
 */
function closeConflictDialog() {
    const dialog = document.getElementById('conflict-dialog');
    if (dialog) {
        dialog.classList.add('hidden');
    }
}

/**
 * Продолжить планирование без замены станков (автосдвиг дат)
 */
async function planWithoutReplacement() {
    const conflictData = window._conflictData;
    if (!conflictData) {
        showToast('Данные конфликтов не найдены', 'error');
        return;
    }

    closeConflictDialog();
    showToast('⏳ Планирую с учётом занятости (автосдвиг дат)...');

    // Передаём пустой список equipment_overrides — планировщик сам найдёт свободные дни
    await performSchedulePlanning(
        conflictData.orderId,
        conflictData.startDate,
        conflictData.priority,
        []  // Нет замен станков
    );
}

/**
 * Разрешить конфликт и продолжить планирование
 */
async function resolveConflictAndSave() {
    const conflictData = window._conflictData;
    if (!conflictData) {
        showToast('Данные конфликтов не найдены', 'error');
        return;
    }

    // Собираем выбранные станки из всех dropdown
    const equipmentOverrides = [];
    const selects = document.querySelectorAll('.conflict-equipment-select');

    selects.forEach((select, idx) => {
        const operationSeq = select.dataset.operationSeq;
        const currentEquipmentId = select.dataset.currentEquipmentId;
        const selectedEquipmentId = select.value;

        if (selectedEquipmentId && operationSeq && currentEquipmentId) {
            equipmentOverrides.push({
                operationSeq: parseInt(operationSeq),
                currentEquipmentId: parseInt(currentEquipmentId),
                newEquipmentId: parseInt(selectedEquipmentId),
                equipmentName: select.options[select.selectedIndex].text
            });
        }
    });

    closeConflictDialog();

    if (equipmentOverrides.length > 0) {
        showToast(`⚙️ Планирую с альтернативными станками...`);

        // Передаём overrides напрямую в планировщик - он использует их без изменения маршрута
        await performSchedulePlanning(
            conflictData.orderId,
            conflictData.startDate,
            conflictData.priority,
            equipmentOverrides  // Передаём замены станков
        );
    } else {
        showToast('⏳ Планирую с учётом занятости (сдвиг дат)...');

        // Передаём пустой список equipment_overrides — планировщик сам найдёт свободные дни
        await performSchedulePlanning(
            conflictData.orderId,
            conflictData.startDate,
            conflictData.priority,
            []  // Нет замен станков
        );
    }
}

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initPlanningPage);
} else {
    initPlanningPage();
}
