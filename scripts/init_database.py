#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database Initialization Script
Enhanced Trading System v3.0 Commercial
"""

import os
import sys
import sqlite3
from datetime import datetime

# Добавляем путь к src для импорта модулей
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

def init_database():
    """Инициализация базы данных"""
    print("🚀 Инициализация базы данных...")
    
    # Создаем папку для базы данных
    db_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'database')
    os.makedirs(db_dir, exist_ok=True)
    
    # Путь к базе данных
    db_path = os.path.join(db_dir, 'secure_users.db')
    
    try:
        # Подключаемся к базе данных
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Создаем таблицу пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'user',
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Создаем таблицу API ключей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                exchange TEXT NOT NULL,
                api_key_encrypted TEXT NOT NULL,
                secret_key_encrypted TEXT NOT NULL,
                passphrase_encrypted TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Создаем таблицу сессий
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                session_token TEXT UNIQUE NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Создаем таблицу логов безопасности
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS security_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT NOT NULL,
                ip_address TEXT,
                user_agent TEXT,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Создаем таблицу подписок
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                tier TEXT NOT NULL,
                status TEXT NOT NULL,
                start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                end_date TIMESTAMP,
                auto_renew BOOLEAN DEFAULT 1,
                payment_method TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Создаем таблицу платежей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subscription_id INTEGER,
                amount DECIMAL(10,2) NOT NULL,
                currency TEXT DEFAULT 'USD',
                status TEXT NOT NULL,
                payment_method TEXT,
                transaction_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (subscription_id) REFERENCES subscriptions (id)
            )
        ''')
        
        # Создаем таблицу использования
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usage_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                date DATE NOT NULL,
                api_calls INTEGER DEFAULT 0,
                bots_active INTEGER DEFAULT 0,
                capital_used DECIMAL(15,2) DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Создаем индексы для производительности
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(session_token)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_security_logs_user_id ON security_logs(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id ON subscriptions(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_usage_stats_user_date ON usage_stats(user_id, date)')
        
        # Сохраняем изменения
        conn.commit()
        
        print("✅ База данных успешно инициализирована!")
        print(f"📁 Путь к базе данных: {db_path}")
        
        # Проверяем созданные таблицы
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"📊 Создано таблиц: {len(tables)}")
        for table in tables:
            print(f"   - {table[0]}")
        
    except Exception as e:
        print(f"❌ Ошибка инициализации базы данных: {e}")
        return False
    finally:
        if conn:
            conn.close()
    
    return True

def create_admin_user():
    """Создание администратора по умолчанию"""
    print("\n👤 Создание администратора...")
    
    try:
        # Создаем администратора напрямую в базе данных
        db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'database', 'secure_users.db')
        
        # Проверяем, существует ли уже администратор
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM users WHERE username = ?", ("admin",))
        if cursor.fetchone():
            print("⚠️ Администратор уже существует")
            conn.close()
            return True
        
        # Создаем хеш пароля
        import hashlib
        password_hash = hashlib.sha256("admin123".encode()).hexdigest()
        
        # Создаем администратора
        cursor.execute('''
            INSERT INTO users (username, email, password_hash, role, is_active)
            VALUES (?, ?, ?, ?, ?)
        ''', ("admin", "admin@example.com", password_hash, "admin", 1))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Администратор создан:")
        print(f"   Username: admin")
        print(f"   Email: admin@example.com")
        print(f"   Password: admin123")
        print(f"   Role: admin")
        return True
            
    except Exception as e:
        print(f"❌ Ошибка создания администратора: {e}")
        return False

def main():
    """Главная функция"""
    print("🚀 ИНИЦИАЛИЗАЦИЯ СИСТЕМЫ")
    print("=" * 50)
    
    # Инициализируем базу данных
    if not init_database():
        print("❌ Не удалось инициализировать базу данных")
        return False
    
    # Создаем администратора
    if not create_admin_user():
        print("❌ Не удалось создать администратора")
        return False
    
    print("\n🎉 ИНИЦИАЛИЗАЦИЯ ЗАВЕРШЕНА УСПЕШНО!")
    print("=" * 50)
    print("📋 Следующие шаги:")
    print("1. Запустите систему: python scripts/start.py")
    print("2. Откройте браузер: http://localhost:5000")
    print("3. Войдите как администратор:")
    print("   Username: admin")
    print("   Password: admin123")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
