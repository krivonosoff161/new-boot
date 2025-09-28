#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Real Grid Bot Runner - скрипт для запуска Grid бота как отдельного процесса
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
from src.trading.real_grid_bot import RealGridBot

async def run_grid_bot(bot_id: str, user_id: int, config: dict):
    """Запуск Grid бота"""
    # Создаем директорию для логов ботов
    os.makedirs('logs/bots', exist_ok=True)
    
    # Настраиваем логгер с записью в файл
    logger = build_logger(
        name=f"grid_bot_{bot_id}",
        level="INFO",
        log_file=f"logs/bots/bot_{bot_id}.log"
    )
    
    try:
        logger.info(f"🚀 Запуск Grid бота {bot_id} для пользователя {user_id}")
        
        # Создаем экземпляр бота
        # Передаем торговые пары из конфигурации
        bot_config = config.get('config', {})
        if 'trading_pairs' in bot_config:
            config['trading_pairs'] = bot_config['trading_pairs']
            logger.info(f"📊 Передаем торговые пары в бот: {config['trading_pairs']}")
        
        bot = RealGridBot(user_id, config)
        
        # Настраиваем биржу
        bot_config = config.get('config', {})
        logger.info(f"📋 Конфигурация бота: {bot_config}")
        
        if 'api_key_id' in bot_config:
            logger.info(f"🔑 API ключ ID: {bot_config['api_key_id']}")
            # Получаем API ключи
            from src.core.api_keys_manager import APIKeysManager
            api_keys_manager = APIKeysManager()
            decrypted_keys = api_keys_manager.get_decrypted_key(user_id, bot_config['api_key_id'])
            
            if decrypted_keys:
                logger.info(f"✅ API ключи получены для бота {bot_id}")
                success = bot.setup_exchange(
                    exchange_name=bot_config.get('exchange', 'okx'),
                    api_key=decrypted_keys['api_key'],
                    secret=decrypted_keys['secret'],
                    passphrase=decrypted_keys.get('passphrase'),
                    mode=bot_config.get('mode', 'demo')
                )
                
                if success:
                    logger.info(f"✅ Биржа настроена для бота {bot_id}")
                    
                    # Основной цикл работы
                    logger.info(f"🔄 Запуск основного цикла бота {bot_id}")
                    cycle_count = 0
                    try:
                        while True:
                            try:
                                cycle_count += 1
                                logger.info(f"🔄 Цикл #{cycle_count} - выполнение стратегии")
                                await bot.execute_strategy()
                                logger.info(f"✅ Цикл #{cycle_count} завершен успешно")
                                await asyncio.sleep(30)  # Пауза между циклами
                            except KeyboardInterrupt:
                                logger.info(f"🛑 Получен сигнал остановки для бота {bot_id}")
                                break
                            except Exception as e:
                                logger.error(f"❌ Ошибка в цикле #{cycle_count} бота: {e}")
                                import traceback
                                logger.error(f"❌ Трассировка ошибки: {traceback.format_exc()}")
                                await asyncio.sleep(60)  # Пауза при ошибке
                    except Exception as e:
                        logger.error(f"❌ Критическая ошибка в основном цикле: {e}")
                        import traceback
                        logger.error(f"❌ Трассировка критической ошибки: {traceback.format_exc()}")
                else:
                    logger.error(f"❌ Не удалось настроить биржу для бота {bot_id}")
            else:
                logger.error(f"❌ Не удалось получить API ключи для бота {bot_id}")
        else:
            logger.error(f"❌ API ключ не указан для бота {bot_id}")
            
    except Exception as e:
        logger.error(f"❌ Критическая ошибка в боте {bot_id}: {e}")
    finally:
        logger.info(f"🛑 Бот {bot_id} завершил работу")

def main():
    """Главная функция"""
    parser = argparse.ArgumentParser(description='Real Grid Bot Runner')
    parser.add_argument('--config', required=True, help='Путь к файлу конфигурации')
    parser.add_argument('--bot-id', required=True, help='ID бота')
    parser.add_argument('--user-id', required=True, type=int, help='ID пользователя')
    
    args = parser.parse_args()
    
    print(f"🚀 Запуск бота {args.bot_id} для пользователя {args.user_id}")
    print(f"📁 Конфигурация: {args.config}")
    
    try:
        # Загружаем конфигурацию
        with open(args.config, 'r', encoding='utf-8') as f:
            bot_config = json.load(f)
        
        print(f"✅ Конфигурация загружена: {bot_config}")
        
        # Запускаем бота
        asyncio.run(run_grid_bot(args.bot_id, args.user_id, bot_config))
        
    except Exception as e:
        print(f"❌ Ошибка запуска бота: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
