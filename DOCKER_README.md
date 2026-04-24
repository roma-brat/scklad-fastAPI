# Docker Deployment — Склад Инструментов

## Быстрый старт

### 1. Настройка

```bash
cd fastapi_app

# Создать .env.production из примера
cp .env.production.example .env.production

# Отредактировать .env.production — задать пароли:
nano .env.production
```

**Обязательно измените:**
- `DB_PASSWORD` — пароль к PostgreSQL
- `SECRET_KEY` — сгенерируйте: `openssl rand -hex 32`

### 2. Запуск

```bash
# Первый запуск (сборка + запуск)
./deploy.sh start

# Или напрямую через docker-compose:
docker-compose up -d
```

### 3. Проверка

```
http://localhost:8551
```

**Логин:** `admin`
**Пароль:** `admin_1234`

---

## Команды

| Команда | Описание |
|---------|----------|
| `./deploy.sh start` | Запуск (сборка + запуск) |
| `./deploy.sh stop` | Остановка |
| `./deploy.sh restart` | Перезапуск |
| `./deploy.sh build` | Пересборка образа |
| `./deploy.sh logs` | Логи приложения |
| `./deploy.sh status` | Статус всех сервисов |

---

## Структура

```
fastapi_app/
├── Dockerfile           # Образ контейнера
├── docker-compose.yml   # Конфигурация сервисов
├── .env.production      # Переменные (НЕ в git!)
├── .env.production.example  # Пример настроек
├── .dockerignore        # Исключения для сборки
├── deploy.sh            # Скрипт управления
└── ...
```

---

## Переменные окружения

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `DB_NAME` | `sklad_db` | Имя базы данных |
| `DB_USER` | `sklad_user` | Пользователь PostgreSQL |
| `DB_PASSWORD` | — | **Обязательно изменить!** |
| `APP_PORT` | `8551` | Порт приложения |
| `TIMEZONE` | `Europe/Moscow` | Часовой пояс |
| `SECRET_KEY` | — | **Обязательно изменить!** |
| `LOG_LEVEL` | `INFO` | Уровень логирования |

---

## Деплой на сервер

### 1. Установить Docker

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
```

### 2. Скопировать проект

```bash
# Вариант A: Git
cd /opt
git clone <repo> sklad
cd sklad/fastapi_app

# Вариант B: rsync
rsync -avz --exclude 'node_modules' --exclude '.git' \
    ./fastapi_app/ user@server:/opt/sklad/fastapi_app/
```

### 3. Настроить и запустить

```bash
cd /opt/sklad/fastapi_app
cp .env.production.example .env.production
nano .env.production  # задать пароли
./deploy.sh start
```

---

## Обновление

```bash
cd /opt/sklad/fastapi_app

# Обновить код из Git
git pull

# Пересобрать и перезапустить
docker-compose down
docker-compose up -d --build
```

---

## Бэкап базы данных

```bash
# Бэкап
docker-compose exec db pg_dump -U sklad_user sklad_db > backup_$(date +%Y%m%d).sql

# Восстановление
cat backup_20240424.sql | docker-compose exec -T db psql -U sklad_user sklad_db
```

---

## Остановка и удаление

```bash
# Остановка (данные сохранятся)
docker-compose down

# Остановка с удалением данных
docker-compose down -v

# Полное удаление
docker-compose down -v --rmi all
```
