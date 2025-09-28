#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot Manager - управление торговыми ботами через веб-интерфейс
Enhanced Trading System v3.0
"""

import os
import sys
import subprocess
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional
import json

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BotManager:
    """Менеджер для управления торговыми ботами"""
    
    def __init__(self):
        """Инициализация менеджера ботов"""
        # Получаем абсолютный путь к скриптам
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        
        self.bots = {
            'grid': {
                'name': 'Enhanced Grid Bot v3.0',
                'script': os.path.join(current_dir, 'enhanced_grid_bot.py'),
                'process': None,
                'status': 'stopped',
                'started_at': None,
                'last_heartbeat': None
            },
            'scalp': {
                'name': 'Enhanced Scalp Bot v3.0',
                'script': os.path.join(current_dir, 'enhanced_scalp_bot.py'),
                'process': None,
                'status': 'stopped',
                'started_at': None,
                'last_heartbeat': None
            },
            'controller': {
                'name': 'Enhanced Controller',
                'script': os.path.join(current_dir, 'enhanced_controller.py'),
                'process': None,
                'status': 'stopped',
                'started_at': None,
                'last_heartbeat': None
            }
        }
        
        # Проверяем статус при инициализации
        self.update_bots_status()
    
    def update_bots_status(self):
        """Обновляет статус всех ботов (упрощенная версия)"""
        try:
            # Простая проверка через subprocess
            for bot_type, bot_info in self.bots.items():
                if bot_info['process']:
                    # Проверяем, работает ли процесс
                    if bot_info['process'].poll() is None:
                        # Процесс еще работает
                        bot_info['status'] = 'running'
                        bot_info['last_heartbeat'] = datetime.now()
                    else:
                        # Процесс завершился
                        bot_info['status'] = 'stopped'
                        bot_info['process'] = None
                        bot_info['started_at'] = None
            
            logger.info("Статус ботов обновлен")
            
        except Exception as e:
            logger.error(f"Ошибка обновления статуса ботов: {e}")
    
    def start_bot(self, bot_type: str) -> Dict:
        """Запускает указанного бота"""
        if bot_type not in self.bots:
            return {"success": False, "error": f"Неизвестный тип бота: {bot_type}"}
        
        bot_info = self.bots[bot_type]
        
        # Проверяем, не запущен ли уже
        self.update_bots_status()
        if bot_info['status'] == 'running':
            return {"success": False, "error": f"Бот {bot_info['name']} уже запущен"}
        
        try:
            logger.info(f"Запуск бота: {bot_info['name']}")
            
            # Запускаем бота в отдельном процессе
            script_path = bot_info['script']
            if not os.path.exists(script_path):
                return {"success": False, "error": f"Скрипт не найден: {script_path}"}
            
            # Запускаем процесс
            process = subprocess.Popen([
                sys.executable, script_path
            ], 
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=os.getcwd(),
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
            )
            
            # Ждем немного чтобы убедиться что процесс запустился
            time.sleep(2)
            
            # Проверяем что процесс все еще работает
            if process.poll() is None:
                # Процесс запущен успешно
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
                # Процесс завершился с ошибкой
                stdout, stderr = process.communicate()
                error_msg = stderr.decode() if stderr else "Неизвестная ошибка"
                
                logger.error(f"Ошибка запуска бота {bot_info['name']}: {error_msg}")
                
                return {
                    "success": False, 
                    "error": f"Ошибка запуска: {error_msg[:200]}"
                }
                
        except Exception as e:
            logger.error(f"Исключение при запуске бота {bot_type}: {e}")
            return {"success": False, "error": str(e)}
    
    def stop_bot(self, bot_type: str) -> Dict:
        """Останавливает указанного бота"""
        if bot_type not in self.bots:
            return {"success": False, "error": f"Неизвестный тип бота: {bot_type}"}
        
        bot_info = self.bots[bot_type]
        
        try:
            logger.info(f"Остановка бота: {bot_info['name']}")
            
            # Обновляем статус
            self.update_bots_status()
            
            if bot_info['status'] == 'stopped':
                return {"success": False, "error": f"Бот {bot_info['name']} уже остановлен"}
            
            # Находим и завершаем процесс через subprocess
            script_name = os.path.basename(bot_info['script'])
            terminated_count = 0
            
            # Если у нас есть процесс, завершаем его
            if bot_info['process']:
                try:
                    logger.info(f"Завершаем процесс {bot_info['process'].pid}: {script_name}")
                    
                    # Сначала пробуем мягко завершить
                    bot_info['process'].terminate()
                    
                    # Ждем немного
                    try:
                        bot_info['process'].wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        # Если не завершился мягко, принудительно
                        bot_info['process'].kill()
                    
                    terminated_count += 1
                    
                except Exception as e:
                    logger.error(f"Ошибка завершения процесса: {e}")
            
            # Дополнительно ищем через taskkill (Windows)
            if os.name == 'nt':
                try:
                    result = subprocess.run([
                        'taskkill', '/F', '/IM', 'python.exe', '/FI', f'COMMANDLINE eq *{script_name}*'
                    ], capture_output=True, text=True, timeout=10)
                    
                    if result.returncode == 0:
                        terminated_count += 1
                        logger.info(f"Процесс завершен через taskkill: {script_name}")
                        
                except Exception as e:
                    logger.error(f"Ошибка taskkill: {e}")
            
            # Обновляем статус бота
            bot_info['status'] = 'stopped'
            bot_info['process'] = None
            bot_info['started_at'] = None
            bot_info['last_heartbeat'] = None
            
            if terminated_count > 0:
                logger.info(f"Бот {bot_info['name']} остановлен (завершено процессов: {terminated_count})")
                return {
                    "success": True,
                    "message": f"Бот {bot_info['name']} остановлен (завершено процессов: {terminated_count})"
                }
            else:
                return {
                    "success": True,
                    "message": f"Бот {bot_info['name']} был уже остановлен"
                }
                
        except Exception as e:
            logger.error(f"Ошибка остановки бота {bot_type}: {e}")
            return {"success": False, "error": str(e)}
    
    def restart_bot(self, bot_type: str) -> Dict:
        """Перезапускает указанного бота"""
        logger.info(f"Перезапуск бота: {bot_type}")
        
        # Сначала останавливаем
        stop_result = self.stop_bot(bot_type)
        if not stop_result["success"] and "уже остановлен" not in stop_result.get("error", ""):
            return stop_result
        
        # Ждем немного
        time.sleep(3)
        
        # Запускаем
        return self.start_bot(bot_type)
    
    def get_bots_status(self) -> Dict:
        """Возвращает статус всех ботов"""
        self.update_bots_status()
        
        result = {}
        active_count = 0
        
        for bot_type, bot_info in self.bots.items():
            if bot_type == 'controller':  # Пропускаем контроллер в общей статистике
                continue
                
            result[bot_type] = {
                'name': bot_info['name'],
                'status': bot_info['status'],
                'started_at': bot_info['started_at'].isoformat() if bot_info['started_at'] else None,
                'uptime': self._calculate_uptime(bot_info['started_at']) if bot_info['started_at'] else None
            }
            
            if bot_info['status'] == 'running':
                active_count += 1
        
        result['summary'] = {
            'total_bots': len([b for b in self.bots.keys() if b != 'controller']),
            'active_bots': active_count,
            'inactive_bots': len([b for b in self.bots.keys() if b != 'controller']) - active_count
        }
        
        return result
    
    def start_all_bots(self) -> Dict:
        """Запускает всех ботов"""
        results = {}
        success_count = 0
        
        for bot_type in ['grid', 'scalp']:  # Пропускаем контроллер
            result = self.start_bot(bot_type)
            results[bot_type] = result
            if result["success"]:
                success_count += 1
        
        return {
            "success": success_count > 0,
            "message": f"Запущено ботов: {success_count} из {len(results)}",
            "details": results
        }
    
    def stop_all_bots(self) -> Dict:
        """Останавливает всех ботов"""
        results = {}
        success_count = 0
        
        for bot_type in ['grid', 'scalp', 'controller']:
            result = self.stop_bot(bot_type)
            results[bot_type] = result
            if result["success"]:
                success_count += 1
        
        return {
            "success": success_count > 0,
            "message": f"Остановлено ботов: {success_count} из {len(results)}",
            "details": results
        }
    
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

# Создаем глобальный экземпляр
bot_manager = BotManager()











