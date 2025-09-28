#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Полная очистка базы данных пользователей
"""

import os
import sys
sys.path.append('enhanced')

def clear_all_users():
    """Полная очистка базы данных"""
    print("🗑️ Полная очистка базы данных")
    print("=" * 40)
    
    # Удаляем файлы базы данных
    db_files = ['secure_users.db', 'users.db', 'users.json']
    
    for db_file in db_files:
        if os.path.exists(db_file):
            try:
                os.remove(db_file)
                print(f"✅ Удален файл: {db_file}")
            except Exception as e:
                print(f"❌ Ошибка удаления {db_file}: {e}")
        else:
            print(f"ℹ️ Файл не найден: {db_file}")
    
    print("\n✅ База данных полностью очищена!")
    print("Теперь можно зарегистрировать нового пользователя")

if __name__ == "__main__":
    clear_all_users()


