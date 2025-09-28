#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flask-Login Integration
Enhanced Trading System v3.0 Commercial
"""

from flask import Flask, request, session, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
import logging

from .auth_system import auth_system, User

class FlaskUser(UserMixin):
    """Flask-Login совместимый класс пользователя"""
    
    def __init__(self, user: User):
        self.id = user.id
        self.username = user.username
        self.email = user.email
        self.role = user.role
        self.is_active = user.is_active
        self.created_at = user.created_at
        self.last_login = user.last_login
        self.login_attempts = user.login_attempts
        self.two_factor_enabled = user.two_factor_enabled
        self.two_factor_secret = user.two_factor_secret
        self.backup_codes = user.backup_codes

def init_flask_auth(app: Flask):
    """Инициализация Flask-Login"""
    
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Пожалуйста, войдите в систему для доступа к этой странице.'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        """Загрузка пользователя по ID"""
        try:
            # Здесь нужно будет добавить метод get_user_by_id в AuthSystem
            # Пока возвращаем None
            return None
        except Exception as e:
            logging.error(f"Ошибка загрузки пользователя {user_id}: {e}")
            return None
    
    return login_manager

def role_required(role):
    """Декоратор для проверки роли"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            
            if current_user.role != role and current_user.role != 'super_admin':
                flash('Недостаточно прав для доступа к этой странице.', 'error')
                return redirect(url_for('main.dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    """Декоратор для админских функций"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        
        if current_user.role not in ['admin', 'super_admin']:
            flash('Требуются права администратора.', 'error')
            return redirect(url_for('main.dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function

def super_admin_required(f):
    """Декоратор для супер-админских функций"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        
        if current_user.role != 'super_admin':
            flash('Требуются права супер-администратора.', 'error')
            return redirect(url_for('main.dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function

def subscription_required(tier):
    """Декоратор для проверки подписки"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            
            # Здесь нужно будет добавить проверку подписки
            # Пока пропускаем
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def two_factor_required(f):
    """Декоратор для функций, требующих 2FA"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        
        if current_user.two_factor_enabled:
            if not session.get('two_factor_verified'):
                return redirect(url_for('auth.verify_2fa'))
        
        return f(*args, **kwargs)
    return decorated_function

def get_user_permissions(user_role: str) -> dict:
    """Получение прав пользователя по роли"""
    return auth_system.roles.get(user_role, {})

def check_permission(user_role: str, permission: str) -> bool:
    """Проверка права пользователя"""
    permissions = get_user_permissions(user_role)
    
    if 'all' in permissions.get('permissions', []):
        return True
    
    return permission in permissions.get('permissions', [])

def get_user_notifications(user_id: int) -> list:
    """Получение доступных уведомлений для пользователя"""
    return auth_system.get_user_notifications(user_id)

def can_access_telegram(user_role: str) -> bool:
    """Проверка доступа к Telegram"""
    permissions = get_user_permissions(user_role)
    return permissions.get('telegram_access', False)

def can_access_dashboard(user_role: str) -> bool:
    """Проверка доступа к дашборду"""
    permissions = get_user_permissions(user_role)
    return permissions.get('dashboard_access', False)

def can_access_api(user_role: str) -> bool:
    """Проверка доступа к API"""
    permissions = get_user_permissions(user_role)
    return permissions.get('api_access', False)






