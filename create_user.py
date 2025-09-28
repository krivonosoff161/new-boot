#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Создание простого пользователя для тестирования дашборда
"""

import os
import sqlite3
from werkzeug.security import generate_password_hash

def create_user_database():
    """Создание базы данных пользователей"""
    
    # Создаем директорию если не существует
    os.makedirs('data/database', exist_ok=True)
    
    # Подключаемся к базе данных
    conn = sqlite3.connect('data/database/auth_users.db')
    cursor = conn.cursor()
    
    # Создаем таблицу пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Создаем тестового пользователя
    username = 'admin'
    email = 'admin@example.com'
    password = 'admin123'
    role = 'admin'
    
    # Проверяем, существует ли пользователь
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    if cursor.fetchone():
        print(f"✅ Пользователь {username} уже существует")
    else:
        # Создаем пользователя
        hashed_password = generate_password_hash(password)
        cursor.execute('''
            INSERT INTO users (username, email, password_hash, role)
            VALUES (?, ?, ?, ?)
        ''', (username, email, hashed_password, role))
        
        conn.commit()
        print(f"✅ Создан пользователь: {username}")
        print(f"   Email: {email}")
        print(f"   Пароль: {password}")
        print(f"   Роль: {role}")
    
    # Создаем обычного пользователя
    username2 = 'user'
    email2 = 'user@example.com'
    password2 = 'user123'
    role2 = 'user'
    
    cursor.execute('SELECT * FROM users WHERE username = ?', (username2,))
    if cursor.fetchone():
        print(f"✅ Пользователь {username2} уже существует")
    else:
        hashed_password2 = generate_password_hash(password2)
        cursor.execute('''
            INSERT INTO users (username, email, password_hash, role)
            VALUES (?, ?, ?, ?)
        ''', (username2, email2, hashed_password2, role2))
        
        conn.commit()
        print(f"✅ Создан пользователь: {username2}")
        print(f"   Email: {email2}")
        print(f"   Пароль: {password2}")
        print(f"   Роль: {role2}")
    
    conn.close()
    print("✅ База данных пользователей создана успешно!")

if __name__ == '__main__':
    create_user_database()






