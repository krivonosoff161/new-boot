#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сброс пароля пользователя
"""

import sys
import os
sys.path.append('enhanced')

from enhanced.security_system_v3 import SecuritySystemV3

def reset_password():
    """Сброс пароля"""
    print("🔐 Сброс пароля")
    print("=" * 30)
    
    security = SecuritySystemV3()
    
    # Получаем пользователя
    users = security.get_all_users()
    if not users:
        print("❌ Пользователи не найдены")
        return
    
    user = users[0]
    print(f"👤 Пользователь: {user.telegram_username}")
    
    # Устанавливаем новый пароль
    new_password = user.telegram_username  # Пароль = логин
    success = security.update_user_password(user.user_id, new_password)
    
    if success:
        print("✅ Пароль сброшен!")
        print(f"   Логин: {user.telegram_username}")
        print(f"   Пароль: {user.telegram_username}")
    else:
        print("❌ Ошибка сброса пароля")

if __name__ == "__main__":
    reset_password()


