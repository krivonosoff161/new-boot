#!/usr/bin/env python3
"""
Управление пользователями системы
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.database.models import User, db
from src.database.database import init_db
from werkzeug.security import generate_password_hash
import argparse

def create_user(username, email, password, role='user'):
    """Создание нового пользователя"""
    try:
        # Проверяем, существует ли пользователь
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            print(f"❌ Пользователь {username} уже существует")
            return False
        
        # Создаем нового пользователя
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            role=role,
            is_active=True
        )
        
        db.session.add(user)
        db.session.commit()
        
        print(f"✅ Пользователь {username} создан успешно")
        print(f"   📧 Email: {email}")
        print(f"   🔑 Роль: {role}")
        print(f"   🆔 ID: {user.id}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка создания пользователя: {e}")
        db.session.rollback()
        return False

def list_users():
    """Список всех пользователей"""
    try:
        users = User.query.all()
        if not users:
            print("📝 Пользователи не найдены")
            return
        
        print("👥 Список пользователей:")
        print("=" * 60)
        for user in users:
            status = "🟢 Активен" if user.is_active else "🔴 Неактивен"
            print(f"ID: {user.id:3d} | {user.username:15s} | {user.email:25s} | {user.role:10s} | {status}")
        
    except Exception as e:
        print(f"❌ Ошибка получения списка пользователей: {e}")

def deactivate_user(username):
    """Деактивация пользователя"""
    try:
        user = User.query.filter_by(username=username).first()
        if not user:
            print(f"❌ Пользователь {username} не найден")
            return False
        
        user.is_active = False
        db.session.commit()
        
        print(f"✅ Пользователь {username} деактивирован")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка деактивации пользователя: {e}")
        db.session.rollback()
        return False

def activate_user(username):
    """Активация пользователя"""
    try:
        user = User.query.filter_by(username=username).first()
        if not user:
            print(f"❌ Пользователь {username} не найден")
            return False
        
        user.is_active = True
        db.session.commit()
        
        print(f"✅ Пользователь {username} активирован")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка активации пользователя: {e}")
        db.session.rollback()
        return False

def change_user_role(username, new_role):
    """Изменение роли пользователя"""
    try:
        user = User.query.filter_by(username=username).first()
        if not user:
            print(f"❌ Пользователь {username} не найден")
            return False
        
        old_role = user.role
        user.role = new_role
        db.session.commit()
        
        print(f"✅ Роль пользователя {username} изменена: {old_role} → {new_role}")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка изменения роли: {e}")
        db.session.rollback()
        return False

def main():
    """Главная функция"""
    parser = argparse.ArgumentParser(description='Управление пользователями')
    subparsers = parser.add_subparsers(dest='command', help='Доступные команды')
    
    # Создание пользователя
    create_parser = subparsers.add_parser('create', help='Создать пользователя')
    create_parser.add_argument('username', help='Имя пользователя')
    create_parser.add_argument('email', help='Email пользователя')
    create_parser.add_argument('password', help='Пароль пользователя')
    create_parser.add_argument('--role', default='user', choices=['user', 'admin'], help='Роль пользователя')
    
    # Список пользователей
    subparsers.add_parser('list', help='Список пользователей')
    
    # Деактивация
    deactivate_parser = subparsers.add_parser('deactivate', help='Деактивировать пользователя')
    deactivate_parser.add_argument('username', help='Имя пользователя')
    
    # Активация
    activate_parser = subparsers.add_parser('activate', help='Активировать пользователя')
    activate_parser.add_argument('username', help='Имя пользователя')
    
    # Изменение роли
    role_parser = subparsers.add_parser('role', help='Изменить роль пользователя')
    role_parser.add_argument('username', help='Имя пользователя')
    role_parser.add_argument('new_role', choices=['user', 'admin'], help='Новая роль')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Инициализируем базу данных
    init_db()
    
    # Выполняем команду
    if args.command == 'create':
        create_user(args.username, args.email, args.password, args.role)
    elif args.command == 'list':
        list_users()
    elif args.command == 'deactivate':
        deactivate_user(args.username)
    elif args.command == 'activate':
        activate_user(args.username)
    elif args.command == 'role':
        change_user_role(args.username, args.new_role)

if __name__ == '__main__':
    main()





