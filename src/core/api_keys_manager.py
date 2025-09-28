"""
Модуль для управления API ключами бирж
Обеспечивает безопасное хранение, шифрование и валидацию API ключей
"""

import json
import os
import time
import hashlib
import hmac
from datetime import datetime
from typing import Dict, List, Optional, Any
from cryptography.fernet import Fernet
import ccxt
from loguru import logger

class APIKeysManager:
    """Менеджер API ключей бирж"""
    
    def __init__(self, keys_dir: str = "data/api_keys", master_key_path: str = "config/.master_key"):
        """
        Инициализация менеджера API ключей
        
        Args:
            keys_dir: Директория для хранения ключей
            master_key_path: Путь к мастер-ключу для шифрования
        """
        self.keys_dir = keys_dir
        self.master_key_path = master_key_path
        self.supported_exchanges = [
            'binance', 'bybit', 'okx', 'huobi', 'kraken', 
            'coinbase', 'bitfinex', 'kucoin', 'gate', 'mexc'
        ]
        
        # Создаем директории
        os.makedirs(self.keys_dir, exist_ok=True)
        os.makedirs(os.path.dirname(master_key_path), exist_ok=True)
        
        # Загружаем или создаем мастер-ключ
        self.cipher = self._load_or_create_master_key()
        
        logger.info("API Keys Manager инициализирован")
    
    def _load_or_create_master_key(self) -> Fernet:
        """Загрузка или создание мастер-ключа для шифрования"""
        try:
            if os.path.exists(self.master_key_path):
                with open(self.master_key_path, 'rb') as f:
                    key = f.read()
                logger.info("Мастер-ключ загружен")
            else:
                key = Fernet.generate_key()
                with open(self.master_key_path, 'wb') as f:
                    f.write(key)
                logger.info("Создан новый мастер-ключ")
            
            return Fernet(key)
        except Exception as e:
            logger.error(f"Ошибка работы с мастер-ключом: {e}")
            raise
    
    def _encrypt_data(self, data: str) -> str:
        """Шифрование данных"""
        try:
            encrypted_data = self.cipher.encrypt(data.encode())
            return encrypted_data.decode()
        except Exception as e:
            logger.error(f"Ошибка шифрования: {e}")
            raise
    
    def _decrypt_data(self, encrypted_data: str) -> str:
        """Расшифровка данных"""
        try:
            decrypted_data = self.cipher.decrypt(encrypted_data.encode())
            return decrypted_data.decode()
        except Exception as e:
            logger.error(f"Ошибка расшифровки: {e}")
            raise
    
    def _get_user_keys_file(self, user_id: int) -> str:
        """Получение пути к файлу ключей пользователя"""
        return os.path.join(self.keys_dir, f"user_{user_id}_keys.json")
    
    def add_api_key(self, user_id: int, exchange: str, api_key: str, 
                   secret: str, passphrase: str = None, mode: str = "sandbox") -> bool:
        """
        Добавление API ключей пользователя
        
        Args:
            user_id: ID пользователя
            exchange: Название биржи
            api_key: API ключ
            secret: Секретный ключ
            passphrase: Пароль (для некоторых бирж)
            mode: Режим работы (sandbox/live)
            
        Returns:
            bool: True если ключи успешно добавлены
        """
        try:
            if exchange.lower() not in self.supported_exchanges:
                logger.error(f"Неподдерживаемая биржа: {exchange}")
                return False
            
            # Шифруем данные
            encrypted_api_key = self._encrypt_data(api_key)
            encrypted_secret = self._encrypt_data(secret)
            encrypted_passphrase = self._encrypt_data(passphrase) if passphrase else None
            
            # Загружаем существующие ключи пользователя
            user_keys_file = self._get_user_keys_file(user_id)
            user_keys = self._load_user_keys(user_id)
            
            # Добавляем новые ключи
            key_id = f"{exchange}_{mode}_{int(time.time())}"
            user_keys[key_id] = {
                "exchange": exchange.lower(),
                "mode": mode,
                "api_key": encrypted_api_key,
                "secret": encrypted_secret,
                "passphrase": encrypted_passphrase,
                "created_at": datetime.now().isoformat(),
                "last_used": None,
                "is_active": True,
                "validation_status": "pending"
            }
            
            # Сохраняем ключи
            self._save_user_keys(user_id, user_keys)
            
            logger.info(f"API ключи для {exchange} ({mode}) добавлены для пользователя {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка добавления API ключей: {e}")
            return False
    
    def _load_user_keys(self, user_id: int) -> Dict[str, Any]:
        """Загрузка ключей пользователя"""
        user_keys_file = self._get_user_keys_file(user_id)
        try:
            if os.path.exists(user_keys_file):
                with open(user_keys_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Ошибка загрузки ключей пользователя {user_id}: {e}")
            return {}
    
    def _save_user_keys(self, user_id: int, keys: Dict[str, Any]):
        """Сохранение ключей пользователя"""
        user_keys_file = self._get_user_keys_file(user_id)
        try:
            with open(user_keys_file, 'w', encoding='utf-8') as f:
                json.dump(keys, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Ошибка сохранения ключей пользователя {user_id}: {e}")
            raise
    
    def get_user_keys(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Получение списка ключей пользователя (без секретных данных)
        
        Args:
            user_id: ID пользователя
            
        Returns:
            List[Dict]: Список ключей пользователя
        """
        try:
            user_keys = self._load_user_keys(user_id)
            result = []
            
            for key_id, key_data in user_keys.items():
                if key_data.get("is_active", True):
                    result.append({
                        "key_id": key_id,
                        "exchange": key_data["exchange"],
                        "mode": key_data["mode"],
                        "created_at": key_data["created_at"],
                        "last_used": key_data.get("last_used"),
                        "validation_status": key_data.get("validation_status", "pending"),
                        "api_key_preview": key_data["api_key"][:8] + "..." + key_data["api_key"][-4:] if len(key_data["api_key"]) > 12 else "***"
                    })
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка получения ключей пользователя {user_id}: {e}")
            return []
    
    def get_decrypted_key(self, user_id: int, key_id: str) -> Optional[Dict[str, str]]:
        """
        Получение расшифрованных ключей для использования
        
        Args:
            user_id: ID пользователя
            key_id: ID ключа
            
        Returns:
            Dict: Расшифрованные ключи или None
        """
        try:
            user_keys = self._load_user_keys(user_id)
            if key_id not in user_keys:
                return None
            
            key_data = user_keys[key_id]
            if not key_data.get("is_active", True):
                return None
            
            # Расшифровываем данные
            decrypted_key = {
                "exchange": key_data["exchange"],
                "mode": key_data["mode"],
                "api_key": self._decrypt_data(key_data["api_key"]),
                "secret": self._decrypt_data(key_data["secret"])
            }
            
            if key_data.get("passphrase"):
                decrypted_key["passphrase"] = self._decrypt_data(key_data["passphrase"])
            
            # Обновляем время последнего использования
            user_keys[key_id]["last_used"] = datetime.now().isoformat()
            self._save_user_keys(user_id, user_keys)
            
            return decrypted_key
            
        except Exception as e:
            logger.error(f"Ошибка получения расшифрованных ключей: {e}")
            return None
    
    def validate_api_key(self, user_id: int, key_id: str) -> Dict[str, Any]:
        """
        Валидация API ключей
        
        Args:
            user_id: ID пользователя
            key_id: ID ключа
            
        Returns:
            Dict: Результат валидации
        """
        try:
            decrypted_key = self.get_decrypted_key(user_id, key_id)
            if not decrypted_key:
                return {"valid": False, "error": "Ключ не найден"}
            
            exchange_name = decrypted_key["exchange"]
            mode = decrypted_key["mode"]
            
            # Используем Exchange Mode Manager для создания экземпляра биржи
            from core.exchange_mode_manager import exchange_mode_manager
            
            try:
                exchange = exchange_mode_manager.create_exchange_instance(
                    exchange_name=exchange_name,
                    api_key=decrypted_key["api_key"],
                    secret=decrypted_key["secret"],
                    passphrase=decrypted_key.get("passphrase"),
                    mode=mode
                )
                
                # Тестируем подключение
                try:
                    # Для OKX сначала проверяем статус API
                    if exchange_name == 'okx':
                        try:
                            # Проверяем статус системы
                            status = exchange.fetch_status()
                            logger.info(f"OKX API статус: {status}")
                        except Exception as e:
                            logger.warning(f"OKX статус недоступен: {e}")
                    
                    # Проверяем баланс (безопасный метод)
                    balance = exchange.fetch_balance()
                    
                    # Обновляем статус валидации
                    user_keys = self._load_user_keys(user_id)
                    user_keys[key_id]["validation_status"] = "valid"
                    self._save_user_keys(user_id, user_keys)
                    
                    # Подсчитываем активные балансы
                    active_balances = len([k for k, v in balance.items() 
                                         if isinstance(v, dict) and v.get('total', 0) > 0])
                    
                    return {
                        "valid": True,
                        "message": f"✅ Ключи для {exchange_name.upper()} ({mode}) валидны",
                        "balance_count": active_balances,
                        "exchange": exchange_name.upper()
                    }
                    
                except Exception as e:
                    error_msg = str(e)
                    
                    # Улучшаем сообщения об ошибках
                    if "APIKey does not match current environment" in error_msg:
                        if exchange_name == 'okx':
                            friendly_error = "Ключи не соответствуют среде. Для OKX используйте live ключи даже для тестирования"
                        else:
                            friendly_error = "Ключи не соответствуют выбранной среде (sandbox/live)"
                    elif "Invalid API-key" in error_msg or "API key" in error_msg:
                        friendly_error = "Неверный API ключ или секретный ключ"
                    elif "signature" in error_msg.lower():
                        friendly_error = "Ошибка подписи запроса. Проверьте секретный ключ"
                    elif "passphrase" in error_msg.lower() or "password" in error_msg.lower():
                        if exchange_name == 'okx':
                            friendly_error = "Неверный пароль (Password). Проверьте пароль, который вы создали при генерации API ключей"
                        else:
                            friendly_error = "Неверный пароль (passphrase)"
                    elif "rate limit" in error_msg.lower():
                        friendly_error = "Превышен лимит запросов. Попробуйте позже"
                    elif "network" in error_msg.lower() or "connection" in error_msg.lower():
                        friendly_error = "Ошибка сети. Проверьте интернет-соединение"
                    elif "credential" in error_msg.lower():
                        if exchange_name == 'okx':
                            friendly_error = "Отсутствует обязательный параметр. Для OKX обязательно нужен пароль (Password)"
                        else:
                            friendly_error = "Отсутствует обязательный параметр аутентификации"
                    else:
                        friendly_error = f"Ошибка подключения: {error_msg}"
                    
                    # Обновляем статус валидации
                    user_keys = self._load_user_keys(user_id)
                    user_keys[key_id]["validation_status"] = "invalid"
                    self._save_user_keys(user_id, user_keys)
                    
                    logger.error(f"Ошибка валидации {exchange_name}: {error_msg}")
                    
                    return {
                        "valid": False,
                        "error": friendly_error,
                        "technical_error": error_msg
                    }
                    
            except Exception as e:
                logger.error(f"Ошибка создания экземпляра биржи {exchange_name}: {e}")
                return {"valid": False, "error": f"Неподдерживаемая биржа: {exchange_name}"}
                
        except Exception as e:
            logger.error(f"Ошибка валидации API ключей: {e}")
            return {"valid": False, "error": str(e)}
    
    def delete_api_key(self, user_id: int, key_id: str) -> bool:
        """
        Удаление API ключей
        
        Args:
            user_id: ID пользователя
            key_id: ID ключа
            
        Returns:
            bool: True если ключи успешно удалены
        """
        try:
            user_keys = self._load_user_keys(user_id)
            if key_id in user_keys:
                del user_keys[key_id]
                self._save_user_keys(user_id, user_keys)
                logger.info(f"API ключ {key_id} удален для пользователя {user_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Ошибка удаления API ключей: {e}")
            return False
    
    def get_supported_exchanges(self) -> List[str]:
        """Получение списка поддерживаемых бирж"""
        return self.supported_exchanges.copy()

# Создаем глобальный экземпляр менеджера
api_keys_manager = APIKeysManager()
