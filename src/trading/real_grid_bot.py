# v4.0 (+стоп-лоссы, улучшенный анализ тренда, риск-менеджмент, MACD, Bollinger Bands)
"""
Real Grid Trading Bot - интегрированная версия из предыдущей версии проекта.
v4.0: Добавлены стоп-лоссы, улучшенный анализ тренда, риск-менеджмент, MACD, Bollinger Bands.
"""
import ccxt.async_support as ccxt
import numpy as np
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
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field

# Импорты из текущего проекта
from core.log_helper import build_logger
from core.config_manager import ConfigManager
from core.exchange_mode_manager import exchange_mode_manager
from .base_trading_bot import BaseTradingBot, TradeEvent
from .capital_distributor import CapitalDistributor
from .adaptive_capital_distributor import AdaptiveCapitalDistributor, TradingMode
from .risk_manager import RiskManager, RiskLimits
from .market_analyzer import MarketAnalyzer, MarketRegime, TechnicalIndicators

@dataclass
class GridOrder:
    """Ордер в Grid сетке"""
    order_id: str
    symbol: str
    type: str  # buy/sell
    price: float
    amount: float
    level: int
    mode: str = 'base'
    created_at: float = field(default_factory=time.time)

class RealGridBot(BaseTradingBot):
    """
    Real Grid Trading Bot с адаптивной системой торговли.
    v3.0: Интеграция с BaseTradingBot и адаптивные режимы.
    """

    def __init__(self, user_id: int, config: Dict[str, any] = None):
        """
        Инициализация Real Grid Bot
        
        Args:
            user_id: ID пользователя
            config: Конфигурация бота
        """
        super().__init__('grid', user_id, config)
        
        # Инициализируем торговые пары из конфигурации
        if config and 'trading_pairs' in config:
            self.symbols = config['trading_pairs']
            self.logger.info(f"📊 Загружены торговые пары из конфигурации: {self.symbols}")
        else:
            self.logger.warning("⚠️ Торговые пары не найдены в конфигурации")
        
        # Состояние Grid-бота
        self.asset_grids = {}  # {symbol: {order_id: GridOrder}}
        self.executed_order_ids = collections.deque(maxlen=1000)
        self.last_grid_updates = {}
        
        # Параметры из конфига
        grid_config = self.config.get('grid', {})
        self.base_spacing = grid_config.get('base_spacing', 0.008)
        self.max_levels = grid_config.get('max_levels', 6)
        self.min_order_usd = grid_config.get('min_order_usd', 20)
        self.grid_mode = grid_config.get('grid_mode', 'spot')  # spot/futures
        self.cci_block = grid_config.get('cci_block', -100)
        
        # Адаптивные параметры
        self.tp_multiplier = 1.0
        
        # Capital Distributor
        self.capital_distributor = None
        self.adaptive_capital_distributor = None
        
        # Новые компоненты v4.0
        self.risk_manager = None
        self.market_analyzer = None
        
        # Адаптивная система
        self.current_trading_mode = TradingMode.AUTOMATIC
        self.pair_analyses = {}
        self.floating_profit_tracking = {}
        
        # Настройки риск-менеджмента
        risk_limits = RiskLimits(
            max_drawdown_pct=grid_config.get('max_drawdown_pct', 15.0),
            max_position_pct=grid_config.get('max_position_pct', 20.0),
            max_correlation=grid_config.get('max_correlation', 0.7),
            stop_loss_pct=grid_config.get('stop_loss_pct', 2.0),
            trailing_stop_pct=grid_config.get('trailing_stop_pct', 1.5),
            atr_multiplier=grid_config.get('atr_multiplier', 2.0)
        )
        
        # Инициализация компонентов
        self.risk_manager = RiskManager(user_id, risk_limits, risk_mode='automatic')
        self.market_analyzer = MarketAnalyzer(user_id)

    def setup_exchange(self, exchange_name: str, api_key: str, secret: str, passphrase: str = None, mode: str = "demo"):
        """Настройка биржи и всех компонентов"""
        success = super().setup_exchange(exchange_name, api_key, secret, passphrase, mode)
        if success and self.ex:
            self.capital_distributor = CapitalDistributor(self.ex, self.user_id)
            self.adaptive_capital_distributor = AdaptiveCapitalDistributor(self.ex, self.user_id, self.config)
            
            # Получаем реальный баланс
            try:
                balance = self.ex.fetch_balance({'type': 'spot'})
                real_balance = 0.0
                if 'total' in balance and 'USDT' in balance['total']:
                    real_balance = float(balance['total']['USDT'])
                else:
                    # Если USDT нет, берем первый доступный баланс
                    for currency, amount in balance.get('total', {}).items():
                        if amount > 0:
                            real_balance = float(amount)
                            break
                
                self.logger.info(f"💰 Реальный баланс: ${real_balance:.2f}")
                
                # Инициализация риск-менеджера с реальным балансом
                self.risk_manager.set_exchange(self.ex, real_balance)
                
                # Определяем режим торговли на основе капитала
                recommended_mode = self.risk_manager.get_recommended_mode(real_balance)
                self.current_trading_mode = TradingMode(recommended_mode)
                self.risk_manager.set_risk_mode(recommended_mode)
                
                self.logger.info(f"🎯 Режим торговли: {self.current_trading_mode.value} (капитал: ${real_balance:.2f})")
                
            except Exception as e:
                self.logger.error(f"❌ Ошибка получения баланса: {e}")
                # Fallback к $1000 если не удалось получить баланс
                self.risk_manager.set_exchange(self.ex, 1000.0)
        return success

    async def analyze_market_regime(self, symbol: str, ohlcv: List) -> Tuple:
        """
        Улучшенный анализ рыночного режима с использованием MarketAnalyzer
        
        Args:
            symbol: Торговая пара
            ohlcv: Данные OHLCV
            
        Returns:
            Tuple: (mode, spacing_mult, grid_levels, volatility, trend_strength, rsi, cci)
        """
        try:
            if len(ohlcv) < 20:
                self.logger.warning(f"Недостаточно данных OHLCV для {symbol}")
                return 'neutral', 1.0, 6, 0.01, 0, 50, 0
            
            # Используем новый MarketAnalyzer
            regime = self.market_analyzer.analyze_market_regime(ohlcv)
            indicators = self.market_analyzer.get_technical_indicators(ohlcv)
            
            # Проверяем, стоит ли торговать
            should_trade, reason = self.market_analyzer.should_trade(regime, indicators)
            
            if not should_trade:
                self.logger.info(f"⚠️ {symbol}: Торговля не рекомендуется - {reason}")
                return 'avoid', 0.0, 0, regime.volatility, regime.trend_strength, indicators.rsi, 0
            
            # Адаптивные параметры на основе режима
            if regime.name == 'sideways':
                mode = 'range'
                spacing_mult = 1.0 + regime.volatility * 5
                grid_levels = max(4, min(8, int(6 + regime.volatility * 2)))
            elif regime.name in ['strong_uptrend', 'strong_downtrend']:
                mode = 'trend'
                spacing_mult = 1.0 + regime.volatility * 8
                grid_levels = max(3, min(6, int(4 + regime.volatility * 2)))
            elif regime.name == 'high_volatility':
                mode = 'volatile'
                spacing_mult = 1.0 + regime.volatility * 12
                grid_levels = max(2, min(4, int(3 + regime.volatility)))
            else:
                mode = 'neutral'
                spacing_mult = 1.0 + regime.volatility * 6
                grid_levels = max(4, min(6, int(5 + regime.volatility)))
            
            # Логирование анализа
            self.logger.info(f"📊 {symbol}: {regime.name} (уверенность: {regime.confidence:.2f}), "
                           f"RSI: {indicators.rsi:.1f}, BB: {indicators.bb_position:.2f}, "
                           f"Vol: {regime.volatility:.3f}, Рекомендация: {regime.recommendation}")
            
            return (mode, spacing_mult, grid_levels, regime.volatility, 
                   regime.trend_strength, indicators.rsi, 0)
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка анализа рынка для {symbol}: {e}")
            return 'neutral', 1.0, 6, 0.01, 0, 50, 0

    def is_spread_acceptable(self, symbol: str) -> bool:
        """Фильтр по спреду"""
        try:
            ticker = self.ex.fetch_ticker(symbol)
            bid = ticker.get('bid')
            ask = ticker.get('ask')
            if bid is None or ask is None or bid == 0:
                return False
            spread_pct = (ask - bid) / bid
            # Спред должен быть меньше 0.1%
            return spread_pct < 0.001
        except Exception as e:
            self.logger.error(f"Ошибка проверки спреда для {symbol}: {e}")
            return False

    async def create_reverse_grid(self, symbol: str):
        """Создание реверсивной сетки (основной метод)"""
        # Cooldown
        current_time = time.time()
        last_update = self.last_grid_updates.get(symbol, 0)
        cooldown_period = 60  # 1 минута
        
        if current_time - last_update < cooldown_period:
            self.logger.debug(f"⏳ {symbol}: Пропущено обновление из-за cooldown")
            return
            
        self.last_grid_updates[symbol] = current_time
        
        try:
            # 1. Проверка глобального стоп-лосса
            if await self.risk_manager.check_global_stop_loss():
                self.logger.critical(f"🚨 {symbol}: Создание сетки заблокировано глобальным стоп-лоссом")
                return
            
            # 2. Проверка фильтров
            if not self.is_spread_acceptable(symbol):
                self.logger.info(f"⚠️ {symbol}: Создание сетки заблокировано фильтром по спреду")
                return
                
            # Получение данных
            balances = await self.get_balances()
            symbol_balance = balances.get(symbol, {'base': 0, 'quote': 0})
            ticker = self.ex.fetch_ticker(symbol)
            current_price = ticker['last']
            allocated_capital_for_symbol = self.allocated_capital.get(symbol, 0)
            
            # 2. Проверка минимального капитала
            if allocated_capital_for_symbol < self.min_order_usd * 2:
                self.logger.info(f"⚠️ {symbol}: Недостаточный выделенный капитал ({allocated_capital_for_symbol:.2f} USDT)")
                return
                
            # 3. Анализ рынка
            ohlcv = self.ex.fetch_ohlcv(symbol, '1m', limit=50)
            mode, spacing_mult, grid_levels, volatility, trend_strength, rsi, cci = await self.analyze_market_regime(symbol, ohlcv)
            
            # Проверка режима торговли
            if mode == 'avoid':
                self.logger.info(f"⚠️ {symbol}: Создание сетки заблокировано анализом рынка")
                return
            
            # 4. Проверка корреляции с существующими парами
            existing_symbols = list(self.asset_grids.keys())
            if existing_symbols:
                ohlcv_data = {symbol: ohlcv}
                for existing_symbol in existing_symbols:
                    try:
                        existing_ohlcv = self.ex.fetch_ohlcv(existing_symbol, '1m', limit=20)
                        ohlcv_data[existing_symbol] = existing_ohlcv
                    except:
                        continue
                
                if not await self.risk_manager.check_correlation_limits(symbol, existing_symbols, ohlcv_data):
                    self.logger.info(f"⚠️ {symbol}: Создание сетки заблокировано корреляционным анализом")
                    return
                
            # 4. Параметры сетки
            adjusted_spacing = self.base_spacing * spacing_mult
            actual_levels = min(grid_levels, self.max_levels)
            
            # 5. Проверка позиционных лимитов
            estimated_position_value = allocated_capital_for_symbol
            if not await self.risk_manager.check_position_limit(symbol, current_price, estimated_position_value / current_price):
                self.logger.warning(f"⚠️ {symbol}: Превышен позиционный лимит")
                return
            
            # 6. Рассчитываем объем на уровень
            total_orders = actual_levels * 2  # BUY и SELL уровни
            capital_per_order = allocated_capital_for_symbol / total_orders if total_orders > 0 else 0
            
            if capital_per_order <= 0:
                self.logger.warning(f"⚠️ {symbol}: Невозможно рассчитать объем ордера")
                return
            
            # 6. Создаем BUY уровни (LONG)
            buy_prices = []
            for i in range(actual_levels):
                price_level = current_price * (1 - adjusted_spacing * (i + 1))
                buy_prices.append(price_level)
                
            # 7. Создаем SELL уровни
            sell_prices = []
            if self.grid_mode == 'spot':
                # Для spot проверяем наличие базового актива
                base_balance = symbol_balance['base']
                
                if base_balance <= 0:
                    self.logger.warning(f"⚠️ {symbol}: Нет базового актива для создания SELL ордеров в spot режиме")
                else:
                    for i in range(actual_levels):
                        price_level = current_price * (1 + adjusted_spacing * (i + 1))
                        sell_prices.append(price_level)
            else:
                # Для futures создаем SELL уровни как обычно
                for i in range(actual_levels):
                    price_level = current_price * (1 + adjusted_spacing * (i + 1))
                    sell_prices.append(price_level)
            
            # 8. Отменяем существующие ордера по этой паре
            if symbol in self.asset_grids:
                await self._cancel_existing_orders(symbol)
                    
            # 9. Создаем новые ордера
            new_orders = {}
            
            # BUY ордера
            for i, buy_price in enumerate(buy_prices):
                try:
                    amount_usd = capital_per_order
                    amount_asset = amount_usd / buy_price
                    
                    # Проверка минимального лота
                    if not await self.check_min_lot(symbol, amount_asset, buy_price):
                        continue
                        
                    order = self.ex.create_limit_buy_order(symbol, amount_asset, buy_price)
                    order_id = order['id']
                    
                    new_orders[order_id] = GridOrder(
                        order_id=order_id,
                        symbol=symbol,
                        type='buy',
                        price=buy_price,
                        amount=amount_asset,
                        level=i+1,
                        mode=mode
                    )
                    
                    self.logger.info(f"📉 {symbol} BUY ордер #{order_id}: {amount_asset:.6f} @ {buy_price:.2f} (${amount_usd:.2f})")
                except ccxt.InsufficientFunds as e:
                    self.logger.warning(f"⚠️ {symbol} Недостаточно средств для BUY ордера на уровне {i+1}: {e}")
                    break
                except Exception as e:
                    self.logger.error(f"❌ Ошибка BUY ордера {symbol} на уровне {i+1}: {e}")
                    
            # SELL ордера
            if not sell_prices:
                self.asset_grids[symbol] = new_orders
                self.logger.info(f"🔧 {symbol} Grid: Buy {len(buy_prices)} | Sell 0")
                return
                
            for i, sell_price in enumerate(sell_prices):
                try:
                    if self.grid_mode == 'spot':
                        # Для spot используем базовый баланс
                        balance = await self.get_balances()
                        symbol_balance = balance.get(symbol, {'base': 0, 'quote': 0})
                        base_balance = symbol_balance['base']
                        amount_per_sell_level = base_balance / len(sell_prices) if len(sell_prices) > 0 else 0
                        
                        if amount_per_sell_level <= 0:
                            continue
                            
                        # Проверка минимального лота
                        if not await self.check_min_lot(symbol, amount_per_sell_level, sell_price):
                            continue
                            
                        order = self.ex.create_limit_sell_order(symbol, amount_per_sell_level, sell_price)
                    else:
                        # Для futures рассчитываем количество как для LONG позиции
                        amount_usd = capital_per_order
                        amount_asset = amount_usd / sell_price
                        
                        # Проверка минимального лота
                        if not await self.check_min_lot(symbol, amount_asset, sell_price):
                            continue
                            
                        order = self.ex.create_limit_sell_order(symbol, amount_asset, sell_price)
                        
                    order_id = order['id']
                    
                    new_orders[order_id] = GridOrder(
                        order_id=order_id,
                        symbol=symbol,
                        type='sell',
                        price=sell_price,
                        amount=amount_per_sell_level if self.grid_mode == 'spot' else amount_asset,
                        level=i+1,
                        mode=mode
                    )
                    
                    self.logger.info(f"📈 {symbol} SELL ордер #{order_id}: {new_orders[order_id].amount:.6f} @ {sell_price:.2f}")
                except ccxt.InsufficientFunds as e:
                    self.logger.warning(f"⚠️ {symbol} Недостаточно средств для SELL ордера на уровне {i+1}: {e}")
                    break
                except Exception as e:
                    self.logger.error(f"❌ Ошибка SELL ордера {symbol} на уровне {i+1}: {e}")
                    
            # Сохраняем информацию о новых ордерах
            self.asset_grids[symbol] = new_orders
            self.logger.info(f"🔧 {symbol} Grid: Buy {len(buy_prices)} | Sell {len(sell_prices)}")
            
        except Exception as e:
            self.logger.error(f"❌ Критическая ошибка создания сетки для {symbol}: {e}")

    async def check_all_orders(self):
        """Проверка исполнения всех ордеров"""
        for symbol in list(self.asset_grids.keys()):
            try:
                open_orders = self.ex.fetch_open_orders(symbol)
                open_order_ids = {order['id'] for order in open_orders}
            except Exception as e:
                self.logger.error(f"Ошибка получения ордеров для {symbol}: {e}")
                continue
                
            executed_orders = []
            current_grid_orders = list(self.asset_grids[symbol].items())
            
            for order_id, order_info in current_grid_orders:
                if order_id not in open_order_ids and order_id not in self.executed_order_ids:
                    # Ордер исполнен
                    executed_orders.append((order_id, order_info))
                    self.executed_order_ids.append(order_id)
                    self.logger.info(f"✅ {symbol}: Исполнен ордер #{order_id} ({order_info.type})")
                    
            # Обработка исполненных ордеров
            for order_id, order_info in executed_orders:
                # Удаляем из активных ордеров
                if order_id in self.asset_grids[symbol]:
                    del self.asset_grids[symbol][order_id]
                    
                # Логирование исполнения ордера
                trade_event = TradeEvent(
                    ts=time.time(),
                    symbol=symbol,
                    side=order_info.type,
                    price=order_info.price,
                    qty=order_info.amount
                )
                await self.log_trade(trade_event)
                
                # Добавляем позицию в риск-менеджер
                try:
                    current_price = order_info.price  # Используем цену исполнения
                    side = 'long' if order_info.type == 'buy' else 'short'
                    await self.risk_manager.add_position(
                        symbol=symbol,
                        side=side,
                        entry_price=order_info.price,
                        quantity=order_info.amount,
                        current_price=current_price,
                        ohlcv=[]  # OHLCV будет получен позже
                    )
                except Exception as e:
                    self.logger.error(f"❌ Ошибка добавления позиции в риск-менеджер: {e}")
                
                # Создаем встречный ордер
                try:
                    if order_info.type == 'buy':
                        # Создаем SELL ордер (Take Profit)
                        tp_price = order_info.price * (1 + self.base_spacing)
                        tp_amount = order_info.amount
                        
                        # Проверка минимального лота
                        if await self.check_min_lot(symbol, tp_amount, tp_price):
                            tp_order = self.ex.create_limit_sell_order(symbol, tp_amount, tp_price)
                            tp_order_id = tp_order['id']
                            
                            self.asset_grids[symbol][tp_order_id] = GridOrder(
                                order_id=tp_order_id,
                                symbol=symbol,
                                type='sell',
                                price=tp_price,
                                amount=tp_amount,
                                level=order_info.level,
                                mode=order_info.mode
                            )
                            
                            self.logger.info(f"🎯 {symbol} TP SELL ордер #{tp_order_id}: {tp_amount:.6f} @ {tp_price:.2f}")
                            
                    elif order_info.type == 'sell':
                        # Создаем BUY ордер (Take Profit)
                        tp_price = order_info.price * (1 - self.base_spacing)
                        tp_amount = order_info.amount
                        
                        # Проверка минимального лота
                        if await self.check_min_lot(symbol, tp_amount, tp_price):
                            tp_order = self.ex.create_limit_buy_order(symbol, tp_amount, tp_price)
                            tp_order_id = tp_order['id']
                            
                            self.asset_grids[symbol][tp_order_id] = GridOrder(
                                order_id=tp_order_id,
                                symbol=symbol,
                                type='buy',
                                price=tp_price,
                                amount=tp_amount,
                                level=order_info.level,
                                mode=order_info.mode
                            )
                            
                            self.logger.info(f"🎯 {symbol} TP BUY ордер #{tp_order_id}: {tp_amount:.6f} @ {tp_price:.2f}")
                            
                except Exception as e:
                    self.logger.error(f"❌ Ошибка создания встречного ордера для {symbol}: {e}")

    async def _cancel_existing_orders(self, symbol: str):
        """Отмена существующих ордеров"""
        try:
            for order_id, order_info in self.asset_grids[symbol].items():
                try:
                    self.ex.cancel_order(order_id, symbol)
                    self.logger.info(f"❌ {symbol}: Отменён ордер #{order_id}")
                except Exception as e:
                    self.logger.debug(f"Ошибка отмены ордера {order_id}: {e}")
            
            self.asset_grids[symbol] = {}
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка отмены ордеров для {symbol}: {e}")

    async def close_all_positions(self):
        """Закрытие всех позиций и отмена ордеров"""
        self.logger.info("🚪 Начало закрытия всех позиций Grid-бота...")
        
        # Отмена всех открытых ордеров
        for symbol in list(self.asset_grids.keys()):
            await self._cancel_existing_orders(symbol)
        
        # Закрытие позиций (для futures)
        if self.grid_mode == 'futures':
            try:
                positions = self.ex.fetch_positions()
                for position in positions:
                    symbol = position['symbol']
                    side = position['side']
                    amount = position['contracts']
                    
                    if amount > 0:
                        close_side = 'sell' if side == 'long' else 'buy'
                        try:
                            if close_side == 'sell':
                                self.ex.create_market_sell_order(symbol, amount)
                            else:
                                self.ex.create_market_buy_order(symbol, amount)
                            self.logger.info(f"🚪 {symbol}: Закрыта позиция {side} {amount}")
                        except Exception as e:
                            self.logger.error(f"Ошибка закрытия позиции {symbol} {side}: {e}")
            except Exception as e:
                self.logger.error(f"Ошибка получения позиций для закрытия: {e}")
        else:
            self.logger.info("📭 Spot режим: ордера отменены")
            
        self.logger.info("✅ Закрытие всех позиций Grid-бота завершено.")

    async def execute_strategy(self):
        """Реализация торговой стратегии для Grid-бота с риск-менеджментом"""
        try:
            # 1. Проверка глобального стоп-лосса
            if await self.risk_manager.check_global_stop_loss():
                self.logger.critical("🚨 ГЛОБАЛЬНЫЙ СТОП-ЛОСС! Остановка торговли")
                await self.close_all_positions()
                return
            
            # 2. Проверка стоп-лоссов по позициям
            triggered_stops = await self.risk_manager.check_stop_losses()
            for symbol in triggered_stops:
                self.logger.warning(f"🛑 Стоп-лосс сработал для {symbol}")
                # Закрываем позицию
                await self.risk_manager.remove_position(symbol)
                # Отменяем все ордера по этой паре
                if symbol in self.asset_grids:
                    await self._cancel_existing_orders(symbol)
            
            # 3. Обновление трейлинг стопов
            for symbol in self.asset_grids.keys():
                try:
                    ticker = self.ex.fetch_ticker(symbol)
                    current_price = ticker['last']
                    await self.risk_manager.update_trailing_stops(symbol, current_price)
                except Exception as e:
                    self.logger.error(f"❌ Ошибка обновления трейлинг стопа для {symbol}: {e}")
            
            # 4. Распределяем капитал
            await self.distribute_capital()
            
            # 5. Обновляем плавающий профит
            await self.update_floating_profits()
            
            # 6. Проверяем исполнение ордеров
            await self.check_all_orders()
            
            # 7. Создаем/обновляем сетки для активов
            for symbol in self.symbols:
                await self.create_reverse_grid(symbol)
                
        except Exception as e:
            self.logger.error(f"❌ Критическая ошибка в execute_strategy: {e}")

    async def distribute_capital(self):
        """Адаптивное распределение капитала с анализом пар и плавающим профитом"""
        self.logger.info("🔄 Начало адаптивного распределения капитала...")
        self.logger.info(f"📊 Текущие символы для анализа: {self.symbols}")
        
        try:
            if self.adaptive_capital_distributor:
                # 1. Анализируем торговые пары
                self.logger.info(f"📊 Анализируем {len(self.symbols)} торговых пар...")
                pair_analyses = await self.adaptive_capital_distributor.analyze_trading_pairs(self.symbols)
                self.pair_analyses = {analysis.symbol: analysis for analysis in pair_analyses}
                
                # 2. Выбираем оптимальные пары для текущего режима
                total_capital = await self.adaptive_capital_distributor.get_total_capital()
                selected_pairs = await self.adaptive_capital_distributor.select_optimal_pairs(
                    pair_analyses, self.current_trading_mode, total_capital
                )
                
                # 3. Адаптивно распределяем капитал
                allocations = await self.adaptive_capital_distributor.distribute_capital_adaptively(
                    self.current_trading_mode, selected_pairs
                )
                
                # 4. Обновляем символы для торговли
                self.symbols = [pair.symbol for pair in selected_pairs]
                
                # 5. Конвертируем в формат для бота
                self.allocated_capital = {
                    allocation.symbol: allocation.allocated_amount 
                    for allocation in allocations.values()
                }
                
                self.logger.info(f"🎯 Выбрано {len(selected_pairs)} пар для режима {self.current_trading_mode.value}")
                self.logger.info(f"💰 Адаптивные аллокации: {self.allocated_capital}")
                
            elif self.capital_distributor:
                # Fallback к умному распределению
                self.logger.info(f"📊 Используем CapitalDistributor для {len(self.symbols)} символов")
                allocations = await self.capital_distributor.smart_distribute_for_strategy('grid', self.symbols)
                self.allocated_capital = allocations
                self.logger.info(f"💰 Получены аллокации: {allocations}")
            else:
                # Fallback к базовому распределению
                self.logger.info("📊 Используем базовое распределение капитала")
                allocations = await super().distribute_capital()
                self.allocated_capital = allocations
                self.logger.info(f"💰 Базовые аллокации: {allocations}")
            
            # Логирование распределения
            for symbol, amount in self.allocated_capital.items():
                self.logger.info(f"💰 {symbol}: выделено ${amount:.2f} USDT")
                
            self.logger.info("✅ Адаптивное распределение капитала завершено.")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка адаптивного распределения капитала: {e}")
            # Fallback к базовому распределению
            try:
                allocations = await super().distribute_capital()
                self.allocated_capital = allocations
                self.logger.info(f"💰 Fallback аллокации: {allocations}")
            except Exception as fallback_error:
                self.logger.error(f"❌ Критическая ошибка fallback распределения: {fallback_error}")
                self.allocated_capital = {}

    async def update_floating_profits(self):
        """Обновление плавающего профита для всех активных пар"""
        try:
            if not self.adaptive_capital_distributor:
                return
                
            for symbol in self.symbols:
                try:
                    # Получаем текущую цену
                    ticker = self.ex.fetch_ticker(symbol)
                    current_price = ticker['last']
                    
                    # Получаем аллокацию для пары
                    if symbol in self.allocated_capital:
                        # Создаем временную аллокацию для расчета
                        from src.trading.adaptive_capital_distributor import CapitalAllocation
                        temp_allocation = CapitalAllocation(
                            symbol=symbol,
                            allocated_amount=self.allocated_capital[symbol],
                            min_amount=200.0,
                            max_amount=self.allocated_capital[symbol] * 2.0,
                            risk_level='medium',
                            profit_target=self.allocated_capital[symbol] * 0.1,
                            stop_loss=self.allocated_capital[symbol] * 0.05,
                            trailing_stop=True,
                            position_size=0.0
                        )
                        
                        # Обновляем плавающий профит
                        profit_info = await self.adaptive_capital_distributor.update_floating_profit(
                            symbol, current_price, temp_allocation
                        )
                        
                        # Сохраняем информацию о профите
                        self.floating_profit_tracking[symbol] = profit_info
                        
                        # Логируем значимые изменения
                        if profit_info.get('current_profit', 0) > 50:
                            self.logger.info(f"💰 {symbol}: Плавающий профит ${profit_info.get('current_profit', 0):.2f} "
                                           f"({profit_info.get('profit_pct', 0):.1f}%)")
                            
                except Exception as e:
                    self.logger.error(f"❌ Ошибка обновления плавающего профита для {symbol}: {e}")
                    
        except Exception as e:
            self.logger.error(f"❌ Ошибка обновления плавающих профитов: {e}")

    async def get_grid_status(self) -> Dict:
        """Получение статуса Grid сеток"""
        try:
            status = {
                'active_grids': len(self.asset_grids),
                'total_orders': sum(len(orders) for orders in self.asset_grids.values()),
                'executed_orders': len(self.executed_order_ids),
                'current_mode': self.current_mode,
                'mode_switches': self.mode_switch_count,
                'symbols': {}
            }
            
            for symbol, orders in self.asset_grids.items():
                buy_orders = [o for o in orders.values() if o.type == 'buy']
                sell_orders = [o for o in orders.values() if o.type == 'sell']
                
                status['symbols'][symbol] = {
                    'buy_orders': len(buy_orders),
                    'sell_orders': len(sell_orders),
                    'total_orders': len(orders),
                    'allocated_capital': self.allocated_capital.get(symbol, 0)
                }
            
            return status
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения статуса Grid: {e}")
            return {}

    async def get_adaptive_summary(self) -> Dict:
        """Получение сводки адаптивного бота"""
        try:
            base_summary = {
                'current_mode': self.current_mode,
                'mode_switches': self.mode_switch_count,
                'last_mode_switch': self.last_mode_switch,
                'active_grids': len(self.asset_grids),
                'total_orders': sum(len(orders) for orders in self.asset_grids.values()),
                'executed_orders': len(self.executed_order_ids),
                'grid_status': await self.get_grid_status()
            }
            
            return base_summary
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения сводки: {e}")
            return {}
    
    async def get_risk_summary(self) -> Dict:
        """Получение сводки по рискам"""
        try:
            if self.risk_manager:
                return self.risk_manager.get_risk_summary()
            else:
                return {}
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения сводки рисков: {e}")
            return {}
    
    async def get_enhanced_summary(self) -> Dict:
        """Получение расширенной сводки с рисками и адаптивной системой"""
        try:
            base_summary = await self.get_adaptive_summary()
            risk_summary = await self.get_risk_summary()
            
            # Получаем сводку адаптивной системы
            adaptive_summary = {}
            if self.adaptive_capital_distributor:
                adaptive_summary = await self.adaptive_capital_distributor.get_allocation_summary()
            
            # Объединяем сводки
            enhanced_summary = {
                **base_summary,
                'risk_management': risk_summary,
                'adaptive_system': {
                    'current_mode': self.current_trading_mode.value,
                    'pair_analyses': len(self.pair_analyses),
                    'floating_profits': self.floating_profit_tracking,
                    'allocation_summary': adaptive_summary
                },
                'version': 'v5.0',
                'features': [
                    'adaptive_capital_distribution',
                    'floating_profit_tracking',
                    '3_mode_risk_management',
                    'dynamic_pair_selection',
                    'correlation_analysis',
                    'stop_losses',
                    'trend_analysis',
                    'position_risk_management',
                    'macd_indicators',
                    'bollinger_bands',
                    'volume_analysis'
                ]
            }
            
            return enhanced_summary
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения расширенной сводки: {e}")
            return {}


