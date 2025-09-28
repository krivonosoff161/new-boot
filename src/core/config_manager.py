#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration Manager
Enhanced Trading System v3.0 Commercial
"""

import json
import os
from typing import Dict, Any, Optional
from loguru import logger

class ConfigManager:
    """Менеджер конфигурации системы"""
    
    def __init__(self, config_path: str = None):
        """
        Инициализация менеджера конфигурации
        
        Args:
            config_path: Путь к файлу конфигурации
        """
        if config_path is None:
            # Определяем путь к конфигурации относительно корня проекта
            current_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            config_path = os.path.join(current_dir, 'config', 'bot_config.json')
        
        self.config_path = config_path
        self.config = {}
        self.load_config()
    
    def load_config(self) -> None:
        """Загрузка конфигурации из файла"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                logger.info(f"Конфигурация загружена из {self.config_path}")
            else:
                logger.warning(f"Файл конфигурации не найден: {self.config_path}")
                self.config = self._get_default_config()
        except Exception as e:
            logger.error(f"Ошибка загрузки конфигурации: {e}")
            self.config = self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Получение конфигурации по умолчанию"""
        return {
            "telegram": {
                "bot_token": "",
                "admin_ids": []
            },
            "trading": {
                "max_bots_per_user": 3,
                "default_risk_per_trade": 0.02
            },
            "database": {
                "path": "data/database/secure_users.db"
            },
            "logging": {
                "level": "INFO",
                "file": "logs/system.log"
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Получение значения конфигурации
        
        Args:
            key: Ключ конфигурации (поддерживает вложенные ключи через точку)
            default: Значение по умолчанию
            
        Returns:
            Значение конфигурации или значение по умолчанию
        """
        keys = key.split('.')
        value = self.config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any) -> None:
        """
        Установка значения конфигурации
        
        Args:
            key: Ключ конфигурации (поддерживает вложенные ключи через точку)
            value: Значение для установки
        """
        keys = key.split('.')
        config = self.config
        
        # Создаем вложенную структуру
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # Устанавливаем значение
        config[keys[-1]] = value
    
    def save_config(self) -> bool:
        """
        Сохранение конфигурации в файл
        
        Returns:
            True если сохранение успешно, False в противном случае
        """
        try:
            # Создаем директорию если не существует
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Конфигурация сохранена в {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"Ошибка сохранения конфигурации: {e}")
            return False
    
    def reload_config(self) -> None:
        """Перезагрузка конфигурации из файла"""
        self.load_config()
    
    def get_telegram_config(self) -> Dict[str, Any]:
        """Получение конфигурации Telegram"""
        return self.get('telegram', {})
    
    def get_trading_config(self) -> Dict[str, Any]:
        """Получение конфигурации торговли"""
        return self.get('trading', {})
    
    def get_database_config(self) -> Dict[str, Any]:
        """Получение конфигурации базы данных"""
        return self.get('database', {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Получение конфигурации логирования"""
        return self.get('logging', {})
    
    def get_config(self) -> Dict[str, Any]:
        """Получение всей конфигурации"""
        return self.config
