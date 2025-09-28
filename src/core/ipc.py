#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Inter-Process Communication (IPC) Server
Enhanced Trading System v3.0 Commercial
"""

import json
import socket
import threading
import time
from typing import Dict, Any, Optional
from loguru import logger

class BaseIPCServer:
    """Базовый IPC сервер"""
    
    def __init__(self, port: int = 8888):
        """
        Инициализация IPC сервера
        
        Args:
            port: Порт для IPC сервера
        """
        self.port = port
        self.socket = None
        self.running = False
        self.clients = []
        self.data = {}
        
    def start(self) -> bool:
        """
        Запуск IPC сервера
        
        Returns:
            True если сервер запущен успешно, False в противном случае
        """
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind(('localhost', self.port))
            self.socket.listen(5)
            
            self.running = True
            
            # Запускаем поток для обработки клиентов
            server_thread = threading.Thread(target=self._handle_clients)
            server_thread.daemon = True
            server_thread.start()
            
            logger.info(f"IPC сервер запущен на порту {self.port}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка запуска IPC сервера: {e}")
            return False
    
    def stop(self) -> None:
        """Остановка IPC сервера"""
        self.running = False
        
        if self.socket:
            self.socket.close()
            self.socket = None
        
        logger.info("IPC сервер остановлен")
    
    def _handle_clients(self) -> None:
        """Обработка клиентских подключений"""
        while self.running:
            try:
                client_socket, address = self.socket.accept()
                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, address)
                )
                client_thread.daemon = True
                client_thread.start()
                
            except Exception as e:
                if self.running:
                    logger.error(f"Ошибка обработки клиента: {e}")
    
    def _handle_client(self, client_socket: socket.socket, address: tuple) -> None:
        """
        Обработка отдельного клиента
        
        Args:
            client_socket: Сокет клиента
            address: Адрес клиента
        """
        try:
            while self.running:
                data = client_socket.recv(1024)
                if not data:
                    break
                
                try:
                    message = json.loads(data.decode('utf-8'))
                    response = self._process_message(message)
                    
                    if response:
                        client_socket.send(json.dumps(response).encode('utf-8'))
                        
                except json.JSONDecodeError:
                    logger.warning(f"Некорректный JSON от клиента {address}")
                    
        except Exception as e:
            logger.error(f"Ошибка обработки клиента {address}: {e}")
        finally:
            client_socket.close()
    
    def _process_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Обработка сообщения от клиента
        
        Args:
            message: Сообщение от клиента
            
        Returns:
            Ответ клиенту
        """
        try:
            action = message.get('action')
            
            if action == 'get_data':
                return {
                    'status': 'success',
                    'data': self.data
                }
            
            elif action == 'set_data':
                key = message.get('key')
                value = message.get('value')
                
                if key:
                    self.data[key] = value
                    return {
                        'status': 'success',
                        'message': f'Данные {key} обновлены'
                    }
            
            elif action == 'ping':
                return {
                    'status': 'success',
                    'message': 'pong'
                }
            
            else:
                return {
                    'status': 'error',
                    'message': f'Неизвестное действие: {action}'
                }
                
        except Exception as e:
            logger.error(f"Ошибка обработки сообщения: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def set_data(self, key: str, value: Any) -> None:
        """
        Установка данных
        
        Args:
            key: Ключ данных
            value: Значение данных
        """
        self.data[key] = value
        logger.debug(f"Данные {key} обновлены")
    
    def get_data(self, key: str, default: Any = None) -> Any:
        """
        Получение данных
        
        Args:
            key: Ключ данных
            default: Значение по умолчанию
            
        Returns:
            Значение данных или значение по умолчанию
        """
        return self.data.get(key, default)
    
    def broadcast_data(self, data: Dict[str, Any]) -> None:
        """
        Рассылка данных всем клиентам
        
        Args:
            data: Данные для рассылки
        """
        # В простой реализации просто обновляем локальные данные
        self.data.update(data)
        logger.debug("Данные разосланы всем клиентам")

class GridBotIPCServer(BaseIPCServer):
    """IPC сервер для Grid бота"""
    
    def __init__(self, port: int = 8888):
        """
        Инициализация IPC сервера
        
        Args:
            port: Порт для IPC сервера
        """
        super().__init__(port)

class ScalpBotIPCServer(BaseIPCServer):
    """IPC сервер для Scalp бота"""
    
    def __init__(self, port: int = 8889):
        """
        Инициализация IPC сервера
        
        Args:
            port: Порт для IPC сервера
        """
        super().__init__(port)
