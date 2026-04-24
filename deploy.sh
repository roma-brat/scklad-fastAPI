#!/bin/bash
# ============================================
# deploy.sh — Управление Docker деплоем
# ============================================
# Использование:
#   ./deploy.sh start   — Первый запуск / запуск
#   ./deploy.sh stop    — Остановка
#   ./deploy.sh restart — Перезапуск
#   ./deploy.sh logs    — Просмотр логов
#   ./deploy.sh status  — Статус сервисов
#   ./deploy.sh build   — Пересборка образа
# ============================================

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# Цвета
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Загрузка .env.production если есть
load_env() {
    if [ -f .env.production ]; then
        set -a
        source .env.production
        set +a
    fi
}

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Проверка .env.production
check_env() {
    if [ ! -f .env.production ]; then
        log_warn ".env.production не найден"
        log_info "Создайте из примера: cp .env.production.example .env.production"
        return 1
    fi
    return 0
}

# Запуск
start() {
    log_info "Запуск Склад Инструментов..."

    if ! check_env; then
        log_error "Не могу продолжить"
        exit 1
    fi

    load_env

    # Сборка (если нужно) и запуск
    docker-compose up -d --build

    # Ожидание запуска
    sleep 3

    # Проверка
    if curl -sf http://localhost:${APP_PORT:-8551}/health > /dev/null 2>&1; then
        log_info "✅ Приложение запущено!"
        log_info "📍 http://localhost:${APP_PORT:-8551}"
        log_info "📚 Swagger: http://localhost:${APP_PORT:-8551}/docs"
    else
        log_error "Приложение не отвечает. Проверьте логи:"
        docker-compose logs app --tail=50
    fi
}

# Остановка
stop() {
    log_info "Остановка..."
    docker-compose down
    log_info "✅ Остановлено"
}

# Перезапуск
restart() {
    stop
    start
}

# Логи
logs() {
    docker-compose logs -f --tail="${1:-100}" app
}

# Статус
status() {
    echo ""
    echo "=========================================="
    echo "         СКЛАД ИНСТРУМЕНТОВ"
    echo "=========================================="
    echo ""
    docker-compose ps
    echo ""

    if curl -sf http://localhost:${APP_PORT:-8551}/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Приложение: РАБОТАЕТ${NC}"
    else
        echo -e "${RED}❌ Приложение: НЕ ОТВЕЧАЕТ${NC}"
    fi
    echo ""
}

# Сборка
build() {
    log_info "Сборка Docker образа..."
    docker-compose build --pull
    log_info "✅ Готово"
}

# Help
help() {
    echo ""
    echo "=========================================="
    echo "    СКЛАД ИНСТРУМЕНТОВ — DEPLOY"
    echo "=========================================="
    echo ""
    echo "Использование: ./deploy.sh [command]"
    echo ""
    echo "Команды:"
    echo "  start    — Запуск (сборка + запуск)"
    echo "  stop     — Остановка"
    echo "  restart  — Перезапуск"
    echo "  build    — Только сборка"
    echo "  logs     — Логи (tail -100)"
    echo "  status   — Статус сервисов"
    echo "  help     — Эта справка"
    echo ""
}

# Главная логика
case "${1:-help}" in
    start)   start ;;
    stop)    stop ;;
    restart) restart ;;
    build)   build ;;
    logs)    logs "$@" ;;
    status)  status ;;
    help|*)  help ;;
esac
