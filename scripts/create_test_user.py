#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Создание тестового пользователя
"""

import sys
import os
sys.path.append('enhanced')

from enhanced.security_system_v3 import SecuritySystemV3

def create_test_user():
    """Создание тестового пользователя"""
    print("🔐 Создание тестового пользователя")
    print("=" * 40)
    
    security = SecuritySystemV3()
    
    # Проверяем, есть ли уже пользователи
    users = security.get_all_users()
    if users:
        print("👥 Найденные пользователи:")
        for user in users:
            print(f"   - ID: {user.user_id}, Username: {user.telegram_username}, Role: {user.role}")
        return
    
    # Создаем тестового пользователя
    test_data = {
        'telegram_user_id': 123456789,
        'telegram_username': 'testuser',
        'api_key': 'test_api_key_123',
        'secret_key': 'test_secret_key_456',
        'passphrase': 'test_passphrase_789',
        'role': 'admin'
    }
    
    print("📝 Создаем тестового пользователя...")
    success = security.register_user(**test_data)
    
    if success:
        print("✅ Тестовый пользователь создан!")
        print("   Логин: testuser")
        print("   Пароль: testuser")
        print("   Роль: admin")
    else:
        print("❌ Ошибка создания пользователя")

if __name__ == "__main__":
    create_test_user()


