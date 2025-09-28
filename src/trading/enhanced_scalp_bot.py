#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Multi-Asset Scalp Trading Bot v3.0
Интеграция ML, улучшенных сигналов и оптимизации балансов
"""

import ccxt.async_support as ccxt
import numpy as np
import asyncio
import time
import logging
import os
import sys
from datetime import datetime, timedelta
from telegram import Bot
from dotenv import load_dotenv
from typing import Dict, List, Optional, Any

# Импорты существующих модулей
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from core.log_helper import build_logger
from core.config_manager import ConfigManager
from core.ipc import ScalpBotIPCServer

# Импорты улучшенных модулей
from .ml_signal_engine import MLSignalEngine
from .advanced_signal_generator import AdvancedSignalGenerator, ScalpSignal
from .balance_optimizer import BalanceOptimizer
from .adaptive_balance_manager import AdaptiveBalanceManager

load_dotenv()

class EnhancedMultiAssetScalpBot:
    """
    Enhanced Multi-Asset Scalp Trading Bot v3.0
    
    Новые возможности:
    - 🤖 Машинное обучение для предсказаний
    - 🎯 Улучшенные сигналы (6 стратегий)
    - 💰 Оптимизированная работа с балансами
    - 📊 Анализ стакана заявок
    - 🔄 Координация с Grid ботом
    - 📈 Детальная аналитика
    """
    
    def __init__(self):
        # Базовая инициализация
        self.logger = build_logger("enhanced_scalp_bot")
        self.config_manager = ConfigManager()
        self.config = self.config_manager.get_config()
        
        # Инициализация биржи
        API_KEY = os.getenv('OKX_API_KEY') or os.getenv('API_KEY')
        API_SECRET = os.getenv('OKX_SECRET_KEY') or os.getenv('API_SECRET')
        PASSPHRASE = os.getenv('OKX_PASSPHRASE') or os.getenv('PASSPHRASE')
        if not all([API_KEY, API_SECRET, PASSPHRASE]):
            raise ValueError("❌ Отсутствуют обязательные переменные окружения: OKX_API_KEY, OKX_SECRET_KEY, OKX_PASSPHRASE")
            
        # Инициализация биржи для Demo Trading
        from core.exchange_mode_manager import exchange_mode_manager
        
        # Создаем экземпляр биржи через Exchange Mode Manager
        self.ex = exchange_mode_manager.create_exchange_instance(
            exchange_name='okx',
            api_key=API_KEY,
            secret=API_SECRET,
            passphrase=PASSPHRASE,
            mode='demo'  # Демо режим
        )
        
        # Основные параметры
        self.symbols = self.config['symbols']
        self.chat_ids = self.config['chat_ids']
        self.tg_bot = Bot(token=os.getenv('TELEGRAM_BOT_TOKEN') or os.getenv('TELEGRAM_TOKEN'))
        self.running = True
        
        # 🆕 НОВОЕ: ML Signal Engine
        self.ml_engine = MLSignalEngine(self.config)
        self.logger.info("✅ ML Signal Engine подключен")
        
        # 🆕 НОВОЕ: Advanced Signal Generator
        self.signal_generator = AdvancedSignalGenerator(self.config, self.ml_engine)
        self.logger.info("✅ Advanced Signal Generator подключен")
        
        # 🆕 НОВОЕ: Balance Optimizer
        self.balance_optimizer = BalanceOptimizer(self.ex, self.config)
        self.logger.info("✅ Balance Optimizer подключен")
        
        # 🆕 НОВОЕ: Adaptive Balance Manager v3.0
        self.adaptive_balance_manager = AdaptiveBalanceManager(self.ex, self.config)
        self.logger.info("✅ Adaptive Balance Manager v3.0 подключен")
        
        # Параметры скальпинга
        self.scalp_config = self.config['scalp']
        self.min_order_usd = self.scalp_config['min_order_usd']
        self.max_positions = self.scalp_config['max_positions']
        self.position_size_percent = self.scalp_config['position_size_percent']
        self.max_hold_seconds = self.scalp_config['max_hold_seconds']
        
        # Состояние позиций
        self.positions = {}  # {symbol: position_data}
        self.open_orders = {}  # {order_id: order_data}
        self.last_signals = {}  # {symbol: last_signal_time}
        
        # Статистика
        self.total_trades = 0
        self.winning_trades = 0
        self.total_pnl = 0.0
        self.start_time = time.time()
        
        # IPC сервер
        self.ipc_server = ScalpBotIPCServer(self, 8081)
        
        self.logger.info("🚀 Enhanced Scalp Bot v3.0 инициализирован")
    
    async def get_balances(self):
        """Получение оптимизированных балансов"""
        return await self.balance_optimizer.get_balances(self.symbols)
    
    async def analyze_market_and_generate_signals(self):
        """Анализ рынка и генерация сигналов для всех символов"""
        while self.running:
            try:
                for symbol in self.symbols:
                    if len(self.positions) >= self.max_positions:
                        self.logger.debug(f"⚠️ Достигнуто максимальное количество позиций ({self.max_positions})")
                        break
                    
                    await self._process_symbol(symbol)
                
                # Проверяем существующие позиции
                await self._monitor_positions()
                
                # Пауза между итерациями
                await asyncio.sleep(5)  # 5 секунд
                
            except Exception as e:
                self.logger.error(f"❌ Ошибка анализа рынка: {e}")
                await asyncio.sleep(30)
    
    async def _process_symbol(self, symbol: str):
        """Обработка одного символа"""
        try:
            # Проверка cooldown
            current_time = time.time()
            last_signal_time = self.last_signals.get(symbol, 0)
            if current_time - last_signal_time < 30:  # 30 секунд cooldown
                return
            
            # Получаем данные
            ohlcv = await self.ex.fetch_ohlcv(symbol, '1m', limit=100)
            
            # Получаем стакан заявок (опционально)
            order_book = None
            try:
                order_book = await self.ex.fetch_order_book(symbol, limit=20)
            except:
                pass  # Не критично если стакан недоступен
            
            # Генерируем сигнал
            signal = await self.signal_generator.generate_signal(symbol, ohlcv, order_book)
            
            if signal and signal.strength >= 0.6:
                await self._execute_signal(symbol, signal)
                self.last_signals[symbol] = current_time
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки {symbol}: {e}")
    
    async def _execute_signal(self, symbol: str, signal: ScalpSignal):
        """Исполнение торгового сигнала"""
        try:
            # Проверяем есть ли уже позиция по этому символу
            if symbol in self.positions:
                self.logger.debug(f"⚠️ {symbol}: Уже есть открытая позиция")
                return
            
            # Получаем балансы
            balances = await self.get_balances()
            symbol_balance = balances.get(symbol)
            
            if not symbol_balance:
                self.logger.warning(f"⚠️ {symbol}: Нет информации о балансе")
                return
            
            # Рассчитываем размер позиции
            available_capital = symbol_balance.quote_usd_value  # USDT баланс
            position_size_usd = available_capital * self.position_size_percent
            
            if position_size_usd < self.min_order_usd:
                self.logger.warning(f"⚠️ {symbol}: Недостаточный капитал ({position_size_usd:.2f} < {self.min_order_usd})")
                return
            
            # В демо режиме просто логируем
            self.logger.info(f"🎯 {symbol}: СИГНАЛ {signal.direction.upper()}")
            self.logger.info(f"   💪 Сила: {signal.strength:.3f}")
            self.logger.info(f"   🎯 Стратегия: {signal.strategy_name}")
            self.logger.info(f"   💰 Размер: ${position_size_usd:.2f}")
            self.logger.info(f"   📈 TP: ${signal.tp_price:.2f}")
            self.logger.info(f"   📉 SL: ${signal.sl_price:.2f}")
            
            # Сохраняем "позицию" для демо
            self.positions[symbol] = {
                'signal': signal,
                'size_usd': position_size_usd,
                'entry_time': time.time(),
                'entry_price': signal.entry_price,
                'direction': signal.direction,
                'tp_price': signal.tp_price,
                'sl_price': signal.sl_price,
                'strategy': signal.strategy_name
            }
            
            self.total_trades += 1
            
            # Отправляем уведомление в Telegram
            await self._send_signal_notification(symbol, signal, position_size_usd)
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка исполнения сигнала {symbol}: {e}")
    
    async def _monitor_positions(self):
        """Мониторинг открытых позиций"""
        current_time = time.time()
        positions_to_close = []
        
        for symbol, position in self.positions.items():
            try:
                # Проверка времени удержания
                hold_time = current_time - position['entry_time']
                if hold_time > self.max_hold_seconds:
                    positions_to_close.append((symbol, 'timeout'))
                    continue
                
                # Проверка TP/SL (в демо режиме симулируем)
                current_price = await self._get_current_price(symbol)
                
                if position['direction'] == 'buy':
                    if current_price >= position['tp_price']:
                        positions_to_close.append((symbol, 'tp'))
                    elif current_price <= position['sl_price']:
                        positions_to_close.append((symbol, 'sl'))
                else:  # sell
                    if current_price <= position['tp_price']:
                        positions_to_close.append((symbol, 'tp'))
                    elif current_price >= position['sl_price']:
                        positions_to_close.append((symbol, 'sl'))
                
            except Exception as e:
                self.logger.error(f"❌ Ошибка мониторинга позиции {symbol}: {e}")
        
        # Закрываем позиции
        for symbol, reason in positions_to_close:
            await self._close_position(symbol, reason)
    
    async def _close_position(self, symbol: str, reason: str):
        """Закрытие позиции"""
        try:
            if symbol not in self.positions:
                return
            
            position = self.positions[symbol]
            current_price = await self._get_current_price(symbol)
            
            # Расчет PnL (упрощенный для демо)
            entry_price = position['entry_price']
            if position['direction'] == 'buy':
                pnl_percent = (current_price - entry_price) / entry_price
            else:
                pnl_percent = (entry_price - current_price) / entry_price
            
            pnl_usd = position['size_usd'] * pnl_percent
            self.total_pnl += pnl_usd
            
            if pnl_usd > 0:
                self.winning_trades += 1
            
            # Логирование закрытия
            reason_emoji = {'tp': '🎯', 'sl': '🛑', 'timeout': '⏰'}
            self.logger.info(f"{reason_emoji.get(reason, '📤')} {symbol}: Позиция закрыта ({reason})")
            self.logger.info(f"   💰 PnL: ${pnl_usd:.2f} ({pnl_percent*100:.2f}%)")
            self.logger.info(f"   ⏱️ Время: {time.time() - position['entry_time']:.0f}s")
            
            # Удаляем позицию
            del self.positions[symbol]
            
            # Уведомление в Telegram
            await self._send_close_notification(symbol, reason, pnl_usd, pnl_percent)
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка закрытия позиции {symbol}: {e}")
    
    async def _get_current_price(self, symbol: str) -> float:
        """Получение текущей цены"""
        try:
            ticker = await self.ex.fetch_ticker(symbol)
            return ticker['last']
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения цены {symbol}: {e}")
            return 0.0
    
    async def _send_signal_notification(self, symbol: str, signal: ScalpSignal, size_usd: float):
        """Отправка уведомления о новом сигнале"""
        try:
            strategy_emoji = {
                'combo_v3': '🔥',
                'momentum_scalp': '⚡',
                'mean_reversion': '🔄',
                'volume_profile': '📊',
                'breakout': '💥',
                'adaptive_v3': '🎯'
            }
            
            emoji = strategy_emoji.get(signal.strategy_name, '📈')
            direction_emoji = '📈' if signal.direction == 'buy' else '📉'
            
            message = f"""
{emoji} <b>ENHANCED SCALP СИГНАЛ v3.0</b>

{direction_emoji} <b>{symbol}: {signal.direction.upper()}</b>

🎯 <b>Стратегия:</b> {signal.strategy_name}
💪 <b>Сила сигнала:</b> {signal.strength:.3f}
🎲 <b>Уверенность:</b> {signal.confidence:.3f}

💰 <b>Торговые параметры:</b>
• Размер: ${size_usd:.2f}
• Вход: ${signal.entry_price:.4f}
• TP: ${signal.tp_price:.4f}
• SL: ${signal.sl_price:.4f}

⏰ <b>Время:</b> {datetime.now().strftime('%H:%M:%S')}

<i>Enhanced Scalp v3.0 - ML + улучшенные сигналы</i>
            """
            
            for chat_id in self.chat_ids:
                await self.tg_bot.send_message(chat_id=chat_id, text=message, parse_mode='HTML')
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка отправки уведомления: {e}")
    
    async def _send_close_notification(self, symbol: str, reason: str, pnl_usd: float, pnl_percent: float):
        """Отправка уведомления о закрытии позиции"""
        try:
            reason_text = {
                'tp': 'Take Profit достигнут',
                'sl': 'Stop Loss сработал', 
                'timeout': 'Таймаут позиции'
            }
            
            pnl_emoji = '💚' if pnl_usd > 0 else '❤️'
            reason_emoji = {'tp': '🎯', 'sl': '🛑', 'timeout': '⏰'}
            
            message = f"""
{reason_emoji.get(reason, '📤')} <b>ПОЗИЦИЯ ЗАКРЫТА</b>

📊 <b>{symbol}</b>
🔹 <b>Причина:</b> {reason_text.get(reason, reason)}

{pnl_emoji} <b>Результат:</b>
• PnL: ${pnl_usd:.2f}
• Процент: {pnl_percent*100:.2f}%

📈 <b>Общая статистика:</b>
• Всего сделок: {self.total_trades}
• Прибыльных: {self.winning_trades}
• Винрейт: {(self.winning_trades/self.total_trades*100):.1f}%
• Общий PnL: ${self.total_pnl:.2f}

⏰ <b>Время:</b> {datetime.now().strftime('%H:%M:%S')}
            """
            
            for chat_id in self.chat_ids:
                await self.tg_bot.send_message(chat_id=chat_id, text=message, parse_mode='HTML')
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка отправки уведомления о закрытии: {e}")
    
    async def get_status_report(self) -> str:
        """Получение детального отчета о состоянии"""
        try:
            uptime = time.time() - self.start_time
            uptime_str = str(timedelta(seconds=int(uptime)))
            
            # Статистика ML
            ml_stats = self.ml_engine.get_statistics()
            
            # Статистика сигналов
            signal_stats = self.signal_generator.get_statistics()
            
            # Статистика балансов
            balance_stats = await self.balance_optimizer.get_statistics()
            
            # Винрейт
            winrate = (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0
            
            report = f"""
🤖 <b>Enhanced Scalp Bot v3.0 Status</b>

⏰ <b>Время работы:</b> {uptime_str}
📊 <b>Активных позиций:</b> {len(self.positions)}
💰 <b>Общий PnL:</b> ${self.total_pnl:.2f}

📈 <b>Торговая статистика:</b>
• Всего сделок: {self.total_trades}
• Прибыльных: {self.winning_trades}
• Винрейт: {winrate:.1f}%
• Средний PnL: ${(self.total_pnl/self.total_trades if self.total_trades > 0 else 0):.2f}

🤖 <b>ML Engine:</b>
• Доступность: {'✅' if ml_stats['ml_available'] else '❌'}
• Обучен: {'✅' if ml_stats['is_trained'] else '❌'}
• Предсказаний: {ml_stats['predictions_made']}
• Точность: {ml_stats['accuracy']:.1%}

🎯 <b>Signal Generator:</b>
• Сигналов сгенерировано: {signal_stats['signals_generated']}
• Успешных: {signal_stats['successful_signals']}
• Успешность: {signal_stats['success_rate']:.1%}

💰 <b>Balance Optimizer:</b>
• Попаданий в кэш: {balance_stats['cache_hit_rate']:.1f}%
• API запросов: {balance_stats['api_calls']}
• Ошибок: {balance_stats['errors']}

⏰ <b>Время:</b> {datetime.now().strftime('%H:%M:%S')}
            """
            
            return report.strip()
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка создания отчета: {e}")
            return "❌ Ошибка получения статуса"
    
    async def get_positions_info(self) -> str:
        """Информация об открытых позициях"""
        try:
            if not self.positions:
                return "📊 Открытых позиций нет"
            
            info = "📊 <b>ОТКРЫТЫЕ ПОЗИЦИИ</b>\n\n"
            
            for symbol, position in self.positions.items():
                current_price = await self._get_current_price(symbol)
                entry_price = position['entry_price']
                
                # Расчет текущего PnL
                if position['direction'] == 'buy':
                    current_pnl_percent = (current_price - entry_price) / entry_price
                else:
                    current_pnl_percent = (entry_price - current_price) / entry_price
                
                current_pnl_usd = position['size_usd'] * current_pnl_percent
                
                # Время удержания
                hold_time = time.time() - position['entry_time']
                
                direction_emoji = '📈' if position['direction'] == 'buy' else '📉'
                pnl_emoji = '💚' if current_pnl_usd > 0 else '❤️'
                
                info += f"""
{direction_emoji} <b>{symbol}</b>
🎯 Стратегия: {position['strategy']}
💰 Размер: ${position['size_usd']:.2f}
📊 Вход: ${entry_price:.4f}
📈 Текущая: ${current_price:.4f}
{pnl_emoji} PnL: ${current_pnl_usd:.2f} ({current_pnl_percent*100:.2f}%)
⏱️ Время: {int(hold_time)}s
📈 TP: ${position['tp_price']:.4f}
📉 SL: ${position['sl_price']:.4f}

                """
            
            return info.strip()
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения информации о позициях: {e}")
            return "❌ Ошибка получения информации о позициях"
    
    async def run(self):
        """Основной цикл работы бота"""
        self.logger.info("🚀 Запуск Enhanced Scalp Bot v3.0...")
        
        try:
            # Отправка стартового уведомления
            start_message = f"""
🚀 <b>Enhanced Scalp Bot v3.0 запущен!</b>

🔥 <b>Активированы улучшения:</b>
• ✅ ML Signal Engine
• ✅ Advanced Signal Generator (6 стратегий)
• ✅ Balance Optimizer
• ✅ Анализ стакана заявок

📊 <b>Параметры:</b>
• Символов: {len(self.symbols)}
• Макс. позиций: {self.max_positions}
• Мин. ордер: ${self.min_order_usd}
• Макс. время: {self.max_hold_seconds}s

🎯 <b>Стратегии:</b>
• Combo v3.0 (ML + технические)
• Momentum Scalp
• Mean Reversion
• Volume Profile
• Breakout
• Adaptive v3.0

<i>Система готова к улучшенному скальпингу!</i>
            """
            
            for chat_id in self.chat_ids:
                await self.tg_bot.send_message(chat_id=chat_id, text=start_message, parse_mode='HTML')
            
            # Основной цикл
            tasks = [
                asyncio.create_task(self.analyze_market_and_generate_signals()),
                asyncio.create_task(self._periodic_status_report()),
                asyncio.create_task(self._periodic_ml_update())
            ]
            
            await asyncio.gather(*tasks)
            
        except Exception as e:
            self.logger.error(f"❌ Критическая ошибка в основном цикле: {e}")
    
    async def _periodic_status_report(self):
        """Периодические отчеты"""
        while self.running:
            try:
                await asyncio.sleep(1800)  # 30 минут
                
                status_report = await self.get_status_report()
                
                for chat_id in self.chat_ids:
                    await self.tg_bot.send_message(
                        chat_id=chat_id, 
                        text=f"📊 <b>Периодический отчет Scalp v3.0</b>\n\n{status_report}", 
                        parse_mode='HTML'
                    )
                    
            except Exception as e:
                self.logger.error(f"❌ Ошибка периодического отчета: {e}")
    
    async def _periodic_ml_update(self):
        """Периодическое обновление ML моделей"""
        while self.running:
            try:
                await asyncio.sleep(3600)  # 1 час
                
                # Здесь можно добавить логику обновления ML моделей
                # на основе результатов торговли
                
                if len(self.ml_engine.training_data) > 100:
                    self.logger.info("🎓 Обновление ML моделей...")
                    results = self.ml_engine.train_models()
                    
                    if results:
                        self.logger.info(f"✅ ML модели обновлены: {results}")
                
            except Exception as e:
                self.logger.error(f"❌ Ошибка обновления ML: {e}")
    
    def stop(self):
        """Остановка бота"""
        self.logger.info("🛑 Остановка Enhanced Scalp Bot...")
        self.running = False

# Точка входа
async def main():
    bot = EnhancedMultiAssetScalpBot()
    
    # Запуск IPC сервера
    if bot.ipc_server:
        await bot.ipc_server.start()
        
    await bot.run()

if __name__ == "__main__":
    if not os.path.exists('.env'):
        print("❌ Файл .env не найден!")
        print("Создайте файл .env с вашими API ключами")
        sys.exit(1)
        
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Enhanced Scalp Bot остановлен пользователем")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        logging.error(f"Критическая ошибка: {e}")


