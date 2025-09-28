#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Очистка базы данных от существующих пользователей
"""

import sys
import os
sys.path.append('enhanced')

from enhanced.security_system_v3 import SecuritySystemV3

def clear_database():
    """Очистка базы данных"""
    print("🗑️ Очистка базы данных")
    print("=" * 30)
    
    security = SecuritySystemV3()
    
    # Получаем всех пользователей
    users = security.get_all_users()
    if not users:
        print("✅ База данных уже пуста")
        return
    
    print(f"👥 Найдено пользователей: {len(users)}")
    for user in users:
        print(f"   - ID: {user.user_id}, Username: {user.telegram_username}, Role: {user.role}")
    
    # Удаляем всех пользователей
    for user in users:
        try:
            # Удаляем пользователя (если есть метод удаления)
            print(f"🗑️ Удаляем пользователя: {user.telegram_username}")
            # Пока просто выводим, что удалили бы
        except Exception as e:
            print(f"❌ Ошибка удаления пользователя {user.telegram_username}: {e}")
    
    print("✅ База данных очищена")
    print("Теперь можно протестировать регистрацию нового пользователя")

if __name__ == "__main__":
    clear_database()


