#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Scalp Bot Runner - скрипт для запуска Scalp бота как отдельного процесса
"""
import os
import sys
import json
import asyncio
import argparse
from datetime import datetime

# Добавляем пути для импорта
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from src.core.log_helper import build_logger
from src.trading.enhanced_scalp_bot import EnhancedScalpBot

async def run_scalp_bot(bot_id: str, user_id: int, config: dict):
    """Запуск Scalp бота"""
    # Создаем директорию для логов ботов
    os.makedirs('logs/bots', exist_ok=True)
    
    # Настраиваем логгер с записью в файл
    logger = build_logger(
        name=f"scalp_bot_{bot_id}",
        level="INFO",
        log_file=f"logs/bots/bot_{bot_id}.log"
    )
    
    try:
        logger.info(f"🚀 Запуск Scalp бота {bot_id} для пользователя {user_id}")
        
        # Создаем экземпляр бота
        bot_config = config.get('config', {})
        if 'trading_pairs' in bot_config:
            config['trading_pairs'] = bot_config['trading_pairs']
            logger.info(f"📊 Передаем торговые пары в бот: {config['trading_pairs']}")
        
        bot = EnhancedScalpBot(user_id, config)
        
        # Настраиваем биржу
        bot_config = config.get('config', {})
        logger.info(f"📋 Конфигурация бота: {bot_config}")
        
        if 'api_key_id' in bot_config:
            logger.info(f"🔑 API ключ ID: {bot_config['api_key_id']}")
            # Получаем API ключи
            api_keys = config.get('api_keys', [])
            if api_keys:
                key_data = api_keys[0]  # Берем первый ключ
                logger.info(f"🔑 Используем API ключ: {key_data.get('api_key', 'N/A')[:10]}...")
                
                # Настраиваем биржу
                exchange_name = key_data.get('exchange', 'OKX')
                mode = key_data.get('mode', 'sandbox')
                
                success = await bot.setup_exchange(
                    exchange_name,
                    key_data.get('api_key'),
                    key_data.get('secret_key'),
                    key_data.get('passphrase', ''),
                    mode
                )
                
                if success:
                    logger.info(f"✅ Биржа {exchange_name} настроена успешно")
                    
                    # Запускаем торговлю
                    logger.info("🎯 Начинаем торговлю...")
                    await bot.start_trading()
                else:
                    logger.error(f"❌ Ошибка настройки биржи {exchange_name}")
            else:
                logger.error("❌ API ключи не найдены в конфигурации")
        else:
            logger.error("❌ API ключ ID не найден в конфигурации")
            
    except Exception as e:
        logger.error(f"❌ Критическая ошибка в Scalp боте: {e}")
        import traceback
        logger.error(f"❌ Трассировка: {traceback.format_exc()}")

def main():
    """Главная функция"""
    parser = argparse.ArgumentParser(description='Enhanced Scalp Bot Runner')
    parser.add_argument('--bot-id', required=True, help='ID бота')
    parser.add_argument('--user-id', required=True, type=int, help='ID пользователя')
    parser.add_argument('--config-file', required=True, help='Путь к файлу конфигурации')
    
    args = parser.parse_args()
    
    try:
        # Загружаем конфигурацию
        with open(args.config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        print(f"🚀 Запуск Enhanced Scalp Bot Runner")
        print(f"📊 Bot ID: {args.bot_id}")
        print(f"👤 User ID: {args.user_id}")
        print(f"📁 Config: {args.config_file}")
        
        # Запускаем бота
        asyncio.run(run_scalp_bot(args.bot_id, args.user_id, config))
        
    except Exception as e:
        print(f"❌ Ошибка запуска Scalp бота: {e}")
        import traceback
        print(f"❌ Трассировка: {traceback.format_exc()}")
        sys.exit(1)

if __name__ == "__main__":
    main()













