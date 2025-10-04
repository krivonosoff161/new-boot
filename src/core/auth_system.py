#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Authentication System
Enhanced Trading System v3.0 Commercial
"""

import os
import hashlib
import secrets
import base64
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from cryptography.fernet import Fernet
import sqlite3
from passlib.hash import bcrypt
import pyotp
import qrcode
from io import BytesIO
import base64

@dataclass
class User:
    """Пользователь системы"""
    id: int
    username: str
    email: str
    password_hash: str
    role: str
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]
    login_attempts: int
    two_factor_enabled: bool
    two_factor_secret: Optional[str]
    backup_codes: List[str]

@dataclass
class LinkedAccount:
    """Привязанный аккаунт"""
    id: int
    user_id: int
    account_type: str  # telegram, email, phone
    account_value: str
    is_verified: bool
    is_primary: bool
    verified_at: Optional[datetime]

@dataclass
class UserSession:
    """Сессия пользователя"""
    id: int
    user_id: int
    session_token: str
    expires_at: datetime
    ip_address: str
    user_agent: str
    is_active: bool
    created_at: datetime

class AuthSystem:
    """
    Система аутентификации с поддержкой:
    - Веб-входа (username/email + password)
    - Ролей и прав доступа
    - 2FA (TOTP, Telegram, Email, SMS)
    - Привязки аккаунтов
    - Уведомлений по тарифам
    """
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            parent_dir = os.path.dirname(current_dir)
            self.db_path = os.path.join(parent_dir, '..', 'data', 'database', 'auth_users.db')
        else:
            self.db_path = db_path
        
        self.logger = logging.getLogger(__name__)
        self.init_database()
        
        # Мастер-ключ для шифрования
        self.master_key = self._get_or_create_master_key()
        
        # Роли и их права
        self.roles = {
            'super_admin': {
                'name': 'Super Admin',
                'permissions': ['all'],
                'telegram_access': True,
                'dashboard_access': True,
                'api_access': True,
                'max_count': 2
            },
            'admin': {
                'name': 'Admin',
                'permissions': ['user_management', 'system_settings'],
                'telegram_access': True,
                'dashboard_access': True,
                'api_access': True,
                'max_count': 0
            },
            'user': {
                'name': 'User',
                'permissions': ['basic_trading'],
                'telegram_access': False,
                'dashboard_access': True,
                'api_access': False,
                'max_count': 0
            }
        }
        
        # Тарифы и уведомления
        self.subscription_tiers = {
            'free': {
                'name': 'Free',
                'notifications': [],
                'price': 0
            },
            'basic': {
                'name': 'Basic',
                'notifications': ['telegram'],
                'price': 29.99
            },
            'premium': {
                'name': 'Premium',
                'notifications': ['telegram', 'email'],
                'price': 99.99
            },
            'professional': {
                'name': 'Professional',
                'notifications': ['telegram', 'email', 'sms'],
                'price': 299.99
            },
            'enterprise': {
                'name': 'Enterprise',
                'notifications': ['telegram', 'email', 'sms', 'push', 'webhook'],
                'price': 999.99
            }
        }
    
    def _get_or_create_master_key(self) -> bytes:
        """Получение или создание мастер-ключа"""
        master_key_path = os.path.join(os.path.dirname(self.db_path), '.master_key')
        
        if os.path.exists(master_key_path):
            with open(master_key_path, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(master_key_path, 'wb') as f:
                f.write(key)
            return key
    
    def init_database(self):
        """Инициализация базы данных"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Таблица пользователей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT DEFAULT 'user',
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    login_attempts INTEGER DEFAULT 0,
                    two_factor_enabled BOOLEAN DEFAULT 0,
                    two_factor_secret TEXT,
                    backup_codes TEXT
                )
            ''')
            
            # Таблица привязанных аккаунтов
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS linked_accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    account_type TEXT NOT NULL,
                    account_value TEXT NOT NULL,
                    is_verified BOOLEAN DEFAULT 0,
                    is_primary BOOLEAN DEFAULT 0,
                    verified_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # Таблица сессий
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    session_token TEXT UNIQUE NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    ip_address TEXT,
                    user_agent TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # Таблица API ключей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS exchange_keys (
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
            
            # Таблица уведомлений
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    type TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    message TEXT NOT NULL,
                    sent_at TIMESTAMP,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # Таблица подписок
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    tier TEXT NOT NULL,
                    status TEXT NOT NULL,
                    start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    end_date TIMESTAMP,
                    auto_renew BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            conn.commit()
    
    def register_user(self, username: str, email: str, password: str, 
                     role: str = 'user') -> Tuple[bool, str]:
        """
        Регистрация нового пользователя
        
        Args:
            username: Имя пользователя
            email: Email
            password: Пароль
            role: Роль пользователя
            
        Returns:
            (success, message)
        """
        try:
            # Проверяем лимиты ролей
            if role in ['super_admin', 'admin']:
                current_count = self._get_role_count(role)
                max_count = self.roles[role]['max_count']
                if max_count > 0 and current_count >= max_count:
                    return False, f"Достигнут лимит ролей {role}: {max_count}"
            
            # Проверяем уникальность
            if self._user_exists(username, email):
                return False, "Пользователь с таким именем или email уже существует"
            
            # Хешируем пароль
            password_hash = bcrypt.hash(password)
            
            # Создаем пользователя
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO users (username, email, password_hash, role)
                    VALUES (?, ?, ?, ?)
                ''', (username, email, password_hash, role))
                
                user_id = cursor.lastrowid
                
                # Создаем подписку по умолчанию
                cursor.execute('''
                    INSERT INTO user_subscriptions (user_id, tier, status)
                    VALUES (?, 'free', 'active')
                ''', (user_id,))
                
                conn.commit()
            
            # Логируем регистрацию
            self.logger.info(f"Пользователь {username} зарегистрирован с ролью {role}")
            
            return True, "Пользователь успешно зарегистрирован"
            
        except Exception as e:
            self.logger.error(f"Ошибка регистрации пользователя: {e}")
            return False, f"Ошибка регистрации: {str(e)}"
    
    def authenticate_user(self, username_or_email: str, password: str, 
                         ip_address: str = None, user_agent: str = None) -> Tuple[bool, Optional[User], str]:
        """
        Аутентификация пользователя
        
        Args:
            username_or_email: Имя пользователя или email
            password: Пароль
            ip_address: IP адрес
            user_agent: User Agent
            
        Returns:
            (success, user, message)
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Ищем пользователя
                cursor.execute('''
                    SELECT * FROM users 
                    WHERE (username = ? OR email = ?) AND is_active = 1
                ''', (username_or_email, username_or_email))
                
                result = cursor.fetchone()
                if not result:
                    return False, None, "Пользователь не найден или неактивен"
                
                user = self._row_to_user(result)
                
                # Проверяем пароль
                if not bcrypt.verify(password, user.password_hash):
                    # Увеличиваем счетчик попыток
                    self._increment_login_attempts(user.id)
                    return False, None, "Неверный пароль"
                
                # Сбрасываем счетчик попыток
                self._reset_login_attempts(user.id)
                
                # Обновляем последний вход
                self._update_last_login(user.id)
                
                # Логируем вход
                self.logger.info(f"Пользователь {user.username} вошел в систему")
                
                return True, user, "Успешная аутентификация"
                
        except Exception as e:
            self.logger.error(f"Ошибка аутентификации: {e}")
            return False, None, f"Ошибка аутентификации: {str(e)}"
    
    def create_session(self, user_id: int, ip_address: str = None, 
                      user_agent: str = None, remember_me: bool = False) -> str:
        """
        Создание сессии пользователя
        
        Args:
            user_id: ID пользователя
            ip_address: IP адрес
            user_agent: User Agent
            remember_me: Запомнить устройство
            
        Returns:
            session_token
        """
        # Определяем срок жизни сессии
        if remember_me:
            expires_at = datetime.now() + timedelta(days=30)
        else:
            expires_at = datetime.now() + timedelta(days=7)
        
        # Генерируем токен сессии
        session_token = secrets.token_urlsafe(32)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO user_sessions 
                (user_id, session_token, expires_at, ip_address, user_agent)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, session_token, expires_at, ip_address, user_agent))
            conn.commit()
        
        return session_token
    
    def validate_session(self, session_token: str) -> Tuple[bool, Optional[User]]:
        """
        Валидация сессии
        
        Args:
            session_token: Токен сессии
            
        Returns:
            (valid, user)
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT u.* FROM users u
                    JOIN user_sessions s ON u.id = s.user_id
                    WHERE s.session_token = ? AND s.is_active = 1 
                    AND s.expires_at > ? AND u.is_active = 1
                ''', (session_token, datetime.now()))
                
                result = cursor.fetchone()
                if result:
                    return True, self._row_to_user(result)
                else:
                    return False, None
                    
        except Exception as e:
            self.logger.error(f"Ошибка валидации сессии: {e}")
            return False, None
    
    def setup_two_factor(self, user_id: int) -> Tuple[bool, str, str]:
        """
        Настройка 2FA для пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            (success, qr_code, backup_codes)
        """
        try:
            # Генерируем секретный ключ
            secret = pyotp.random_base32()
            
            # Генерируем backup коды
            backup_codes = [secrets.token_hex(4) for _ in range(10)]
            
            # Создаем QR код
            totp = pyotp.TOTP(secret)
            qr_code = totp.provisioning_uri(
                name=f"user_{user_id}",
                issuer_name="Enhanced Trading System"
            )
            
            # Сохраняем в базу
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users 
                    SET two_factor_secret = ?, backup_codes = ?
                    WHERE id = ?
                ''', (secret, json.dumps(backup_codes), user_id))
                conn.commit()
            
            return True, qr_code, json.dumps(backup_codes)
            
        except Exception as e:
            self.logger.error(f"Ошибка настройки 2FA: {e}")
            return False, "", ""
    
    def verify_two_factor(self, user_id: int, code: str) -> bool:
        """
        Проверка 2FA кода
        
        Args:
            user_id: ID пользователя
            code: 2FA код
            
        Returns:
            valid
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT two_factor_secret FROM users WHERE id = ?
                ''', (user_id,))
                
                result = cursor.fetchone()
                if not result or not result[0]:
                    return False
                
                secret = result[0]
                totp = pyotp.TOTP(secret)
                
                return totp.verify(code)
                
        except Exception as e:
            self.logger.error(f"Ошибка проверки 2FA: {e}")
            return False
    
    def link_account(self, user_id: int, account_type: str, 
                    account_value: str, is_primary: bool = False) -> Tuple[bool, str]:
        """
        Привязка аккаунта к пользователю
        
        Args:
            user_id: ID пользователя
            account_type: Тип аккаунта (telegram, email, phone)
            account_value: Значение аккаунта
            is_primary: Основной аккаунт
            
        Returns:
            (success, message)
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Проверяем, не привязан ли уже
                cursor.execute('''
                    SELECT id FROM linked_accounts 
                    WHERE user_id = ? AND account_type = ? AND account_value = ?
                ''', (user_id, account_type, account_value))
                
                if cursor.fetchone():
                    return False, "Аккаунт уже привязан"
                
                # Привязываем аккаунт
                cursor.execute('''
                    INSERT INTO linked_accounts 
                    (user_id, account_type, account_value, is_primary)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, account_type, account_value, is_primary))
                
                conn.commit()
            
            return True, "Аккаунт успешно привязан"
            
        except Exception as e:
            self.logger.error(f"Ошибка привязки аккаунта: {e}")
            return False, f"Ошибка привязки: {str(e)}"
    
    def get_user_notifications(self, user_id: int) -> List[str]:
        """
        Получение доступных уведомлений для пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Список доступных каналов уведомлений
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT tier FROM user_subscriptions 
                    WHERE user_id = ? AND status = 'active'
                ''', (user_id,))
                
                result = cursor.fetchone()
                if result:
                    tier = result[0]
                    return self.subscription_tiers.get(tier, {}).get('notifications', [])
                else:
                    return []
                    
        except Exception as e:
            self.logger.error(f"Ошибка получения уведомлений: {e}")
            return []
    
    def _user_exists(self, username: str, email: str) -> bool:
        """Проверка существования пользователя"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id FROM users 
                WHERE username = ? OR email = ?
            ''', (username, email))
            return cursor.fetchone() is not None
    
    def _get_role_count(self, role: str) -> int:
        """Получение количества пользователей с ролью"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM users WHERE role = ?', (role,))
            return cursor.fetchone()[0]
    
    def _increment_login_attempts(self, user_id: int):
        """Увеличение счетчика попыток входа"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users SET login_attempts = login_attempts + 1 
                WHERE id = ?
            ''', (user_id,))
            conn.commit()
    
    def _reset_login_attempts(self, user_id: int):
        """Сброс счетчика попыток входа"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users SET login_attempts = 0 
                WHERE id = ?
            ''', (user_id,))
            conn.commit()
    
    def _update_last_login(self, user_id: int):
        """Обновление времени последнего входа"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users SET last_login = ? 
                WHERE id = ?
            ''', (datetime.now(), user_id))
            conn.commit()
    
    def _row_to_user(self, row) -> User:
        """Преобразование строки БД в объект User"""
        return User(
            id=row[0],
            username=row[1],
            email=row[2],
            password_hash=row[3],
            role=row[4],
            is_active=bool(row[5]),
            created_at=datetime.fromisoformat(row[6]),
            last_login=datetime.fromisoformat(row[7]) if row[7] else None,
            login_attempts=row[8],
            two_factor_enabled=bool(row[9]),
            two_factor_secret=row[10],
            backup_codes=json.loads(row[11]) if row[11] else []
        )

# Глобальный экземпляр системы аутентификации
auth_system = AuthSystem()



















