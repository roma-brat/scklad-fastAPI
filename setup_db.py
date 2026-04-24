#!/usr/bin/env python3
"""
Скрипт инициализации базы данных PostgreSQL
"""
import subprocess
import sys
import getpass

def run_psql_command(command, user=None):
    """Выполнить SQL команду через psql"""
    psql_user = user or getpass.getuser()
    try:
        result = subprocess.run(
            ['psql', '-U', psql_user, '-c', command],
            capture_output=True,
            text=True,
            check=True
        )
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr

def check_postgresql():
    """Проверить что PostgreSQL запущен"""
    try:
        result = subprocess.run(
            ['pg_isready'],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False

def main():
    print("🗄️  Инициализация базы данных PostgreSQL для Склад Инструментов")
    print("=" * 70)
    print()
    
    # Проверка PostgreSQL
    print("📋 Проверка PostgreSQL...")
    if not check_postgresql():
        print("❌ PostgreSQL не запущен или не установлен")
        print()
        print("Установите и запустите PostgreSQL:")
        print("  brew install postgresql")
        print("  brew services start postgresql")
        print()
        sys.exit(1)
    
    print("✅ PostgreSQL запущен")
    print()
    
    # Параметры БД
    db_user = "sklad_user"
    db_pass = "sklad_pass"
    db_name = "sklad_instrumenta"
    
    current_user = getpass.getuser()
    
    # Создание пользователя
    print(f"📝 Создание пользователя '{db_user}'...")
    success, output = run_psql_command(
        f"DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{db_user}') THEN CREATE ROLE {db_user} WITH LOGIN PASSWORD '{db_pass}'; END IF; END $$;",
        current_user
    )
    
    if success:
        print("✅ Пользователь создан")
    else:
        if "does not exist" in output and "role" in output:
            print(f"⚠️  Нужно подключиться от имени пользователя PostgreSQL")
            print(f"   Попробуйте: psql -U postgres -c \"CREATE ROLE {db_user} WITH LOGIN PASSWORD '{db_pass}';\"")
        else:
            print(f"⚠️  {output.strip()}")
    
    print()
    
    # Создание базы данных
    print(f"📝 Создание базы данных '{db_name}'...")
    success, output = run_psql_command(
        f"SELECT 'CREATE DATABASE {db_name}' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '{db_name}')\\gexec",
        current_user
    )
    
    if success:
        if "CREATE DATABASE" in output:
            print("✅ База данных создана")
        else:
            print("ℹ️  База данных уже существует")
    else:
        print(f"❌ Ошибка: {output.strip()}")
        print(f"   Создайте вручную: psql -U {current_user} -c \"CREATE DATABASE {db_name};\"")
        sys.exit(1)
    
    print()
    
    # Предоставление прав
    print("📝 Предоставление прав...")
    success, output = run_psql_command(
        f"GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {db_user};",
        current_user
    )
    
    if success:
        print("✅ Права предоставлены")
    else:
        print(f"⚠️  {output.strip()}")
    
    print()
    print("=" * 70)
    print("✅ Инициализация завершена!")
    print()
    print("📋 Параметры подключения:")
    print(f"   DATABASE_URL=postgresql://{db_user}:{db_pass}@localhost:5432/{db_name}")
    print()
    print("🚀 Запуск приложения:")
    print("   cd fastapi_app")
    print("   python run.py")
    print()
    print("🌐 Приложение будет доступно:")
    print("   Десктоп: http://localhost:8550")
    print("   Мобильный: http://localhost:8550/mobile/")
    print()
    print("🔐 Вход по умолчанию:")
    print("   Логин: admin")
    print("   Пароль: admin_1234")
    print()

if __name__ == "__main__":
    main()
