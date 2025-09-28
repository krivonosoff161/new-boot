#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для полной очистки и реорганизации проекта
Enhanced Trading System v3.0
"""

import os
import shutil
import glob
from pathlib import Path

def create_rttya_structure():
    """Создает структуру папок в rttya"""
    rttya_dirs = [
        'rttya/old_versions',
        'rttya/unused_files', 
        'rttya/empty_files',
        'rttya/duplicate_files',
        'rttya/archive_files',
        'rttya/test_files',
        'rttya/documentation_old',
        'rttya/scripts_old',
        'rttya/bat_files'
    ]
    
    for directory in rttya_dirs:
        os.makedirs(directory, exist_ok=True)
        print(f"✅ Создана папка: {directory}")

def analyze_files():
    """Анализирует все файлы в проекте"""
    print("🔍 Анализ файлов в проекте...")
    
    # Файлы для перемещения в rttya
    files_to_move = {
        'old_versions': [
            'base_trading_bot.py',
            'security.py', 
            'config_manager.py',
            'ipc.py',
            'log_helper.py',
            'capital_distributor_v2.0.py',
            'multi_analyze_stats_v2.0.py',
            'test_api_connection.py',
            'test_multi_user_manager.py',
            'test_web_interface.py'
        ],
        'empty_files': [
            'add_admins.py',
            'cleanup_users_db.py',
            'cleanup_users.py',
            'test_bot_launch.py',
            'test_web_simple.py',
            'test_bot_api.py',
            'fix_admins.py',
            'create_admin_simple.py',
            'security_utils.py',
            'test_api_simple.py'
        ],
        'bat_files': [
            '👑 Админ Панель.bat',
            '🛑 Остановить Все.bat',
            '⚡ Полный Запуск.bat',
            '🤖 Запуск Ботов.bat',
            '🚀 Запуск Dashboard.bat'
        ],
        'documentation_old': [
            'FINAL_INSTRUCTIONS.md',
            'API_KEYS_FINAL_FIX.md',
            'ENV_FILE_FIX.md',
            'FINAL_SUCCESS_PRODUCTION.md',
            'SYSTEM_STATUS_FIXED.md',
            'QUICK_START_WINDOWS.md',
            'TROUBLESHOOTING_GUIDE.md',
            'START_ENHANCED_SYSTEM.md'
        ],
        'duplicate_files': [
            'start_enhanced_system.py',  # Дублирует start_system.py
            'reorganize_system.py'       # Временный скрипт
        ]
    }
    
    return files_to_move

def move_files_to_rttya(files_to_move):
    """Перемещает файлы в соответствующие папки rttya"""
    print("📦 Перемещение файлов в rttya...")
    
    for category, files in files_to_move.items():
        for file in files:
            if os.path.exists(file):
                dest = f'rttya/{category}/{file}'
                shutil.move(file, dest)
                print(f"✅ Перемещен: {file} -> {dest}")
            else:
                print(f"⏭️ Файл не найден: {file}")

def move_directories_to_rttya():
    """Перемещает ненужные папки в rttya"""
    print("📁 Перемещение папок в rttya...")
    
    directories_to_move = [
        'enhanced_trading_system',  # Дублирующая структура
        'system_cleanup',          # Временная папка
        'archive',                 # Старые версии
        'temp',                    # Временные файлы
        'reports',                 # Старые отчеты
        'docs',                    # Дублирующая документация
        'tests',                   # Старые тесты
        'static',                  # Дублирующие статические файлы
        'templates'                # Дублирующие шаблоны
    ]
    
    for directory in directories_to_move:
        if os.path.exists(directory):
            dest = f'rttya/old_versions/{directory}'
            shutil.move(directory, dest)
            print(f"✅ Перемещена папка: {directory} -> {dest}")
        else:
            print(f"⏭️ Папка не найдена: {directory}")

def clean_empty_files():
    """Удаляет пустые файлы"""
    print("🗑️ Удаление пустых файлов...")
    
    empty_files = [
        'add_admins.py',
        'cleanup_users_db.py', 
        'cleanup_users.py',
        'test_bot_launch.py',
        'test_web_simple.py',
        'test_bot_api.py',
        'fix_admins.py',
        'create_admin_simple.py',
        'security_utils.py',
        'test_api_simple.py'
    ]
    
    for file in empty_files:
        if os.path.exists(file) and os.path.getsize(file) == 0:
            os.remove(file)
            print(f"🗑️ Удален пустой файл: {file}")

def create_clean_structure():
    """Создает чистую структуру проекта"""
    print("🏗️ Создание чистой структуры...")
    
    # Основные папки
    main_dirs = [
        'enhanced',      # Основные модули
        'web_interface', # Веб-интерфейс
        'user_data',     # Данные пользователей
        'logs',          # Логи
        'config'         # Конфигурация
    ]
    
    for directory in main_dirs:
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            print(f"✅ Создана папка: {directory}")

def move_config_files():
    """Перемещает конфигурационные файлы в папку config"""
    print("⚙️ Организация конфигурационных файлов...")
    
    config_files = [
        'bot_config.json',
        '.env',
        '.master_key'
    ]
    
    for file in config_files:
        if os.path.exists(file):
            dest = f'config/{file}'
            shutil.move(file, dest)
            print(f"✅ Перемещен конфиг: {file} -> {dest}")

def create_main_launcher():
    """Создает главный скрипт запуска"""
    print("🚀 Создание главного скрипта запуска...")
    
    launcher_content = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Trading System v3.0 - Главный скрипт запуска
"""

import os
import sys
import subprocess

def main():
    print("🚀 Enhanced Trading System v3.0")
    print("=" * 50)
    
    # Переходим в папку веб-интерфейса
    os.chdir('web_interface')
    
    # Запускаем веб-интерфейс
    print("🌐 Запуск веб-интерфейса...")
    subprocess.run([sys.executable, 'app.py'])

if __name__ == "__main__":
    main()
'''
    
    with open('start.py', 'w', encoding='utf-8') as f:
        f.write(launcher_content)
    print("✅ Создан главный скрипт: start.py")

def create_readme():
    """Создает README для очищенного проекта"""
    print("📖 Создание README...")
    
    readme_content = '''# Enhanced Trading System v3.0

## 📁 Структура проекта

```
enhanced_trading_system/
├── enhanced/              # Основные модули системы
│   ├── security_system_v3.py
│   ├── user_bot_manager.py
│   ├── bot_manager.py
│   └── ...
├── web_interface/         # Веб-интерфейс
│   ├── app.py
│   ├── static/
│   └── templates/
├── user_data/            # Данные пользователей
├── logs/                 # Логи системы
├── config/               # Конфигурационные файлы
│   ├── bot_config.json
│   ├── .env
│   └── .master_key
├── secure_users.db       # База данных пользователей
├── users.db             # Старая база данных
└── start.py             # Главный скрипт запуска
```

## 🚀 Запуск системы

```bash
python start.py
```

## 📖 Документация

- `SYSTEM_FIXES_REPORT.md` - Отчет об исправлениях
- `ENHANCED_SYSTEM_GUIDE.md` - Руководство пользователя
- `WEB_INTERFACE_GUIDE.md` - Руководство по веб-интерфейсу

## 🗂️ Архив

Старые файлы и версии перемещены в папку `rttya/`:
- `rttya/old_versions/` - Старые версии файлов
- `rttya/empty_files/` - Пустые файлы
- `rttya/duplicate_files/` - Дублирующие файлы
- `rttya/archive_files/` - Архивные файлы
'''
    
    with open('README.md', 'w', encoding='utf-8') as f:
        f.write(readme_content)
    print("✅ Создан README.md")

def main():
    """Главная функция очистки"""
    print("🧹 Полная очистка и реорганизация проекта")
    print("=" * 60)
    
    # Создаем структуру rttya
    create_rttya_structure()
    
    # Анализируем файлы
    files_to_move = analyze_files()
    
    # Перемещаем файлы
    move_files_to_rttya(files_to_move)
    
    # Перемещаем папки
    move_directories_to_rttya()
    
    # Удаляем пустые файлы
    clean_empty_files()
    
    # Создаем чистую структуру
    create_clean_structure()
    
    # Организуем конфигурацию
    move_config_files()
    
    # Создаем главный скрипт
    create_main_launcher()
    
    # Создаем README
    create_readme()
    
    print("\n🎉 Очистка завершена!")
    print("📁 Основная структура:")
    print("   - enhanced/ (основные модули)")
    print("   - web_interface/ (веб-интерфейс)")
    print("   - user_data/ (данные пользователей)")
    print("   - logs/ (логи)")
    print("   - config/ (конфигурация)")
    print("   - start.py (главный скрипт)")
    print("\n🗂️ Старые файлы перемещены в rttya/")
    print("\n🚀 Для запуска: python start.py")

if __name__ == "__main__":
    main()
