#!/usr/bin/env python3
"""
Скрипт для исправления проблемы с двойным шифрованием ключей
"""

import sqlite3
import os

def fix_encryption_issue():
    """Исправление проблемы с двойным шифрованием"""
    print("🔧 ИСПРАВЛЕНИЕ ПРОБЛЕМЫ С ШИФРОВАНИЕМ")
    print("=" * 50)
    
    try:
        # Удаляем текущую базу данных
        if os.path.exists('secure_users.db'):
            os.remove('secure_users.db')
            print("✅ Старая база данных удалена")
        
        # Создаем новую базу данных
        conn = sqlite3.connect('secure_users.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS secure_users (
                user_id INTEGER PRIMARY KEY,
                telegram_username TEXT UNIQUE NOT NULL,
                encrypted_api_key TEXT,
                encrypted_secret_key TEXT,
                encrypted_passphrase TEXT,
                encryption_key TEXT,
                registration_date TEXT,
                last_login TEXT,
                login_attempts INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                role TEXT DEFAULT 'user',
                subscription_status TEXT DEFAULT 'free',
                key_mode TEXT DEFAULT 'sandbox'
            )
        ''')
        
        conn.commit()
        conn.close()
        print("✅ Новая база данных создана")
        
        print("\n🎯 РЕШЕНИЕ ПРОБЛЕМЫ:")
        print("1. Удалена старая база с неправильно зашифрованными ключами")
        print("2. Создана новая база данных")
        print("3. Теперь нужно перерегистрироваться с правильными ключами")
        
        print("\n📋 ИНСТРУКЦИЯ:")
        print("1. Откройте http://localhost:5000/register")
        print("2. Зарегистрируйтесь заново с вашими API ключами")
        print("3. Ключи будут правильно зашифрованы")
        print("4. Система будет работать корректно")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    fix_encryption_issue()
