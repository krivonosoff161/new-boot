#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Исправление роли супер-админа
"""

import sqlite3

def fix_super_admin():
    """Исправляем роль супер-админа"""
    print("🔥 SOVERYN FIELD: ИСПРАВЛЕНИЕ РОЛИ СУПЕР-АДМИНА")
    print("=" * 50)
    
    try:
        conn = sqlite3.connect('secure_users.db')
        cursor = conn.cursor()
        
        # Обновляем subscription_status для super_admin
        cursor.execute('UPDATE secure_users SET subscription_status = ? WHERE role = ?', ('premium', 'super_admin'))
        conn.commit()
        
        # Проверяем результат
        cursor.execute('SELECT user_id, telegram_username, role, subscription_status FROM secure_users WHERE role = ?', ('super_admin',))
        result = cursor.fetchone()
        
        if result:
            print(f"✅ Супер-админ обновлен:")
            print(f"   ID: {result[0]}")
            print(f"   Username: {result[1]}")
            print(f"   Роль: {result[2]}")
            print(f"   Подписка: {result[3]}")
        else:
            print("❌ Супер-админ не найден")
        
        conn.close()
        
    except Exception as e:
        print(f"Ошибка: {e}")

if __name__ == "__main__":
    fix_super_admin()
