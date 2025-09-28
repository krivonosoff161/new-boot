#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Multi-Asset Grid Trading Bot
v3.0: Интеграция зонального риск-менеджмента и улучшенной адаптации
"""

import ccxt.async_support as ccxt
import numpy as np
import talib
import asyncio
import time
import logging
import signal
import sys
import os
import json
import math
import collections
from datetime import datetime, timedelta
from telegram import Bot
from dotenv import load_dotenv

# Импорты существующих модулей
from core.log_helper import build_logger
from core.config_manager import ConfigManager
from core.ipc import GridBotIPCServer
import importlib.util
spec = importlib.util.spec_from_file_location("capital_distributor_v2", "capital_distributor_v2.0.py")
capital_distributor_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(capital_distributor_module)
CapitalDistributor = capital_distributor_module.CapitalDistributor

# Импорт новых модулей
from .zonal_risk_manager import ZonalRiskManager
from .adaptive_balance_manager import AdaptiveBalanceManager

load_dotenv()
os.makedirs('logs', exist_ok=True)

class EnhancedMultiAssetGridBot:
    """
    Улучшенный Multi-Asset Grid Trading Bot
    v3.0: Зональный риск-менеджмент + адаптивная сетка
    """
    
    def __init__(self):
        # Базовая инициализация
        self.logger = build_logger("enhanced_grid_bot")
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
        
        # 🆕 НОВОЕ: Зональный риск-менеджер
        self.risk_manager = ZonalRiskManager(self.config)
        self.logger.info("✅ Зональный риск-менеджер подключен")
        
        # 🆕 НОВОЕ: Adaptive Balance Manager v3.0
        self.balance_manager = AdaptiveBalanceManager(self.ex, self.config)
        self.logger.info("✅ Adaptive Balance Manager v3.0 подключен")
        
        # Состояние капитала
        self.total_capital = 0
        self.allocated_capital = {}
        self.last_redistribution = 0
        self.redistribution_interval = self.config.get('redistribution_interval', 1800)
        
        # Состояние сеток
        self.active_grids = {}  # {symbol: grid_data}
        self.last_grid_updates = {}
        self.executed_order_ids = set()
        
        # Параметры из конфига
        self.grid_config = self.config['grid']
        self.min_order_usd = self.grid_config['min_order_usd']
        self.max_levels = self.grid_config['max_levels']
        self.base_spacing = self.grid_config['base_spacing']
        self.cci_block = self.grid_config['cci_block']
        
        # Параметры индикаторов
        indicators_cfg = self.grid_config['indicators']
        self.rsi_period = indicators_cfg['rsi']['timeperiod']
        self.atr_period = indicators_cfg['atr']['timeperiod']
        self.bb_period = indicators_cfg['bb']['timeperiod']
        self.bb_nbdevup = indicators_cfg['bb']['nbdevup']
        self.bb_nbdevdn = indicators_cfg['bb']['nbdevdn']
        
        # IPC сервер
        self.ipc_server = GridBotIPCServer(self, 8080)
        
        self.logger.info("🚀 Enhanced Grid Bot v3.0 инициализирован")
    
    async def get_balances(self):
        """Получение балансов через Adaptive Balance Manager v3.0"""
        try:
            # Используем новый Adaptive Balance Manager
            user_capital = await self.balance_manager.get_user_capital(user_id=1)  # Default user для совместимости
            
            if user_capital.total_balance_usd == 0:
                self.logger.warning("⚠️ Баланс пользователя равен нулю")
                return {}
            
            # Преобразуем в старый формат для совместимости
            formatted_balances = {}
            for symbol in self.symbols:
                base_currency = symbol.split('/')[0]
                quote_currency = symbol.split('/')[1]
                
                base_balance = user_capital.currencies.get(base_currency, 0)
                quote_balance = user_capital.currencies.get(quote_currency, 0)
                
                formatted_balances[symbol] = {
                    'base': base_balance,
                    'quote': quote_balance
                }
            
            self.logger.info(f"💰 Получены балансы: ${user_capital.total_balance_usd:.2f} USD")
            return formatted_balances
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения балансов через Adaptive Manager: {e}")
            return {}
    
    async def analyze_market_regime(self, symbol, ohlcv):
        """
        Улучшенный анализ рыночного режима
        Возвращает: режим, множитель_спейсинга, уровни_сетки, волатильность, сила_тренда, RSI, CCI
        """
        try:
            if len(ohlcv) < 50:
                self.logger.warning(f"Недостаточно данных OHLCV для {symbol}")
                return 'neutral', 1.0, self.max_levels, 0.02, 20, 50, 0
                
            closes = np.array([candle[4] for candle in ohlcv])
            highs = np.array([candle[2] for candle in ohlcv])
            lows = np.array([candle[3] for candle in ohlcv])
            
            # Проверка на NaN
            if np.any(np.isnan(closes)) or np.any(np.isnan(highs)) or np.any(np.isnan(lows)):
                self.logger.warning(f"NaN в данных OHLCV для {symbol}")
                return 'neutral', 1.0, self.max_levels, 0.02, 20, 50, 0
            
            # Расчет волатильности (ATR)
            atr = talib.ATR(highs, lows, closes, timeperiod=self.atr_period)
            atr_value = atr[-1] if len(atr) > 0 and not np.isnan(atr[-1]) else 0.001 * closes[-1]
            avg_price = np.mean(closes)
            volatility = (atr_value / avg_price) if avg_price > 0 else 0.02
            
            # Сила тренда (ADX)
            adx = talib.ADX(highs, lows, closes, timeperiod=14)
            trend_strength = adx[-1] if len(adx) > 0 and not np.isnan(adx[-1]) else 20
            
            # RSI
            rsi = talib.RSI(closes, timeperiod=self.rsi_period)
            rsi_value = rsi[-1] if len(rsi) > 0 and not np.isnan(rsi[-1]) else 50
            
            # CCI
            cci = talib.CCI(highs, lows, closes, timeperiod=14)
            cci_value = cci[-1] if len(cci) > 0 and not np.isnan(cci[-1]) else 0
            
            # 🆕 УЛУЧШЕННОЕ: Определение режима рынка
            market_regime = self._determine_market_regime(
                closes, volatility, trend_strength, rsi_value, cci_value
            )
            
            # Адаптивные параметры
            spacing_mult, grid_levels = self._calculate_adaptive_params(
                market_regime, volatility, trend_strength
            )
            
            self.logger.debug(f"{symbol}: режим={market_regime}, волат={volatility:.4f}, "
                             f"тренд={trend_strength:.1f}, RSI={rsi_value:.1f}, CCI={cci_value:.1f}")
            
            return market_regime, spacing_mult, grid_levels, volatility, trend_strength, rsi_value, cci_value
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка анализа рынка для {symbol}: {e}")
            return 'neutral', 1.0, self.max_levels, 0.02, 20, 50, 0
    
    def _determine_market_regime(self, closes, volatility, trend_strength, rsi, cci):
        """Определяет режим рынка на основе множественных индикаторов"""
        
        # Анализ тренда по цене
        recent_closes = closes[-10:]
        price_trend = (recent_closes[-1] - recent_closes[0]) / recent_closes[0]
        
        # Классификация режима
        if volatility > 0.03:  # Высокая волатильность
            return 'volatile'
        elif trend_strength > 30 and price_trend > 0.02:  # Сильный восходящий тренд
            return 'bullish'
        elif trend_strength > 30 and price_trend < -0.02:  # Сильный нисходящий тренд
            return 'bearish'
        else:  # Боковой рынок
            return 'neutral'
    
    def _calculate_adaptive_params(self, market_regime, volatility, trend_strength):
        """Рассчитывает адаптивные параметры для режима рынка"""
        
        base_levels = self.max_levels
        base_spacing = 1.0
        
        if market_regime == 'volatile':
            # В волатильном рынке: меньше уровней, больше расстояние
            spacing_mult = 1.5 + volatility * 10
            grid_levels = max(3, int(base_levels * 0.7))
        elif market_regime == 'bullish':
            # В бычьем рынке: больше sell уровней
            spacing_mult = 1.0 + volatility * 5
            grid_levels = base_levels
        elif market_regime == 'bearish':
            # В медвежьем рынке: больше buy уровней
            spacing_mult = 1.0 + volatility * 5
            grid_levels = base_levels
        else:  # neutral
            spacing_mult = 1.0 + volatility * 3
            grid_levels = base_levels
        
        return spacing_mult, grid_levels
    
    async def create_enhanced_grid(self, symbol):
        """
        🆕 НОВЫЙ МЕТОД: Создание улучшенной сетки с зональным риск-менеджментом
        """
        current_time = time.time()
        
        # Cooldown проверка
        last_update = self.last_grid_updates.get(symbol, 0)
        cooldown_period = 60  # 1 минута
        
        if current_time - last_update < cooldown_period:
            self.logger.debug(f"⏳ {symbol}: Пропущено обновление из-за cooldown")
            return
            
        self.last_grid_updates[symbol] = current_time
        
        try:
            # 1. Получение данных
            balances = await self.get_balances()
            ticker = await self.ex.fetch_ticker(symbol)
            current_price = ticker['last']
            allocated_capital = self.allocated_capital.get(symbol, 0)
            
            # 2. Проверка капитала
            if allocated_capital < self.min_order_usd * 2:
                self.logger.info(f"⚠️ {symbol}: Недостаточный капитал ({allocated_capital:.2f} USDT)")
                return
            
            # 3. Анализ рынка
            ohlcv = await self.ex.fetch_ohlcv(symbol, '1m', limit=50)
            market_regime, spacing_mult, grid_levels, volatility, trend_strength, rsi, cci = await self.analyze_market_regime(symbol, ohlcv)
            
            # 4. CCI фильтр
            if cci < self.cci_block:
                self.logger.info(f"⚠️ {symbol}: Заблокировано CCI фильтром (CCI={cci:.2f})")
                return
            
            # 🆕 5. НОВОЕ: Создание оптимизированной сетки через зональный риск-менеджер
            optimized_levels = self.risk_manager.optimize_grid_levels(
                current_price=current_price,
                available_capital=allocated_capital,
                base_spacing=self.base_spacing * spacing_mult,
                max_levels=grid_levels,
                volatility=volatility,
                market_regime=market_regime
            )
            
            # 6. Размещение ордеров
            await self._place_optimized_orders(symbol, optimized_levels, current_price)
            
            # 7. Сохранение состояния сетки
            self.active_grids[symbol] = {
                'timestamp': current_time,
                'current_price': current_price,
                'market_regime': market_regime,
                'volatility': volatility,
                'levels': optimized_levels,
                'total_levels': len(optimized_levels['buy_levels']) + len(optimized_levels['sell_levels'])
            }
            
            self.logger.info(f"✅ {symbol}: Создана улучшенная сетка - "
                           f"{len(optimized_levels['buy_levels'])} buy + "
                           f"{len(optimized_levels['sell_levels'])} sell уровней")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка создания сетки для {symbol}: {e}")
    
    async def _place_optimized_orders(self, symbol, optimized_levels, current_price):
        """Размещение оптимизированных ордеров"""
        
        # Размещаем buy ордера
        for level in optimized_levels['buy_levels']:
            if level['price'] < current_price * 0.95:  # Только если цена достаточно далеко
                try:
                    # Здесь был бы реальный ордер на биржу
                    self.logger.debug(f"📉 {symbol}: Buy order ${level['price']:.2f} "
                                    f"size=${level['size']:.2f} zone={level['zone']}")
                    
                    # В демо режиме просто логируем
                    
                except Exception as e:
                    self.logger.error(f"❌ Ошибка размещения buy ордера {symbol}: {e}")
        
        # Размещаем sell ордера
        for level in optimized_levels['sell_levels']:
            if level['price'] > current_price * 1.05:  # Только если цена достаточно далеко
                try:
                    # Здесь был бы реальный ордер на биржу
                    self.logger.debug(f"📈 {symbol}: Sell order ${level['price']:.2f} "
                                    f"size=${level['size']:.2f} zone={level['zone']}")
                    
                    # В демо режиме просто логируем
                    
                except Exception as e:
                    self.logger.error(f"❌ Ошибка размещения sell ордера {symbol}: {e}")
    
    async def monitor_and_update_grids(self):
        """Мониторинг и обновление сеток"""
        while self.running:
            try:
                for symbol in self.symbols:
                    await self.create_enhanced_grid(symbol)
                
                # Пауза между итерациями
                await asyncio.sleep(30)  # 30 секунд
                
            except Exception as e:
                self.logger.error(f"❌ Ошибка мониторинга сеток: {e}")
                await asyncio.sleep(60)
    
    async def update_capital(self):
        """Обновление информации о капитале"""
        try:
            balance = await self.ex.fetch_balance()
            
            # Рассчитываем общий капитал в USDT
            total_usdt = balance['total'].get('USDT', 0)
            
            # Добавляем стоимость других активов
            for symbol in self.symbols:
                base_currency = symbol.split('/')[0]
                base_amount = balance['total'].get(base_currency, 0)
                
                if base_amount > 0:
                    try:
                        ticker = await self.ex.fetch_ticker(symbol)
                        total_usdt += base_amount * ticker['last']
                    except:
                        pass
            
            self.total_capital = total_usdt
            self.logger.debug(f"💰 Общий капитал: ${self.total_capital:.2f} USDT")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка обновления капитала: {e}")
    
    async def distribute_capital(self):
        """Распределение капитала между символами"""
        try:
            self.logger.info("🔄 Начало перераспределения капитала...")
            
            distributor = CapitalDistributor(self.ex)
            allocations = await distributor.distribute_for_strategy('grid', self.symbols)
            
            self.allocated_capital = allocations
            
            for symbol, amount in self.allocated_capital.items():
                self.logger.info(f"💰 {symbol}: выделено ${amount:.2f} USDT")
                
            self.logger.info("✅ Перераспределение капитала завершено.")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка распределения капитала: {e}")
    
    async def send_telegram_notification(self, message):
        """Отправка уведомлений в Telegram"""
        try:
            for chat_id in self.chat_ids:
                await self.tg_bot.send_message(chat_id=chat_id, text=message, parse_mode='HTML')
        except Exception as e:
            self.logger.error(f"❌ Ошибка отправки в Telegram: {e}")
    
    async def get_status_report(self):
        """Получение отчета о состоянии бота"""
        active_grids_count = len(self.active_grids)
        total_levels = sum(grid['total_levels'] for grid in self.active_grids.values())
        
        # Статистика по зонам
        zone_stats = self.risk_manager.get_zone_statistics()
        
        report = f"""
🤖 <b>Enhanced Grid Bot v3.0 Status</b>

💰 <b>Капитал:</b> ${self.total_capital:.2f} USDT
📊 <b>Активных сеток:</b> {active_grids_count}
🎯 <b>Всего уровней:</b> {total_levels}

🔥 <b>Зональный риск-менеджмент:</b>
• Ближняя зона (0-2%): TP×{zone_stats['close']['tp_multiplier']:.1f}, SL×{zone_stats['close']['sl_multiplier']:.1f}
• Средняя зона (2-5%): TP×{zone_stats['medium']['tp_multiplier']:.1f}, SL×{zone_stats['medium']['sl_multiplier']:.1f}  
• Дальняя зона (5-15%): TP×{zone_stats['far']['tp_multiplier']:.1f}, SL×{zone_stats['far']['sl_multiplier']:.1f}

⏰ <b>Время:</b> {datetime.now().strftime('%H:%M:%S')}
        """
        
        return report.strip()
    
    async def run(self):
        """Основной цикл работы бота"""
        self.logger.info("🚀 Запуск Enhanced Grid Bot v3.0...")
        
        try:
            # Инициализация капитала
            await self.update_capital()
            await self.distribute_capital()
            
            # Отправка стартового уведомления
            start_message = await self.get_status_report()
            await self.send_telegram_notification(f"🚀 <b>Enhanced Grid Bot запущен!</b>\n\n{start_message}")
            
            # Основной цикл
            tasks = [
                asyncio.create_task(self.monitor_and_update_grids()),
                asyncio.create_task(self._periodic_capital_update()),
                asyncio.create_task(self._periodic_status_report())
            ]
            
            await asyncio.gather(*tasks)
            
        except Exception as e:
            self.logger.error(f"❌ Критическая ошибка в основном цикле: {e}")
            await self.send_telegram_notification(f"❌ <b>Критическая ошибка:</b> {e}")
    
    async def _periodic_capital_update(self):
        """Периодическое обновление капитала"""
        while self.running:
            try:
                await self.update_capital()
                
                # Перераспределение капитала каждые 30 минут
                current_time = time.time()
                if current_time - self.last_redistribution > self.redistribution_interval:
                    await self.distribute_capital()
                    self.last_redistribution = current_time
                
                await asyncio.sleep(300)  # 5 минут
                
            except Exception as e:
                self.logger.error(f"❌ Ошибка периодического обновления капитала: {e}")
                await asyncio.sleep(300)
    
    async def update_capital(self):
        """Обновление информации о капитале через Adaptive Balance Manager"""
        try:
            user_capital = await self.balance_manager.get_user_capital(user_id=1, force_refresh=True)
            self.total_capital = user_capital.total_balance_usd
            
            if self.total_capital <= 0:
                self.logger.warning("⚠️ Общий капитал равен нулю или отрицателен.")
                return
            
            self.logger.info(f"💰 Обновлен капитал: ${self.total_capital:.2f} USD")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка обновления капитала: {e}")
    
    async def distribute_capital(self):
        """Распределение капитала через Adaptive Balance Manager"""
        try:
            self.logger.info("🔄 Начало перераспределения капитала...")
            
            user_capital = await self.balance_manager.get_user_capital(user_id=1)
            allocation = self.balance_manager.get_optimal_allocation(user_capital)
            
            # Обновляем распределение для Grid стратегии
            grid_capital = allocation.grid_allocation
            
            if grid_capital > 0:
                # Распределяем капитал между торговыми парами
                capital_per_pair = grid_capital / len(allocation.recommended_pairs)
                
                for symbol in allocation.recommended_pairs:
                    if symbol in self.symbols:  # Проверяем, что пара активна
                        self.allocated_capital[symbol] = capital_per_pair
                        
                self.logger.info(f"💰 Распределено ${grid_capital:.2f} для Grid торговли")
                self.logger.info(f"📊 Капитал на пару: ${capital_per_pair:.2f}")
            else:
                self.logger.warning("⚠️ Недостаточно средств для Grid торговли")
            
            self.logger.info("✅ Перераспределение капитала завершено.")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка распределения капитала: {e}")
    
    async def _periodic_status_report(self):
        """Периодические отчеты о состоянии"""
        while self.running:
            try:
                await asyncio.sleep(3600)  # 1 час
                
                status_report = await self.get_status_report()
                await self.send_telegram_notification(f"📊 <b>Периодический отчет</b>\n\n{status_report}")
                
            except Exception as e:
                self.logger.error(f"❌ Ошибка периодического отчета: {e}")
    
    def stop(self):
        """Остановка бота"""
        self.logger.info("🛑 Остановка Enhanced Grid Bot...")
        self.running = False

# Точка входа
async def main():
    bot = EnhancedMultiAssetGridBot()
    
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
        print("🛑 Бот остановлен пользователем")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        logging.error(f"Критическая ошибка: {e}")
