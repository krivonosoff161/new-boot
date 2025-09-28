"""
Bot Process Manager - управление процессами торговых ботов
"""
import os
import sys
import json
import time
import asyncio
import subprocess
import threading
import signal
from typing import Dict, List, Optional, Any
from datetime import datetime
from src.core.log_helper import build_logger

class BotProcessManager:
    """Менеджер процессов торговых ботов"""
    
    def __init__(self):
        self.logger = build_logger("bot_process_manager")
        self.running_bots = {}  # {bot_id: process_info}
        self.bot_scripts = {
            'grid': 'src/trading/real_grid_bot_runner.py',
            'scalp': 'src/trading/scalp_bot_runner.py'
        }
    
    def start_bot(self, bot_id: str, bot_type: str, user_id: int, config: Dict[str, Any]) -> bool:
        """Запуск бота как отдельного процесса"""
        try:
            if bot_id in self.running_bots:
                self.logger.warning(f"Бот {bot_id} уже запущен")
                return False
            
            # Подготавливаем конфигурацию для бота
            bot_config = {
                'bot_id': bot_id,
                'user_id': user_id,
                'bot_type': bot_type,
                'config': config,
                'started_at': datetime.now().isoformat()
            }
            
            # Создаем файл конфигурации для бота
            config_file = f'data/bot_configs/{bot_id}_config.json'
            os.makedirs(os.path.dirname(config_file), exist_ok=True)
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(bot_config, f, ensure_ascii=False, indent=2)
            
            # Запускаем бот как отдельный процесс
            if bot_type in self.bot_scripts:
                script_path = self.bot_scripts[bot_type]
                
                # Команда для запуска бота
                cmd = [
                    sys.executable, 
                    script_path,
                    '--config', config_file,
                    '--bot-id', bot_id,
                    '--user-id', str(user_id)
                ]
                
                # Запускаем процесс
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=os.getcwd(),
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
                )
                
                # Сохраняем информацию о процессе
                self.running_bots[bot_id] = {
                    'process': process,
                    'bot_type': bot_type,
                    'user_id': user_id,
                    'started_at': datetime.now().isoformat(),
                    'pid': process.pid,
                    'config_file': config_file
                }
                
                self.logger.info(f"✅ Бот {bot_id} ({bot_type}) запущен с PID {process.pid}")
                
                # Обновляем статус в файле
                self.logger.info(f"🔄 Обновляем статус бота {bot_id} на 'running'")
                self._update_bot_status(bot_id, 'running', process.pid)
                self.logger.info(f"✅ Статус бота {bot_id} обновлен в файле")
                
                return True
            else:
                self.logger.error(f"❌ Неизвестный тип бота: {bot_type}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка запуска бота {bot_id}: {e}")
            return False
    
    def stop_bot(self, bot_id: str) -> bool:
        """Остановка бота"""
        try:
            if bot_id not in self.running_bots:
                self.logger.warning(f"Бот {bot_id} не запущен")
                return False
            
            bot_info = self.running_bots[bot_id]
            process = bot_info['process']
            pid = bot_info['pid']
            
            self.logger.info(f"🛑 Останавливаем бот {bot_id} (PID: {pid})")
            
            # Останавливаем процесс
            if process.poll() is None:  # Процесс еще работает
                try:
                    if os.name == 'nt':  # Windows
                        # В Windows используем taskkill для принудительного завершения
                        import subprocess as sp
                        try:
                            # Сначала пробуем мягко завершить
                            process.terminate()
                            process.wait(timeout=5)
                            self.logger.info(f"✅ Бот {bot_id} мягко завершен")
                        except subprocess.TimeoutExpired:
                            # Принудительно завершаем через taskkill
                            sp.run(['taskkill', '/F', '/T', '/PID', str(pid)], 
                                  capture_output=True, check=False)
                            self.logger.info(f"✅ Бот {bot_id} принудительно завершен через taskkill")
                    else:  # Unix/Linux
                        process.terminate()
                        try:
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            os.kill(pid, signal.SIGKILL)
                            process.wait()
                        self.logger.info(f"✅ Бот {bot_id} завершен")
                except Exception as stop_error:
                    self.logger.error(f"❌ Ошибка при остановке процесса: {stop_error}")
                    # Пробуем принудительно завершить
                    try:
                        if os.name == 'nt':
                            import subprocess as sp
                            sp.run(['taskkill', '/F', '/T', '/PID', str(pid)], 
                                  capture_output=True, check=False)
                        else:
                            os.kill(pid, signal.SIGKILL)
                        self.logger.info(f"✅ Бот {bot_id} принудительно завершен")
                    except Exception as force_error:
                        self.logger.error(f"❌ Не удалось принудительно завершить: {force_error}")
                        return False
            
            # Удаляем из списка запущенных
            del self.running_bots[bot_id]
            
            # Удаляем файл конфигурации
            try:
                if os.path.exists(bot_info['config_file']):
                    os.remove(bot_info['config_file'])
            except:
                pass
            
            self.logger.info(f"✅ Бот {bot_id} остановлен")
            
            # Обновляем статус в файле
            self._update_bot_status(bot_id, 'stopped')
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка остановки бота {bot_id}: {e}")
            return False
    
    def get_bot_status(self, bot_id: str) -> Optional[Dict[str, Any]]:
        """Получение статуса бота"""
        if bot_id in self.running_bots:
            bot_info = self.running_bots[bot_id]
            process = bot_info['process']
            
            # Проверяем, работает ли процесс
            if process.poll() is None:
                return {
                    'status': 'running',
                    'pid': bot_info['pid'],
                    'started_at': bot_info['started_at'],
                    'bot_type': bot_info['bot_type'],
                    'user_id': bot_info['user_id']
                }
            else:
                # Процесс завершился
                del self.running_bots[bot_id]
                self._update_bot_status(bot_id, 'stopped')
                return {
                    'status': 'stopped',
                    'pid': None,
                    'started_at': bot_info['started_at'],
                    'bot_type': bot_info['bot_type'],
                    'user_id': bot_info['user_id']
                }
        else:
            return None
    
    def get_all_bots_status(self) -> Dict[str, Dict[str, Any]]:
        """Получение статуса всех ботов"""
        status = {}
        
        # Проверяем запущенные боты
        for bot_id in list(self.running_bots.keys()):
            bot_status = self.get_bot_status(bot_id)
            if bot_status:
                status[bot_id] = bot_status
        
        return status
    
    def _update_bot_status(self, bot_id: str, status: str, pid: Optional[int] = None):
        """Обновление статуса бота в файле"""
        try:
            self.logger.info(f"📝 Начинаем обновление статуса бота {bot_id} на '{status}'")
            
            # Читаем существующий статус
            try:
                with open('data/bot_status.json', 'r', encoding='utf-8') as f:
                    bots_status = json.load(f)
                self.logger.info(f"📖 Прочитан существующий статус для {len(bots_status)} ботов")
            except Exception as e:
                self.logger.warning(f"⚠️ Не удалось прочитать файл статуса: {e}")
                bots_status = {}
            
            # Обновляем статус
            if bot_id in bots_status:
                old_status = bots_status[bot_id].get('status', 'unknown')
                bots_status[bot_id]['status'] = status
                bots_status[bot_id]['last_update'] = datetime.now().isoformat()
                if pid:
                    bots_status[bot_id]['pid'] = pid
                self.logger.info(f"🔄 Обновлен статус бота {bot_id}: {old_status} -> {status}")
            else:
                bots_status[bot_id] = {
                    'id': bot_id,
                    'status': status,
                    'last_update': datetime.now().isoformat(),
                    'pid': pid
                }
                self.logger.info(f"➕ Создана новая запись для бота {bot_id} со статусом '{status}'")
            
            # Сохраняем
            with open('data/bot_status.json', 'w', encoding='utf-8') as f:
                json.dump(bots_status, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"💾 Статус бота {bot_id} сохранен в файл")
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка обновления статуса бота {bot_id}: {e}")
    
    def cleanup_stopped_bots(self):
        """Очистка остановленных ботов"""
        stopped_bots = []
        
        for bot_id, bot_info in self.running_bots.items():
            process = bot_info['process']
            if process.poll() is not None:  # Процесс завершился
                stopped_bots.append(bot_id)
        
        for bot_id in stopped_bots:
            del self.running_bots[bot_id]
            self._update_bot_status(bot_id, 'stopped')
            self.logger.info(f"🧹 Очищен остановленный бот {bot_id}")
    
    def force_stop_all_bots(self):
        """Принудительная остановка всех ботов"""
        self.logger.info("🛑 Принудительная остановка всех ботов")
        
        # Останавливаем все запущенные боты
        for bot_id in list(self.running_bots.keys()):
            self.stop_bot(bot_id)
        
        # Дополнительно убиваем все процессы Python, связанные с ботами
        stopped_pids = []
        try:
            import psutil
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.info['name'] == 'python.exe' or proc.info['name'] == 'python':
                        cmdline = proc.info['cmdline']
                        if cmdline and any('real_grid_bot_runner.py' in str(cmd) for cmd in cmdline):
                            self.logger.info(f"🛑 Принудительно завершаем процесс {proc.info['pid']}")
                            stopped_pids.append(proc.info['pid'])
                            proc.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except Exception as e:
            self.logger.error(f"❌ Ошибка принудительной остановки: {e}")
        
        # Обновляем статус всех ботов в файле на 'stopped'
        try:
            with open('data/bot_status.json', 'r', encoding='utf-8') as f:
                bots_status = json.load(f)
            
            for bot_id, bot_info in bots_status.items():
                if bot_info.get('status') == 'running':
                    bot_info['status'] = 'stopped'
                    bot_info['last_update'] = datetime.now().isoformat()
                    self.logger.info(f"🔄 Обновлен статус бота {bot_id} на 'stopped'")
            
            with open('data/bot_status.json', 'w', encoding='utf-8') as f:
                json.dump(bots_status, f, ensure_ascii=False, indent=2)
            
            self.logger.info("💾 Статус всех ботов обновлен в файле")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка обновления статуса в файле: {e}")
        
        self.logger.info("✅ Все боты принудительно остановлены")

# Глобальный экземпляр менеджера
bot_process_manager = BotProcessManager()