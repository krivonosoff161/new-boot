#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт запуска Telegram бота для уведомлений
Enhanced Trading System v3.0
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Добавляем путь к проекту
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Основная функция запуска бота"""
    try:
        # Импортируем контроллер уведомлений
        from src.trading.notification_controller import get_notification_controller
        
        logger.info("🔔 Запуск Notification Controller...")
        
        # Получаем контроллер
        controller = get_notification_controller()
        
        # Проверяем наличие токена
        if not controller.telegram_token:
            logger.error("❌ TELEGRAM_BOT_TOKEN не найден!")
            logger.info("Создайте файл .env с переменной TELEGRAM_BOT_TOKEN=your_bot_token")
            return
        
        # Запускаем бота
        logger.info("🚀 Запуск Telegram бота...")
        await controller.start_bot()
        
    except KeyboardInterrupt:
        logger.info("⏹️ Остановка бота по запросу пользователя...")
    except Exception as e:
        logger.error(f"❌ Ошибка запуска бота: {e}")
    finally:
        logger.info("🔔 Notification Controller остановлен")

if __name__ == "__main__":
    print("🔔 SOVERYN FIELD: Notification Controller v3.0")
    print("=" * 50)
    print("Запуск Telegram бота для уведомлений...")
    print("Нажмите Ctrl+C для остановки")
    print("=" * 50)
    
    asyncio.run(main())
