#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
User Bot Manager - управление ботами для конкретного пользователя
Enhanced Trading System v3.0
"""

import os
import sys
import subprocess
import time
import logging
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
import threading
import asyncio

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UserBotManager:
    """Менеджер ботов для конкретного пользователя"""
    
    def __init__(self, user_id: int, api_key: str, secret_key: str, passphrase: str):
        """
        Инициализация менеджера ботов для пользователя
        
        Args:
            user_id: ID пользователя
            api_key: API ключ OKX
            secret_key: Secret ключ OKX
            passphrase: Passphrase OKX
        """
        self.user_id = user_id
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase
        
        # Получаем абсолютный путь к user_data
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        self.user_data_path = os.path.join(parent_dir, 'user_data')
        
        # Создаем конфигурацию для пользователя
        self.user_config = self._create_user_config()
        
        # Состояние ботов пользователя
        self.user_bots = {
            'grid': {
                'name': f'Grid Bot User {user_id}',
                'process': None,
                'status': 'stopped',
                'started_at': None,
                'last_heartbeat': None,
                'config_file': os.path.join(self.user_data_path, f'user_{user_id}_config.json')
            },
            'scalp': {
                'name': f'Scalp Bot User {user_id}',
                'process': None,
                'status': 'stopped',
                'started_at': None,
                'last_heartbeat': None,
                'config_file': os.path.join(self.user_data_path, f'user_{user_id}_config.json')
            }
        }
        
        # Создаем папку для данных пользователя
        os.makedirs('user_data', exist_ok=True)
        
        # Сохраняем конфигурацию пользователя
        self._save_user_config()
        
        logger.info(f"User Bot Manager инициализирован для пользователя {user_id}")
    
    def _create_user_config(self) -> Dict[str, Any]:
        """Создает конфигурацию для пользователя"""
        return {
            "user_id": self.user_id,
            "api_key": self.api_key,
            "secret_key": self.secret_key,
            "passphrase": self.passphrase,
            "symbols": ["BTC/USDT", "ETH/USDT", "BNB/USDT"],
            "capital_split": {
                "grid": 0.6,
                "scalp": 0.4
            },
            "grid": {
                "min_order_usd": 20,
                "max_position_size": 200,
                "exposure_limit": 0.5,
                "base_spacing": 0.008,
                "max_levels": 6,
                "sleep_interval": 15,
                "order_timeout_seconds": 600,
                "cci_block": -150,
                "grid_mode": "futures"
            },
            "scalp": {
                "min_order_usd": 15,
                "max_positions": 8,
                "position_size_percent": 0.05,
                "sleep_interval": 5,
                "signal_threshold": 50,
                "max_hold_seconds": 180,
                "tp_pct": 0.15,
                "sl_pct": 0.25,
                "fee_rate": 0.0004
            },
            "risk": {
                "max_drawdown_pct": 0.25,
                "stop_loss_pct": 0.03
            },
                    "balance_cache_sec": 60,
                    "min_alloc_usd": 200,
                    "adaptive_capital": {
                        "enabled": True,
                        "analysis_period_hours": 4,
                        "reanalysis_interval_hours": 2,
                        "min_hold_time_hours": 4,
                        "floating_profit": {
                            "min_profit_for_trailing": 50.0,
                            "trailing_stop_pct": 0.02,
                            "partial_close_pct": 0.5,
                            "profit_target_pct": 0.1,
                            "reinvestment_threshold": 200.0
                        }
                    },
                    "risk_mode": "automatic"
        }
    
    def _save_user_config(self):
        """Сохраняет конфигурацию пользователя в файл"""
        config_file = os.path.join(self.user_data_path, f'user_{self.user_id}_config.json')
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(self.user_config, f, indent=2, ensure_ascii=False)
    
    def start_bot(self, bot_type: str) -> Dict[str, Any]:
        """Запускает бота для пользователя"""
        if bot_type not in self.user_bots:
            return {"success": False, "error": f"Неизвестный тип бота: {bot_type}"}
        
        bot_info = self.user_bots[bot_type]
        
        # Проверяем, не запущен ли уже
        if bot_info['status'] == 'running':
            return {"success": False, "error": f"Бот {bot_info['name']} уже запущен"}
        
        try:
            logger.info(f"Запуск бота {bot_info['name']} для пользователя {self.user_id}")
            
            # Создаем скрипт для запуска бота пользователя
            bot_script = self._create_user_bot_script(bot_type)
            
            # Запускаем процесс
            process = subprocess.Popen([
                sys.executable, '-c', bot_script
            ], 
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=os.getcwd(),
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
            )
            
            # Ждем немного чтобы убедиться что процесс запустился
            time.sleep(3)
            
            # Проверяем что процесс все еще работает
            if process.poll() is None:
                bot_info['process'] = process
                bot_info['status'] = 'running'
                bot_info['started_at'] = datetime.now()
                bot_info['last_heartbeat'] = datetime.now()
                
                logger.info(f"Бот {bot_info['name']} запущен успешно (PID: {process.pid})")
                
                return {
                    "success": True, 
                    "message": f"Бот {bot_info['name']} запущен успешно",
                    "pid": process.pid,
                    "started_at": bot_info['started_at'].isoformat()
                }
            else:
                stdout, stderr = process.communicate()
                error_msg = stderr.decode() if stderr else "Неизвестная ошибка"
                
                logger.error(f"Ошибка запуска бота {bot_info['name']}: {error_msg}")
                
                return {
                    "success": False, 
                    "error": f"Ошибка запуска: {error_msg[:200]}"
                }
                
        except Exception as e:
            logger.error(f"Исключение при запуске бота {bot_type} для пользователя {self.user_id}: {e}")
            return {"success": False, "error": str(e)}
    
    def stop_bot(self, bot_type: str) -> Dict[str, Any]:
        """Останавливает бота пользователя"""
        if bot_type not in self.user_bots:
            return {"success": False, "error": f"Неизвестный тип бота: {bot_type}"}
        
        bot_info = self.user_bots[bot_type]
        
        try:
            logger.info(f"Остановка бота {bot_info['name']} для пользователя {self.user_id}")
            
            if bot_info['status'] == 'stopped':
                return {"success": False, "error": f"Бот {bot_info['name']} уже остановлен"}
            
            # Завершаем процесс
            if bot_info['process']:
                try:
                    bot_info['process'].terminate()
                    
                    # Ждем завершения
                    try:
                        bot_info['process'].wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        bot_info['process'].kill()
                    
                except Exception as e:
                    logger.error(f"Ошибка завершения процесса: {e}")
            
            # Обновляем статус
            bot_info['status'] = 'stopped'
            bot_info['process'] = None
            bot_info['started_at'] = None
            bot_info['last_heartbeat'] = None
            
            logger.info(f"Бот {bot_info['name']} остановлен")
            return {
                "success": True,
                "message": f"Бот {bot_info['name']} остановлен"
            }
                
        except Exception as e:
            logger.error(f"Ошибка остановки бота {bot_type} для пользователя {self.user_id}: {e}")
            return {"success": False, "error": str(e)}
    
    def restart_bot(self, bot_type: str) -> Dict[str, Any]:
        """Перезапускает бота пользователя"""
        logger.info(f"Перезапуск бота {bot_type} для пользователя {self.user_id}")
        
        # Сначала останавливаем
        stop_result = self.stop_bot(bot_type)
        if not stop_result["success"] and "уже остановлен" not in stop_result.get("error", ""):
            return stop_result
        
        # Ждем немного
        time.sleep(3)
        
        # Запускаем
        return self.start_bot(bot_type)
    
    def get_bots_status(self) -> Dict[str, Any]:
        """Возвращает статус ботов пользователя"""
        result = {}
        active_count = 0
        
        for bot_type, bot_info in self.user_bots.items():
            # Проверяем статус процесса
            if bot_info['process'] and bot_info['process'].poll() is None:
                bot_info['status'] = 'running'
                bot_info['last_heartbeat'] = datetime.now()
            else:
                bot_info['status'] = 'stopped'
                bot_info['process'] = None
            
            result[bot_type] = {
                'name': bot_info['name'],
                'status': bot_info['status'],
                'started_at': bot_info['started_at'].isoformat() if bot_info['started_at'] else None,
                'uptime': self._calculate_uptime(bot_info['started_at']) if bot_info['started_at'] else None
            }
            
            if bot_info['status'] == 'running':
                active_count += 1
        
        result['summary'] = {
            'total_bots': len(self.user_bots),
            'active_bots': active_count,
            'inactive_bots': len(self.user_bots) - active_count,
            'user_id': self.user_id
        }
        
        return result
    
    def start_all_bots(self) -> Dict[str, Any]:
        """Запускает всех ботов пользователя"""
        results = {}
        success_count = 0
        
        for bot_type in self.user_bots.keys():
            result = self.start_bot(bot_type)
            results[bot_type] = result
            if result["success"]:
                success_count += 1
        
        return {
            "success": success_count > 0,
            "message": f"Запущено ботов: {success_count} из {len(results)}",
            "details": results
        }
    
    def stop_all_bots(self) -> Dict[str, Any]:
        """Останавливает всех ботов пользователя"""
        results = {}
        success_count = 0
        
        for bot_type in self.user_bots.keys():
            result = self.stop_bot(bot_type)
            results[bot_type] = result
            if result["success"]:
                success_count += 1
        
        return {
            "success": success_count > 0,
            "message": f"Остановлено ботов: {success_count} из {len(results)}",
            "details": results
        }
    
    def _create_user_bot_script(self, bot_type: str) -> str:
        """Создает скрипт для запуска бота пользователя"""
        if bot_type == 'grid':
            return f"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from .enhanced_grid_bot import EnhancedMultiAssetGridBot
import asyncio
import json

# Загружаем конфигурацию пользователя
with open(os.path.join(self.user_data_path, f'user_{self.user_id}_config.json'), 'r') as f:
    config = json.load(f)

# Создаем и запускаем бота
bot = EnhancedMultiAssetGridBot(
    api_key=config['api_key'],
    secret_key=config['secret_key'],
    passphrase=config['passphrase'],
    config=config
)

asyncio.run(bot.run())
"""
        elif bot_type == 'scalp':
            return f"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from .enhanced_scalp_bot import EnhancedMultiAssetScalpBot
import asyncio
import json

# Загружаем конфигурацию пользователя
with open(os.path.join(self.user_data_path, f'user_{self.user_id}_config.json'), 'r') as f:
    config = json.load(f)

# Создаем и запускаем бота
bot = EnhancedMultiAssetScalpBot(
    api_key=config['api_key'],
    secret_key=config['secret_key'],
    passphrase=config['passphrase'],
    config=config
)

asyncio.run(bot.run())
"""
        else:
            raise ValueError(f"Неизвестный тип бота: {bot_type}")
    
    def _calculate_uptime(self, started_at: datetime) -> str:
        """Вычисляет время работы бота"""
        if not started_at:
            return "0s"
        
        uptime = datetime.now() - started_at
        
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"

# Глобальный словарь для хранения менеджеров пользователей
user_bot_managers: Dict[int, UserBotManager] = {}

def get_user_bot_manager(user_id: int, api_key: str = None, secret_key: str = None, passphrase: str = None) -> UserBotManager:
    """Получает или создает менеджер ботов для пользователя"""
    if user_id not in user_bot_managers:
        if not all([api_key, secret_key, passphrase]):
            raise ValueError("API ключи обязательны для создания менеджера ботов")
        
        user_bot_managers[user_id] = UserBotManager(user_id, api_key, secret_key, passphrase)
    
    return user_bot_managers[user_id]
