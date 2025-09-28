#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Создание администратора в новой системе безопасности
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from enhanced.security_system_v3 import security_system

def create_admin():
    """Создание администратора"""
    print("🔐 Создание администратора в Enhanced Trading System v3.0")
    print("=" * 60)
    
    # Получаем данные от пользователя
    telegram_user_id = input("Введите Telegram User ID: ")
    telegram_username = input("Введите Telegram Username (без @): ")
    api_key = input("Введите OKX API Key: ")
    secret_key = input("Введите OKX Secret Key: ")
    passphrase = input("Введите OKX Passphrase: ")
    
    try:
        telegram_user_id = int(telegram_user_id)
    except ValueError:
        print("❌ Неверный формат Telegram User ID")
        return False
    
    # Валидируем API ключи
    if not security_system.validate_api_keys(api_key, secret_key, passphrase):
        print("❌ Неверный формат API ключей")
        return False
    
    # Регистрируем администратора
    success = security_system.register_user(
        telegram_user_id=telegram_user_id,
        telegram_username=telegram_username,
        api_key=api_key,
        secret_key=secret_key,
        passphrase=passphrase,
        role='admin'
    )
    
    if success:
        print("✅ Администратор успешно создан!")
        print(f"   User ID: {telegram_user_id}")
        print(f"   Username: @{telegram_username}")
        print(f"   Роль: admin")
        print("\nТеперь вы можете войти в систему через веб-интерфейс")
        return True
    else:
        print("❌ Ошибка создания администратора")
        return False

if __name__ == "__main__":
    create_admin()


