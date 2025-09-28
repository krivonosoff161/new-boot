#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Создание простого пользователя с известными данными
"""

import sys
import os
sys.path.append('enhanced')

from enhanced.security_system_v3 import SecuritySystemV3

def create_simple_user():
    """Создание простого пользователя"""
    print("🔐 Создание простого пользователя")
    print("=" * 40)
    
    security = SecuritySystemV3()
    
    # Создаем простого пользователя
    test_data = {
        'telegram_user_id': 999999999,
        'telegram_username': 'admin',
        'api_key': 'test_api_key_123',
        'secret_key': 'test_secret_key_456', 
        'passphrase': 'test_passphrase_789',
        'role': 'admin'
    }
    
    print("📝 Создаем пользователя...")
    success = security.register_user(**test_data)
    
    if success:
        print("✅ Пользователь создан!")
        print("   Логин: admin")
        print("   Пароль: admin")
        print("   Роль: admin")
    else:
        print("❌ Ошибка создания пользователя")

if __name__ == "__main__":
    create_simple_user()


