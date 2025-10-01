#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Проверка базы данных пользователей
"""
import sqlite3

def check_database():
    """Проверяем базу данных"""
    try:
        conn = sqlite3.connect('secure_users.db')
        cursor = conn.cursor()
        
        # Получаем список таблиц
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        print("📊 Таблицы в базе данных:")
        for table in tables:
            print(f"  - {table[0]}")
        
        # Проверяем таблицу secure_users
        if ('secure_users',) in tables:
            # Получаем структуру таблицы
            cursor.execute("PRAGMA table_info(secure_users)")
            columns = cursor.fetchall()
            
            print(f"\n📋 Структура таблицы secure_users:")
            for col in columns:
                print(f"  {col[1]} ({col[2]})")
            
            # Получаем все данные
            cursor.execute("SELECT * FROM secure_users")
            users = cursor.fetchall()
            
            print(f"\n👥 Пользователи ({len(users)}):")
            for user in users:
                print(f"  {user}")
        else:
            print("\n❌ Таблица 'secure_users' не найдена")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    check_database()
