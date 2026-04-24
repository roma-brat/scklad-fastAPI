# Склад Инструментов — FastAPI

## Быстрый старт

### 1. Скачать проект с GitHub

```bash
cd /opt
git clone https://github.com/roma-brat/scklad-fastAPI.git sklad
cd sklad
```

### 2. Настроить переменные окружения

```bash
cp .env.production.example .env.production
nano .env.production
```

**Обязательно изменить:**
```env
DB_PASSWORD=ТУТ_СВОЙ_ПАРОЛЬ
SECRET_KEY=ТУТ_СВОЙ_КЛЮЧ
```

**Генерация SECRET_KEY:**
```bash
openssl rand -hex 32
```

### 3. Запустить

```bash
# Первый запуск (сборка + запуск)
docker-compose up -d --build

# Проверить
curl http://localhost:8551/health
```

### 4. Восстановить базу данных (если есть бэкап)

```bash
docker-compose exec -T db psql -U sklad_user sklad_db < sklad_backup.sql
```

---

## Команды управления

```bash
# Войти в папку проекта
cd /opt/sklad

# Запуск
docker-compose up -d

# Остановка
docker-compose down

# Перезапуск
docker-compose restart

# Логи
docker-compose logs -f app

# Статус
docker-compose ps
```

---

## Обновление проекта

```bash
cd /opt/sklad
git pull origin main
docker-compose down
docker-compose up -d --build
```

---

## Доступ к приложению

- **URL:** http://localhost:8551 (или http://ваш-ip:8551)
- **Логин:** admin
- **Пароль:** admin_1234

---

## Структура файлов

```
sklad/
├── Dockerfile              # Образ контейнера
├── docker-compose.yml      # Конфигурация сервисов
├── .env.production        # Переменные окружения (НЕ в git!)
├── deploy.sh              # Скрипт управления
├── sklad_backup.sql       # Бэкап базы данных
├── main.py                # Точка входа FastAPI
├── config.py              # Конфигурация
├── requirements.txt       # Python зависимости
├── api/                   # API роуты
├── services/              # Бизнес-логика
├── templates/             # HTML шаблоны
└── static/                # CSS, JS
```

---

## Решение проблем

### Контейнер не запускается
```bash
docker-compose logs app --tail=50
```

### Ошибка подключения к БД
```bash
docker-compose logs db --tail=50
docker-compose exec db psql -U sklad_user -d sklad_db -c "\dt"
```

### Полный сброс
```bash
docker-compose down -v
docker-compose up -d --build
```

---

## Переменные окружения (.env.production)

| Переменная | По умолчанию | Описание |
|-----------|--------------|---------|
| `DB_NAME` | sklad_db | Имя базы данных |
| `DB_USER` | sklad_user | Пользователь PostgreSQL |
| `DB_PASSWORD` | — | **Обязательно!** Пароль БД |
| `APP_PORT` | 8551 | Порт приложения |
| `SECRET_KEY` | — | **Обязательно!** Сессия |
| `TIMEZONE` | Europe/Moscow | Часовой пояс |
