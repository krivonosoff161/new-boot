"""
Конфигурация для продакшн-сервера
"""

import os

class ProductionConfig:
    """Конфигурация продакшн-сервера"""
    
    # Основные настройки
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-change-this')
    DEBUG = False
    TESTING = False
    
    # База данных
    DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///data/trading_system.db')
    
    # Безопасность
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Лимиты
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    PERMANENT_SESSION_LIFETIME = 3600  # 1 час
    
    # Логирование
    LOG_LEVEL = 'INFO'
    LOG_FILE = 'logs/production.log'
    
    # API лимиты
    RATE_LIMIT_PER_MINUTE = 60
    MAX_REQUESTS_PER_USER = 1000
    
    # Торговые настройки
    MAX_BOTS_PER_USER = 5
    MAX_TRADING_PAIRS = 20
    
    # Безопасность API
    API_RATE_LIMIT = '1000 per hour'
    API_KEY_LENGTH = 32
    
    # Мониторинг
    ENABLE_METRICS = True
    METRICS_PORT = 9090
    
    # Уведомления
    ENABLE_EMAIL_NOTIFICATIONS = False
    ENABLE_SMS_NOTIFICATIONS = False
    
    # Резервное копирование
    BACKUP_ENABLED = True
    BACKUP_INTERVAL = 3600  # 1 час
    BACKUP_RETENTION_DAYS = 30















