#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Initialize Authentication System
Enhanced Trading System v3.0 Commercial
"""

import os
import sys
import sqlite3
from datetime import datetime

# Добавляем путь к src для импорта модулей
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

def init_auth_system():
    """Инициализация новой системы аутентификации"""
    print("🚀 ИНИЦИАЛИЗАЦИЯ СИСТЕМЫ АУТЕНТИФИКАЦИИ")
    print("=" * 60)
    
    try:
        from core.auth_system import AuthSystem
        
        # Создаем экземпляр системы аутентификации
        auth = AuthSystem()
        
        print("✅ Система аутентификации инициализирована")
        print(f"📁 База данных: {auth.db_path}")
        
        # Создаем супер-администраторов
        create_super_admins(auth)
        
        # Создаем тестовых пользователей
        create_test_users(auth)
        
        print("\n🎉 ИНИЦИАЛИЗАЦИЯ ЗАВЕРШЕНА УСПЕШНО!")
        print("=" * 60)
        print("📋 Созданные аккаунты:")
        print("🔑 Super Admin 1:")
        print("   Username: superadmin")
        print("   Email: superadmin@example.com")
        print("   Password: SuperAdmin123!")
        print("   Role: super_admin")
        print()
        print("🔑 Super Admin 2:")
        print("   Username: admin")
        print("   Email: admin@example.com")
        print("   Password: Admin123!")
        print("   Role: super_admin")
        print()
        print("👤 Test User:")
        print("   Username: testuser")
        print("   Email: test@example.com")
        print("   Password: TestUser123!")
        print("   Role: user")
        print()
        print("📋 Следующие шаги:")
        print("1. Запустите систему: python scripts/start_enhanced.py")
        print("2. Откройте браузер: http://localhost:5000")
        print("3. Войдите как супер-администратор")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка инициализации: {e}")
        return False

def create_super_admins(auth):
    """Создание супер-администраторов"""
    print("\n👑 Создание супер-администраторов...")
    
    # Super Admin 1
    success, message = auth.register_user(
        username="superadmin",
        email="superadmin@example.com",
        password="SuperAdmin123!",
        role="super_admin"
    )
    
    if success:
        print("✅ Super Admin 1 создан")
    else:
        print(f"⚠️ Super Admin 1: {message}")
    
    # Super Admin 2
    success, message = auth.register_user(
        username="admin",
        email="admin@example.com",
        password="Admin123!",
        role="super_admin"
    )
    
    if success:
        print("✅ Super Admin 2 создан")
    else:
        print(f"⚠️ Super Admin 2: {message}")

def create_test_users(auth):
    """Создание тестовых пользователей"""
    print("\n👤 Создание тестовых пользователей...")
    
    # Test User
    success, message = auth.register_user(
        username="testuser",
        email="test@example.com",
        password="TestUser123!",
        role="user"
    )
    
    if success:
        print("✅ Test User создан")
    else:
        print(f"⚠️ Test User: {message}")

def check_database_integrity():
    """Проверка целостности базы данных"""
    print("\n🔍 Проверка целостности базы данных...")
    
    try:
        from core.auth_system import AuthSystem
        auth = AuthSystem()
        
        with sqlite3.connect(auth.db_path) as conn:
            cursor = conn.cursor()
            
            # Проверяем таблицы
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            print(f"📊 Найдено таблиц: {len(tables)}")
            for table in tables:
                print(f"   - {table[0]}")
            
            # Проверяем пользователей
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
            print(f"👥 Пользователей в системе: {user_count}")
            
            # Проверяем роли
            cursor.execute("SELECT role, COUNT(*) FROM users GROUP BY role")
            roles = cursor.fetchall()
            print("📋 Распределение по ролям:")
            for role, count in roles:
                print(f"   - {role}: {count}")
            
            return True
            
    except Exception as e:
        print(f"❌ Ошибка проверки базы данных: {e}")
        return False

def main():
    """Главная функция"""
    print("🚀 ENHANCED TRADING SYSTEM v3.0 COMMERCIAL")
    print("🔐 Инициализация системы аутентификации")
    print("=" * 60)
    
    # Инициализируем систему
    if not init_auth_system():
        return False
    
    # Проверяем целостность
    if not check_database_integrity():
        return False
    
    print("\n✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ УСПЕШНО!")
    print("🎯 Система готова к работе!")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)


















