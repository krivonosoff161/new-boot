#!/usr/bin/env python3
"""
Облегченная версия сервера для слабых ПК
"""

import os
import sys
from waitress import serve
from src.web.app import create_app

def main():
    """Запуск облегченного сервера"""
    
    # Создаем приложение
    app = create_app()
    
    # Настройки для слабых ПК
    host = '0.0.0.0'
    port = int(os.environ.get('PORT', 5000))
    
    print("🚀 Запуск облегченного сервера...")
    print(f"📡 Адрес: http://{host}:{port}")
    print(f"💾 Оптимизировано для слабых ПК")
    print("=" * 50)
    
    # Минимальные настройки Waitress
    serve(
        app,
        host=host,
        port=port,
        threads=2,  # Только 2 потока вместо 8
        connection_limit=20,  # Лимит соединений 20 вместо 100
        cleanup_interval=60,  # Очистка каждые 60 сек
        channel_timeout=60,  # Таймаут 1 мин
        log_socket_errors=False,  # Отключаем логирование ошибок
        max_request_header_size=65536,  # 64KB вместо 256KB
        max_request_body_size=10485760,  # 10MB вместо 1GB
    )

if __name__ == '__main__':
    main()






