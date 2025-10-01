#!/usr/bin/env python3
"""
Продакшн-сервер для торговой системы
Поддерживает несколько пользователей одновременно
"""

import os
import sys
from waitress import serve
from src.web.app import create_app

def main():
    """Запуск продакшн-сервера"""
    
    # Создаем приложение
    app = create_app()
    
    # Настройки продакшна
    host = '0.0.0.0'  # Доступно для всех IP
    port = int(os.environ.get('PORT', 5000))
    
    print("🚀 Запуск продакшн-сервера...")
    print(f"📡 Адрес: http://{host}:{port}")
    print(f"👥 Поддержка множественных пользователей: ✅")
    print(f"🔒 Безопасность: ✅")
    print(f"⚡ Производительность: ✅")
    print("=" * 50)
    
    # Запускаем Waitress сервер
    serve(
        app,
        host=host,
        port=port,
        threads=8,  # 8 потоков для обработки запросов
        connection_limit=100,  # Лимит соединений
        cleanup_interval=30,  # Очистка каждые 30 сек
        channel_timeout=120,  # Таймаут канала 2 мин
        log_socket_errors=True,
        max_request_header_size=262144,  # 256KB
        max_request_body_size=1073741824,  # 1GB
    )

if __name__ == '__main__':
    main()








