#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Plugin Manager - Система управления плагинами
Enhanced Trading System v3.0 Commercial
"""

import os
import sys
import importlib
import json
from typing import Dict, List, Optional, Any, Type
from abc import ABC, abstractmethod

class TradingBot(ABC):
    """Базовый класс для торговых ботов"""
    
    @abstractmethod
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.running = False
    
    @abstractmethod
    async def start(self):
        """Запуск бота"""
        pass
    
    @abstractmethod
    async def stop(self):
        """Остановка бота"""
        pass
    
    @abstractmethod
    async def get_status(self) -> Dict[str, Any]:
        """Получение статуса бота"""
        pass

class Exchange(ABC):
    """Базовый класс для бирж"""
    
    @abstractmethod
    def __init__(self, api_key: str, secret_key: str, passphrase: str = None):
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase
    
    @abstractmethod
    async def get_balance(self) -> Dict[str, float]:
        """Получение баланса"""
        pass
    
    @abstractmethod
    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """Получение тикера"""
        pass
    
    @abstractmethod
    async def place_order(self, symbol: str, side: str, amount: float, price: float = None) -> Dict[str, Any]:
        """Размещение ордера"""
        pass

class PluginManager:
    """
    Менеджер плагинов для расширения функциональности
    
    Поддерживает:
    - Новые торговые боты
    - Новые биржи
    - Новые стратегии
    - Новые индикаторы
    """
    
    def __init__(self, plugins_dir: str = "src/plugins"):
        self.plugins_dir = plugins_dir
        self.bots: Dict[str, Type[TradingBot]] = {}
        self.exchanges: Dict[str, Type[Exchange]] = {}
        self.strategies: Dict[str, Any] = {}
        self.indicators: Dict[str, Any] = {}
        
        # Создаем папку для плагинов
        os.makedirs(plugins_dir, exist_ok=True)
        os.makedirs(f"{plugins_dir}/bots", exist_ok=True)
        os.makedirs(f"{plugins_dir}/exchanges", exist_ok=True)
        os.makedirs(f"{plugins_dir}/strategies", exist_ok=True)
        os.makedirs(f"{plugins_dir}/indicators", exist_ok=True)
        
        # Загружаем плагины
        self.load_plugins()
    
    def load_plugins(self):
        """Загрузка всех плагинов"""
        self.load_bots()
        self.load_exchanges()
        self.load_strategies()
        self.load_indicators()
    
    def load_bots(self):
        """Загрузка торговых ботов"""
        bots_dir = f"{self.plugins_dir}/bots"
        
        for filename in os.listdir(bots_dir):
            if filename.endswith('.py') and not filename.startswith('_'):
                module_name = filename[:-3]
                try:
                    spec = importlib.util.spec_from_file_location(
                        f"plugins.bots.{module_name}",
                        os.path.join(bots_dir, filename)
                    )
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # Ищем класс бота
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (isinstance(attr, type) and 
                            issubclass(attr, TradingBot) and 
                            attr != TradingBot):
                            self.bots[module_name] = attr
                            print(f"✅ Загружен бот: {module_name}")
                            
                except Exception as e:
                    print(f"❌ Ошибка загрузки бота {module_name}: {e}")
    
    def load_exchanges(self):
        """Загрузка бирж"""
        exchanges_dir = f"{self.plugins_dir}/exchanges"
        
        for filename in os.listdir(exchanges_dir):
            if filename.endswith('.py') and not filename.startswith('_'):
                module_name = filename[:-3]
                try:
                    spec = importlib.util.spec_from_file_location(
                        f"plugins.exchanges.{module_name}",
                        os.path.join(exchanges_dir, filename)
                    )
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # Ищем класс биржи
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (isinstance(attr, type) and 
                            issubclass(attr, Exchange) and 
                            attr != Exchange):
                            self.exchanges[module_name] = attr
                            print(f"✅ Загружена биржа: {module_name}")
                            
                except Exception as e:
                    print(f"❌ Ошибка загрузки биржи {module_name}: {e}")
    
    def load_strategies(self):
        """Загрузка стратегий"""
        strategies_dir = f"{self.plugins_dir}/strategies"
        
        for filename in os.listdir(strategies_dir):
            if filename.endswith('.py') and not filename.startswith('_'):
                module_name = filename[:-3]
                try:
                    spec = importlib.util.spec_from_file_location(
                        f"plugins.strategies.{module_name}",
                        os.path.join(strategies_dir, filename)
                    )
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    self.strategies[module_name] = module
                    print(f"✅ Загружена стратегия: {module_name}")
                    
                except Exception as e:
                    print(f"❌ Ошибка загрузки стратегии {module_name}: {e}")
    
    def load_indicators(self):
        """Загрузка индикаторов"""
        indicators_dir = f"{self.plugins_dir}/indicators"
        
        for filename in os.listdir(indicators_dir):
            if filename.endswith('.py') and not filename.startswith('_'):
                module_name = filename[:-3]
                try:
                    spec = importlib.util.spec_from_file_location(
                        f"plugins.indicators.{module_name}",
                        os.path.join(indicators_dir, filename)
                    )
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    self.indicators[module_name] = module
                    print(f"✅ Загружен индикатор: {module_name}")
                    
                except Exception as e:
                    print(f"❌ Ошибка загрузки индикатора {module_name}: {e}")
    
    def create_bot(self, bot_type: str, config: Dict[str, Any]) -> Optional[TradingBot]:
        """Создание экземпляра бота"""
        if bot_type not in self.bots:
            print(f"❌ Бот {bot_type} не найден")
            return None
        
        try:
            bot_class = self.bots[bot_type]
            return bot_class(config)
        except Exception as e:
            print(f"❌ Ошибка создания бота {bot_type}: {e}")
            return None
    
    def create_exchange(self, exchange_type: str, api_key: str, 
                       secret_key: str, passphrase: str = None) -> Optional[Exchange]:
        """Создание экземпляра биржи"""
        if exchange_type not in self.exchanges:
            print(f"❌ Биржа {exchange_type} не найдена")
            return None
        
        try:
            exchange_class = self.exchanges[exchange_type]
            return exchange_class(api_key, secret_key, passphrase)
        except Exception as e:
            print(f"❌ Ошибка создания биржи {exchange_type}: {e}")
            return None
    
    def get_available_bots(self) -> List[str]:
        """Получение списка доступных ботов"""
        return list(self.bots.keys())
    
    def get_available_exchanges(self) -> List[str]:
        """Получение списка доступных бирж"""
        return list(self.exchanges.keys())
    
    def get_available_strategies(self) -> List[str]:
        """Получение списка доступных стратегий"""
        return list(self.strategies.keys())
    
    def get_available_indicators(self) -> List[str]:
        """Получение списка доступных индикаторов"""
        return list(self.indicators.keys())
    
    def reload_plugins(self):
        """Перезагрузка всех плагинов"""
        self.bots.clear()
        self.exchanges.clear()
        self.strategies.clear()
        self.indicators.clear()
        self.load_plugins()

# Глобальный экземпляр менеджера плагинов
plugin_manager = PluginManager()


















