#!/usr/bin/env python3
"""
Запуск приложения Склад Инструментов
"""
import sys
import os
import signal
import socket
import subprocess

# Добавляем корень проекта в path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn
from config import APP_PORT


def kill_process_on_port(port):
    """Освобождает порт, убивая процесс, который его использует"""
    try:
        # Ищем процесс, использующий порт
        result = subprocess.run(
            ['lsof', '-ti', f':{port}'],
            capture_output=True,
            text=True
        )
        
        if result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            print(f"⚠️  Порт {port} занят. Освобождаем...")
            
            for pid in pids:
                try:
                    pid = int(pid.strip())
                    os.kill(pid, signal.SIGTERM)
                    print(f"   ✓ Процесс {pid} остановлен")
                except ProcessLookupError:
                    pass
                except Exception as e:
                    print(f"   ✗ Не удалось остановить процесс {pid}: {e}")
            
            # Даем время на освобождение порта
            import time
            time.sleep(1)
            return True
        return False
    except Exception as e:
        print(f"⚠️  Ошибка при освобождении порта: {e}")
        return False


def is_port_in_use(port):
    """Проверяет, занят ли порт"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('0.0.0.0', port))
            return False
        except OSError:
            return True


if __name__ == "__main__":
    # Проверяем и освобождаем порт если нужно
    if is_port_in_use(APP_PORT):
        print(f"\n🔍 Порт {APP_PORT} уже используется")
        if kill_process_on_port(APP_PORT):
            print(f"✅ Порт {APP_PORT} освобожден\n")
        else:
            print(f"⚠️  Не удалось освободить порт {APP_PORT}\n")
    else:
        print(f"\n✅ Порт {APP_PORT} свободен\n")
    
    print(f"🚀 Запуск Склад Инструментов на порту {APP_PORT}")
    print(f"   http://localhost:{APP_PORT}")
    print(f"   Логин: admin / Пароль: admin_1234\n")
    
    uvicorn.run("main:app", host="0.0.0.0", port=APP_PORT, reload=True)
