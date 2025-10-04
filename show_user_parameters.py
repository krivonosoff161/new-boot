#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Показать параметры пользователя для восстановления пароля
"""

import sqlite3

def show_user_parameters():
    """Показать параметры пользователя"""
    print("🔥 SOVERYN FIELD: ПАРАМЕТРЫ ПОЛЬЗОВАТЕЛЯ ДЛЯ ВОССТАНОВЛЕНИЯ ПАРОЛЯ")
    print("=" * 70)
    
    try:
        conn = sqlite3.connect('secure_users.db')
        cursor = conn.cursor()
        
        # Получаем все данные пользователя
        cursor.execute('SELECT * FROM secure_users')
        users = cursor.fetchall()
        
        # Получаем названия колонок
        cursor.execute('PRAGMA table_info(secure_users)')
        columns = [col[1] for col in cursor.fetchall()]
        
        print(f"\nНайдено пользователей: {len(users)}")
        print("\n" + "=" * 70)
        
        for i, user in enumerate(users, 1):
            print(f"\n👤 ПОЛЬЗОВАТЕЛЬ #{i}:")
            print("-" * 50)
            
            # Создаем словарь для удобного отображения
            user_data = dict(zip(columns, user))
            
            # Показываем основные параметры
            print(f"📱 Telegram ID (user_id): {user_data.get('user_id', 'N/A')}")
            print(f"👤 Telegram Username: {user_data.get('telegram_username', 'N/A')}")
            print(f"📧 Email: {user_data.get('email', 'N/A')}")
            print(f"🔑 Роль: {user_data.get('role', 'N/A')}")
            print(f"📅 Дата регистрации: {user_data.get('registration_date', 'N/A')}")
            print(f"🔄 Последний вход: {user_data.get('last_login', 'N/A')}")
            print(f"✅ Активен: {user_data.get('is_active', 'N/A')}")
            print(f"🔐 Режим ключей: {user_data.get('key_mode', 'N/A')}")
            
            print("\n" + "=" * 70)
        
        conn.close()
        
        print("\n🎯 ДЛЯ ВОССТАНОВЛЕНИЯ ПАРОЛЯ ИСПОЛЬЗУЙТЕ:")
        print("=" * 50)
        print("📱 Через Telegram:")
        print("   - Введите Telegram ID (цифры): 462885677")
        print("   - ИЛИ введите Telegram Username: дмитрий")
        print("")
        print("📧 Через Email:")
        print("   - Введите Email: krivonosoffya@mail.ru")
        
    except Exception as e:
        print(f"Ошибка: {e}")

if __name__ == "__main__":
    show_user_parameters()
