#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Security Manager
Enhanced Trading System v3.0 Commercial
"""

import os
import hashlib
import secrets
from typing import Dict, Any, Optional
from loguru import logger

class SecurityManager:
    """Менеджер безопасности системы"""
    
    def __init__(self):
        """Инициализация менеджера безопасности"""
        self.master_key_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', '.master_key')
        self.master_key = self._load_or_generate_master_key()
    
    def _load_or_generate_master_key(self) -> bytes:
        """
        Загрузка или генерация мастер-ключа
        
        Returns:
            Мастер-ключ в виде байтов
        """
        try:
            if os.path.exists(self.master_key_path):
                with open(self.master_key_path, 'rb') as f:
                    key = f.read()
                logger.info("Мастер-ключ загружен")
                return key
            else:
                # Генерируем новый мастер-ключ
                key = secrets.token_bytes(32)
                
                # Создаем директорию если не существует
                os.makedirs(os.path.dirname(self.master_key_path), exist_ok=True)
                
                # Сохраняем ключ
                with open(self.master_key_path, 'wb') as f:
                    f.write(key)
                
                logger.info("Новый мастер-ключ сгенерирован и сохранен")
                return key
                
        except Exception as e:
            logger.error(f"Ошибка работы с мастер-ключом: {e}")
            # Возвращаем случайный ключ в случае ошибки
            return secrets.token_bytes(32)
    
    def hash_password(self, password: str) -> str:
        """
        Хеширование пароля
        
        Args:
            password: Пароль для хеширования
            
        Returns:
            Хеш пароля
        """
        salt = secrets.token_hex(16)
        password_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
        return f"{salt}:{password_hash.hex()}"
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """
        Проверка пароля
        
        Args:
            password: Пароль для проверки
            password_hash: Хеш пароля
            
        Returns:
            True если пароль верный, False в противном случае
        """
        try:
            salt, hash_part = password_hash.split(':')
            password_hash_check = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
            return password_hash_check.hex() == hash_part
        except Exception as e:
            logger.error(f"Ошибка проверки пароля: {e}")
            return False
    
    def generate_token(self, length: int = 32) -> str:
        """
        Генерация токена
        
        Args:
            length: Длина токена
            
        Returns:
            Сгенерированный токен
        """
        return secrets.token_urlsafe(length)
    
    def encrypt_sensitive_data(self, data: str) -> str:
        """
        Шифрование чувствительных данных
        
        Args:
            data: Данные для шифрования
            
        Returns:
            Зашифрованные данные
        """
        try:
            from cryptography.fernet import Fernet
            
            # Создаем ключ из мастер-ключа
            key = Fernet.generate_key()
            cipher_suite = Fernet(key)
            
            # Шифруем данные
            encrypted_data = cipher_suite.encrypt(data.encode('utf-8'))
            
            # Возвращаем ключ и зашифрованные данные
            return f"{key.decode()}:{encrypted_data.decode()}"
            
        except Exception as e:
            logger.error(f"Ошибка шифрования данных: {e}")
            return data
    
    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """
        Расшифровка чувствительных данных
        
        Args:
            encrypted_data: Зашифрованные данные
            
        Returns:
            Расшифрованные данные
        """
        try:
            from cryptography.fernet import Fernet
            
            key, data = encrypted_data.split(':')
            cipher_suite = Fernet(key.encode())
            
            decrypted_data = cipher_suite.decrypt(data.encode())
            return decrypted_data.decode('utf-8')
            
        except Exception as e:
            logger.error(f"Ошибка расшифровки данных: {e}")
            return encrypted_data
    
    def validate_api_key(self, api_key: str) -> bool:
        """
        Валидация API ключа
        
        Args:
            api_key: API ключ для проверки
            
        Returns:
            True если ключ валидный, False в противном случае
        """
        # Простая проверка формата API ключа
        if not api_key or len(api_key) < 20:
            return False
        
        # Дополнительные проверки можно добавить здесь
        return True
    
    def sanitize_input(self, input_data: str) -> str:
        """
        Очистка пользовательского ввода
        
        Args:
            input_data: Входные данные
            
        Returns:
            Очищенные данные
        """
        if not input_data:
            return ""
        
        # Удаляем потенциально опасные символы
        dangerous_chars = ['<', '>', '"', "'", '&', ';', '(', ')', '|', '`', '$']
        sanitized = input_data
        
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, '')
        
        return sanitized.strip()
    
    def check_permission(self, user_role: str, required_permission: str) -> bool:
        """
        Проверка разрешений пользователя
        
        Args:
            user_role: Роль пользователя
            required_permission: Требуемое разрешение
            
        Returns:
            True если разрешение есть, False в противном случае
        """
        permissions = {
            'super_admin': ['all'],
            'admin': ['read', 'write', 'execute', 'manage_users'],
            'user': ['read', 'execute'],
            'free': ['read']
        }
        
        user_permissions = permissions.get(user_role, [])
        
        if 'all' in user_permissions:
            return True
        
        return required_permission in user_permissions



















