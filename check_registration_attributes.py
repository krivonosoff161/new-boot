#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Проверка атрибутов при регистрации
"""

import sqlite3

def check_registration_attributes():
    """Проверяем атрибуты при регистрации"""
    print("🔥 SOVERYN FIELD: ПРОВЕРКА АТРИБУТОВ ПРИ РЕГИСТРАЦИИ")
    print("=" * 60)
    
    try:
        conn = sqlite3.connect('secure_users.db')
        cursor = conn.cursor()
        
        # Проверяем структуру таблицы
        cursor.execute('PRAGMA table_info(secure_users)')
        columns = cursor.fetchall()
        print("\n📋 СТРУКТУРА ТАБЛИЦЫ:")
        print("-" * 40)
        for col in columns:
            print(f"  {col[1]}: {col[2]}")
        
        # Проверяем данные пользователя
        cursor.execute('SELECT * FROM secure_users')
        users = cursor.fetchall()
        
        print(f"\n👤 ДАННЫЕ ПОЛЬЗОВАТЕЛЕЙ ({len(users)} шт.):")
        print("-" * 40)
        
        for i, user in enumerate(users, 1):
            print(f"\nПользователь #{i}:")
            user_dict = dict(zip([col[1] for col in columns], user))
            
            # Показываем ключевые поля
            key_fields = ['user_id', 'telegram_username', 'email', 'role']
            for field in key_fields:
                value = user_dict.get(field, 'N/A')
                print(f"  {field}: {value}")
            
            # Показываем все поля для анализа
            print(f"\n  Все поля:")
            for field, value in user_dict.items():
                if value is not None and str(value).strip():
                    print(f"    {field}: {value}")
        
        conn.close()
        
        print("\n" + "=" * 60)
        print("🎯 АНАЛИЗ ПРОБЛЕМЫ:")
        print("-" * 40)
        print("1. telegram_username - это НИК в Telegram (может отсутствовать)")
        print("2. user_id - это Telegram ID (уникальный номер)")
        print("3. email - это email пользователя")
        print("4. При регистрации нужно правильно заполнять все поля")
        
    except Exception as e:
        print(f"Ошибка: {e}")

if __name__ == "__main__":
    check_registration_attributes()
