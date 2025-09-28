#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Start Script
Enhanced Trading System v3.0 Commercial
"""

import os
import sys
import asyncio
import subprocess
from pathlib import Path

# Добавляем путь к src для импорта модулей
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

def check_dependencies():
    """Проверка зависимостей"""
    print("🔍 Проверка зависимостей...")
    
    required_packages = [
        'flask', 'ccxt', 'numpy', 'pandas', 
        'cryptography', 'aiohttp', 'loguru'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package}")
    
    if missing_packages:
        print(f"\n⚠️ Отсутствуют пакеты: {', '.join(missing_packages)}")
        print("Установите их командой: pip install -r requirements-minimal.txt")
        return False
    
    return True

def check_database():
    """Проверка базы данных"""
    print("\n🔍 Проверка базы данных...")
    
    db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'database', 'secure_users.db')
    
    if not os.path.exists(db_path):
        print("❌ База данных не найдена")
        print("Запустите инициализацию: python scripts/init_database.py")
        return False
    
    print("✅ База данных найдена")
    return True

def check_config():
    """Проверка конфигурации"""
    print("\n🔍 Проверка конфигурации...")
    
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'bot_config.json')
    
    if not os.path.exists(config_path):
        print("❌ Конфигурация не найдена")
        return False
    
    print("✅ Конфигурация найдена")
    return True

def start_web_interface():
    """Запуск веб-интерфейса"""
    print("\n🌐 Запуск веб-интерфейса...")
    
    try:
        # Добавляем путь к src в sys.path
        import sys
        import os
        src_path = os.path.join(os.path.dirname(__file__), '..', 'src')
        sys.path.insert(0, src_path)
        
        from web.app import app
        
        print("✅ Веб-интерфейс запущен")
        print("🌐 Откройте браузер: http://localhost:5000")
        
        # Запускаем Flask приложение
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=True,
            use_reloader=False
        )
        
    except Exception as e:
        print(f"❌ Ошибка запуска веб-интерфейса: {e}")
        import traceback
        traceback.print_exc()
        return False

def start_telegram_bot():
    """Запуск Telegram бота"""
    print("\n🤖 Запуск Telegram бота...")
    
    try:
        # Добавляем путь к src в sys.path
        import sys
        import os
        src_path = os.path.join(os.path.dirname(__file__), '..', 'src')
        sys.path.insert(0, src_path)
        
        from trading.enhanced_controller import main as telegram_main
        
        print("✅ Telegram бот запущен")
        
        # Запускаем Telegram бота в отдельном процессе
        asyncio.run(telegram_main())
        
    except Exception as e:
        print(f"❌ Ошибка запуска Telegram бота: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Главная функция"""
    print("🚀 ENHANCED TRADING SYSTEM v3.0 COMMERCIAL")
    print("=" * 60)
    
    # Проверяем зависимости
    if not check_dependencies():
        return False
    
    # Проверяем базу данных
    if not check_database():
        return False
    
    # Проверяем конфигурацию
    if not check_config():
        return False
    
    print("\n✅ Все проверки пройдены успешно!")
    print("=" * 60)
    
    # Выбираем режим запуска
    print("\n📋 Выберите режим запуска:")
    print("1. Только веб-интерфейс")
    print("2. Только Telegram бот")
    print("3. Веб-интерфейс + Telegram бот")
    print("4. Выход")
    
    while True:
        try:
            choice = input("\nВведите номер (1-4): ").strip()
            
            if choice == "1":
                start_web_interface()
                break
            elif choice == "2":
                start_telegram_bot()
                break
            elif choice == "3":
                print("🚀 Запуск в полном режиме...")
                # Здесь можно добавить запуск в многопоточном режиме
                start_web_interface()
                break
            elif choice == "4":
                print("👋 До свидания!")
                break
            else:
                print("❌ Неверный выбор. Попробуйте снова.")
                
        except KeyboardInterrupt:
            print("\n👋 До свидания!")
            break
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            break
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n👋 До свидания!")
        sys.exit(0)
