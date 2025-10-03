#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Отладка импортов
"""
import os
import sys

# Добавляем пути для импорта
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), 'src'))
sys.path.insert(0, project_root)

print("🔍 ОТЛАДКА ИМПОРТОВ")
print("=" * 30)

print("1️⃣ Проверка путей...")
print(f"   Текущая директория: {os.getcwd()}")
print(f"   project_root: {project_root}")
print(f"   sys.path: {sys.path[:3]}")

print("\n2️⃣ Проверка файлов...")
real_grid_bot_path = os.path.join(project_root, 'trading', 'real_grid_bot.py')
print(f"   real_grid_bot.py: {os.path.exists(real_grid_bot_path)}")

print("\n3️⃣ Попытка импорта...")
try:
    from src.trading.real_grid_bot import RealGridBot
    print("✅ RealGridBot импортирован успешно")
except ImportError as e:
    print(f"❌ Ошибка импорта RealGridBot: {e}")
except Exception as e:
    print(f"❌ Неожиданная ошибка: {e}")
    import traceback
    print(f"Трассировка: {traceback.format_exc()}")

print("\n4️⃣ Проверка зависимостей...")
try:
    import ccxt
    print("✅ ccxt импортирован")
except ImportError as e:
    print(f"❌ ccxt не найден: {e}")

try:
    from src.core.log_helper import build_logger
    print("✅ log_helper импортирован")
except ImportError as e:
    print(f"❌ log_helper не найден: {e}")

print("\n✅ ОТЛАДКА ЗАВЕРШЕНА!")



