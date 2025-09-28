#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Exchange Mode Manager
Модуль для управления режимами работы с биржами (демо/реальные)
"""

import json
import os
from typing import Dict, Any, Optional
from loguru import logger

class ExchangeModeManager:
    """
    Менеджер режимов работы с биржами
    
    Функции:
    - Переключение между демо и реальными режимами
    - Хранение конфигураций для разных бирж
    - Автоматическое применение правильных параметров
    """
    
    def __init__(self, config_path: str = "data/exchange_modes.json"):
        """
        Инициализация менеджера режимов
        
        Args:
            config_path: Путь к файлу конфигурации режимов
        """
        self.config_path = config_path
        self.modes = self._load_modes()
        self._ensure_config_exists()
        
        logger.info("✅ Exchange Mode Manager инициализирован")
    
    def _ensure_config_exists(self):
        """Создание файла конфигурации если его нет"""
        if not os.path.exists(self.config_path):
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            default_config = {
                "exchanges": {
                    "okx": {
                        "demo": {
                            "sandbox": False,  # OKX не поддерживает sandbox
                            "options": {
                                "sandboxMode": True,
                                "defaultType": "spot",
                                "demo": True
                            },
                            "urls": {
                                "api": {
                                    "public": "https://www.okx.com",
                                    "private": "https://www.okx.com"
                                }
                            }
                        },
                        "live": {
                            "sandbox": False,
                            "options": {
                                "sandboxMode": False,
                                "defaultType": "spot",
                                "demo": False
                            },
                            "urls": {
                                "api": {
                                    "public": "https://www.okx.com",
                                    "private": "https://www.okx.com"
                                }
                            }
                        }
                    },
                    "binance": {
                        "demo": {
                            "sandbox": True,
                            "options": {
                                "defaultType": "spot"
                            }
                        },
                        "live": {
                            "sandbox": False,
                            "options": {
                                "defaultType": "spot"
                            }
                        }
                    },
                    "bybit": {
                        "demo": {
                            "sandbox": True,
                            "options": {
                                "defaultType": "spot"
                            }
                        },
                        "live": {
                            "sandbox": False,
                            "options": {
                                "defaultType": "spot"
                            }
                        }
                    }
                },
                "default_mode": "demo"  # По умолчанию демо режим
            }
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            
            logger.info(f"📁 Создан файл конфигурации режимов: {self.config_path}")
    
    def _load_modes(self) -> Dict[str, Any]:
        """Загрузка конфигурации режимов"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки конфигурации режимов: {e}")
            return {}
    
    def _save_modes(self):
        """Сохранение конфигурации режимов"""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.modes, f, indent=2, ensure_ascii=False)
            logger.debug("💾 Конфигурация режимов сохранена")
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения конфигурации режимов: {e}")
    
    def get_exchange_config(self, exchange_name: str, mode: str = "demo") -> Dict[str, Any]:
        """
        Получение конфигурации для биржи
        
        Args:
            exchange_name: Название биржи (okx, binance, bybit)
            mode: Режим (demo, live, sandbox)
            
        Returns:
            Словарь с конфигурацией для ccxt
        """
        try:
            # Маппинг режимов: sandbox -> demo
            if mode == "sandbox":
                mode = "demo"
            
            if exchange_name not in self.modes.get("exchanges", {}):
                logger.warning(f"⚠️ Неизвестная биржа: {exchange_name}, используем базовую конфигурацию")
                return self._get_default_config(exchange_name, mode)
            
            exchange_modes = self.modes["exchanges"][exchange_name]
            
            if mode not in exchange_modes:
                logger.warning(f"⚠️ Неизвестный режим {mode} для {exchange_name}, используем demo")
                mode = "demo"
            
            config = exchange_modes[mode].copy()
            
            # Добавляем enableRateLimit по умолчанию
            config.setdefault("enableRateLimit", True)
            
            logger.debug(f"🔧 Конфигурация {exchange_name} ({mode}): {config}")
            return config
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения конфигурации {exchange_name} ({mode}): {e}")
            return self._get_default_config(exchange_name, mode)
    
    def _get_default_config(self, exchange_name: str, mode: str) -> Dict[str, Any]:
        """Получение базовой конфигурации"""
        if mode == "demo":
            return {
                "sandbox": True,
                "enableRateLimit": True,
                "options": {
                    "defaultType": "spot"
                }
            }
        else:
            return {
                "sandbox": False,
                "enableRateLimit": True,
                "options": {
                    "defaultType": "spot"
                }
            }
    
    def create_exchange_instance(self, exchange_name: str, api_key: str, secret: str, 
                               passphrase: str = None, mode: str = "demo") -> Any:
        """
        Создание экземпляра биржи с правильной конфигурацией
        
        Args:
            exchange_name: Название биржи
            api_key: API ключ
            secret: Секретный ключ
            passphrase: Пароль (для OKX)
            mode: Режим (demo, live, sandbox)
            
        Returns:
            Экземпляр биржи ccxt
        """
        try:
            import ccxt
            
            # Маппинг режимов: sandbox -> demo
            if mode == "sandbox":
                mode = "demo"
            
            # Получаем конфигурацию
            config = self.get_exchange_config(exchange_name, mode)
            
            # Добавляем ключи аутентификации
            config.update({
                'apiKey': api_key,
                'secret': secret
            })
            
            # Добавляем passphrase/password для OKX
            if passphrase:
                if exchange_name == 'okx':
                    config['password'] = passphrase  # OKX использует 'password'
                else:
                    config['passphrase'] = passphrase  # Остальные используют 'passphrase'
            
            # Получаем класс биржи
            if exchange_name in ccxt.exchanges:
                exchange_class = getattr(ccxt, exchange_name)
                exchange = exchange_class(config)
                
                logger.info(f"✅ Создан экземпляр {exchange_name} в режиме {mode}")
                logger.debug(f"🔧 Конфигурация: {config}")
                return exchange
            else:
                raise ValueError(f"Неподдерживаемая биржа: {exchange_name}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка создания экземпляра {exchange_name}: {e}")
            raise
    
    def set_default_mode(self, mode: str):
        """
        Установка режима по умолчанию
        
        Args:
            mode: Режим по умолчанию (demo, live)
        """
        if mode not in ["demo", "live"]:
            logger.error(f"❌ Неверный режим: {mode}. Используйте 'demo' или 'live'")
            return
        
        self.modes["default_mode"] = mode
        self._save_modes()
        logger.info(f"🎯 Установлен режим по умолчанию: {mode}")
    
    def get_default_mode(self) -> str:
        """Получение режима по умолчанию"""
        return self.modes.get("default_mode", "demo")
    
    def get_supported_exchanges(self) -> list:
        """Получение списка поддерживаемых бирж"""
        return list(self.modes.get("exchanges", {}).keys())
    
    def get_exchange_modes(self, exchange_name: str) -> list:
        """Получение доступных режимов для биржи"""
        if exchange_name in self.modes.get("exchanges", {}):
            return list(self.modes["exchanges"][exchange_name].keys())
        return ["demo", "live"]  # По умолчанию
    
    def update_exchange_config(self, exchange_name: str, mode: str, config: Dict[str, Any]):
        """
        Обновление конфигурации биржи
        
        Args:
            exchange_name: Название биржи
            mode: Режим
            config: Новая конфигурация
        """
        try:
            if "exchanges" not in self.modes:
                self.modes["exchanges"] = {}
            
            if exchange_name not in self.modes["exchanges"]:
                self.modes["exchanges"][exchange_name] = {}
            
            self.modes["exchanges"][exchange_name][mode] = config
            self._save_modes()
            
            logger.info(f"✅ Обновлена конфигурация {exchange_name} ({mode})")
            
        except Exception as e:
            logger.error(f"❌ Ошибка обновления конфигурации {exchange_name} ({mode}): {e}")
    
    def get_mode_info(self, exchange_name: str, mode: str) -> str:
        """
        Получение информации о режиме
        
        Args:
            exchange_name: Название биржи
            mode: Режим
            
        Returns:
            Описание режима
        """
        if mode == "demo":
            return f"🎮 Демо-режим {exchange_name.upper()}: виртуальная торговля без реальных средств"
        elif mode == "live":
            return f"💰 Реальный режим {exchange_name.upper()}: торговля реальными средствами"
        else:
            return f"❓ Неизвестный режим {mode} для {exchange_name}"

# Глобальный экземпляр
exchange_mode_manager = ExchangeModeManager()
