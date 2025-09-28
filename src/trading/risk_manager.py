# v1.0 (+стоп-лоссы, риск-менеджмент, мониторинг)
"""
Модуль для управления рисками в торговых ботах.
v1.0: Глобальные и динамические стоп-лоссы, позиционный риск-менеджмент.
"""
import asyncio
import time
import logging
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class RiskLimits:
    """Лимиты риска для бота"""
    max_drawdown_pct: float = 15.0  # Максимальная просадка в %
    max_position_pct: float = 30.0  # Максимальная позиция на пару в % (увеличено для demo)
    max_correlation: float = 0.7    # Максимальная корреляция между парами
    stop_loss_pct: float = 2.0      # Стоп-лосс в % от цены входа
    trailing_stop_pct: float = 1.5  # Трейлинг стоп в %
    atr_multiplier: float = 2.0     # Множитель ATR для динамического стоп-лосса

@dataclass
class PositionInfo:
    """Информация о позиции"""
    symbol: str
    side: str  # 'long' или 'short'
    entry_price: float
    quantity: float
    current_price: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    stop_loss_price: float
    trailing_stop_price: float
    created_at: float

class RiskManager:
    """
    Менеджер рисков для торговых ботов с 3-режимной системой просадки.
    Управляет стоп-лоссами, позиционными лимитами и корреляционным анализом.
    """
    
    def __init__(self, user_id: int, limits: RiskLimits = None, risk_mode: str = "automatic"):
        """
        Инициализация Risk Manager
        
        Args:
            user_id: ID пользователя
            limits: Лимиты риска
            risk_mode: Режим риска ('conservative', 'aggressive', 'automatic')
        """
        self.user_id = user_id
        self.limits = limits or RiskLimits()
        self.logger = logging.getLogger(f"risk_manager_{user_id}")
        
        # 3-режимная система просадки
        self.risk_modes = {
            'conservative': {
                'max_drawdown_pct': 5.0,      # 5% максимальная просадка
                'stop_loss_pct': 2.0,         # 2% стоп-лосс на сделку
                'max_position_pct': 15.0,     # 15% от капитала на позицию
                'max_correlation': 0.5,       # Максимальная корреляция 0.5
                'min_capital_per_pair': 400.0, # Минимум $400 на пару
                'max_pairs': 1,               # Максимум 1 пара
                'volatility_range': (2.0, 4.0) # Волатильность 2-4%
            },
            'aggressive': {
                'max_drawdown_pct': 8.0,      # 8% максимальная просадка
                'stop_loss_pct': 3.0,         # 3% стоп-лосс на сделку
                'max_position_pct': 8.0,      # 8% от капитала на позицию
                'max_correlation': 0.7,       # Максимальная корреляция 0.7
                'min_capital_per_pair': 200.0, # Минимум $200 на пару
                'max_pairs': 3,               # Максимум 3 пары
                'volatility_range': (4.0, 8.0) # Волатильность 4-8%
            },
            'automatic': {
                'max_drawdown_pct': 6.0,      # 6% максимальная просадка
                'stop_loss_pct': 2.5,         # 2.5% стоп-лосс на сделку
                'max_position_pct': 10.0,     # 10% от капитала на позицию
                'max_correlation': 0.6,       # Максимальная корреляция 0.6
                'min_capital_per_pair': 200.0, # Минимум $200 на пару
                'max_pairs': 5,               # Максимум 5 пар
                'volatility_range': (3.0, 6.0) # Волатильность 3-6%
            }
        }
        
        # Текущий режим риска
        self.current_mode = risk_mode
        self.mode_config = self.risk_modes[self.current_mode]
        
        # Обновляем лимиты из режима
        self.limits.max_drawdown_pct = self.mode_config['max_drawdown_pct']
        self.limits.stop_loss_pct = self.mode_config['stop_loss_pct']
        self.limits.max_position_pct = self.mode_config['max_position_pct']
        self.limits.max_correlation = self.mode_config['max_correlation']
        
        # Состояние рисков
        self.positions: Dict[str, PositionInfo] = {}
        self.global_stop_loss_triggered = False
        self.last_balance_check = 0
        self.initial_balance = 0.0
        self.current_balance = 0.0
        
        # Статистика
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.max_drawdown = 0.0
        self.current_drawdown = 0.0
        
        # Адаптивные пороги
        self._adaptive_thresholds = {
            'balance_400_800': {'pairs': 1, 'min_capital': 400},
            'balance_800_1500': {'pairs': 2, 'min_capital': 200},
            'balance_1500_3000': {'pairs': 3, 'min_capital': 200},
            'balance_3000_plus': {'pairs': 4, 'min_capital': 200}
        }
        
    async def initialize(self, exchange, initial_balance: float):
        """
        Инициализация с биржей и начальным балансом
        
        Args:
            exchange: Экземпляр биржи
            initial_balance: Начальный баланс
        """
        self.ex = exchange
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.last_balance_check = time.time()
        
        self.logger.info(f"🛡️ Risk Manager инициализирован. Начальный баланс: ${initial_balance:.2f}")
    
    def set_exchange(self, exchange, initial_balance: float):
        """
        Синхронная инициализация Risk Manager с биржей
        
        Args:
            exchange: Экземпляр биржи
            initial_balance: Начальный баланс
        """
        self.ex = exchange
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.last_balance_check = time.time()
        
        self.logger.info(f"🛡️ Risk Manager инициализирован. Начальный баланс: ${initial_balance:.2f}")
        
    async def check_global_stop_loss(self) -> bool:
        """
        Проверка глобального стоп-лосса
        
        Returns:
            bool: True если стоп-лосс сработал
        """
        try:
            # Обновляем баланс каждые 30 секунд
            if time.time() - self.last_balance_check > 30:
                self.update_balance()
                self.last_balance_check = time.time()
            
            # Рассчитываем текущую просадку
            if self.initial_balance > 0:
                self.current_drawdown = (self.initial_balance - self.current_balance) / self.initial_balance * 100
                
                # Обновляем максимальную просадку
                if self.current_drawdown > self.max_drawdown:
                    self.max_drawdown = self.current_drawdown
                
                # Проверяем глобальный стоп-лосс
                if self.current_drawdown >= self.limits.max_drawdown_pct:
                    if not self.global_stop_loss_triggered:
                        self.global_stop_loss_triggered = True
                        self.logger.critical(f"🚨 ГЛОБАЛЬНЫЙ СТОП-ЛОСС! Просадка: {self.current_drawdown:.2f}% >= {self.limits.max_drawdown_pct}%")
                        return True
                        
            return self.global_stop_loss_triggered
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка проверки глобального стоп-лосса: {e}")
            return False
    
    def update_balance(self):
        """Обновление текущего баланса"""
        try:
            if not self.ex:
                return
                
            balance = self.ex.fetch_balance({'type': 'spot'})
            if 'total' in balance and 'USDT' in balance['total']:
                self.current_balance = float(balance['total']['USDT'])
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка обновления баланса: {e}")
    
    async def calculate_atr_stop_loss(self, symbol: str, ohlcv: List, side: str, entry_price: float) -> float:
        """
        Расчет динамического стоп-лосса на основе ATR
        
        Args:
            symbol: Торговая пара
            ohlcv: Данные OHLCV
            side: 'long' или 'short'
            entry_price: Цена входа
            
        Returns:
            float: Цена стоп-лосса
        """
        try:
            if len(ohlcv) < 14:
                # Fallback к простому стоп-лоссу
                if side == 'long':
                    return entry_price * (1 - self.limits.stop_loss_pct / 100)
                else:
                    return entry_price * (1 + self.limits.stop_loss_pct / 100)
            
            # Расчет ATR
            highs = np.array([candle[2] for candle in ohlcv])
            lows = np.array([candle[3] for candle in ohlcv])
            closes = np.array([candle[4] for candle in ohlcv])
            
            atr_values = []
            for i in range(1, len(ohlcv)):
                tr = max(
                    highs[i] - lows[i],
                    abs(highs[i] - closes[i-1]),
                    abs(lows[i] - closes[i-1])
                )
                atr_values.append(tr)
            
            atr = np.mean(atr_values) if atr_values else entry_price * 0.02
            
            # Расчет стоп-лосса
            atr_stop_distance = atr * self.limits.atr_multiplier
            
            if side == 'long':
                return entry_price - atr_stop_distance
            else:
                return entry_price + atr_stop_distance
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка расчета ATR стоп-лосса для {symbol}: {e}")
            # Fallback к простому стоп-лоссу
            if side == 'long':
                return entry_price * (1 - self.limits.stop_loss_pct / 100)
            else:
                return entry_price * (1 + self.limits.stop_loss_pct / 100)
    
    async def add_position(self, symbol: str, side: str, entry_price: float, quantity: float, 
                          current_price: float, ohlcv: List = None) -> bool:
        """
        Добавление позиции с автоматическим расчетом стоп-лосса
        
        Args:
            symbol: Торговая пара
            side: 'long' или 'short'
            entry_price: Цена входа
            quantity: Количество
            current_price: Текущая цена
            ohlcv: Данные OHLCV для расчета ATR
            
        Returns:
            bool: True если позиция добавлена успешно
        """
        try:
            # Проверяем лимит позиции
            if not await self.check_position_limit(symbol, entry_price, quantity):
                return False
            
            # Рассчитываем стоп-лосс
            if ohlcv:
                stop_loss_price = await self.calculate_atr_stop_loss(symbol, ohlcv, side, entry_price)
            else:
                # Простой стоп-лосс
                if side == 'long':
                    stop_loss_price = entry_price * (1 - self.limits.stop_loss_pct / 100)
                else:
                    stop_loss_price = entry_price * (1 + self.limits.stop_loss_pct / 100)
            
            # Создаем информацию о позиции
            position = PositionInfo(
                symbol=symbol,
                side=side,
                entry_price=entry_price,
                quantity=quantity,
                current_price=current_price,
                unrealized_pnl=0.0,
                unrealized_pnl_pct=0.0,
                stop_loss_price=stop_loss_price,
                trailing_stop_price=stop_loss_price,
                created_at=time.time()
            )
            
            # Обновляем PnL
            await self.update_position_pnl(position)
            
            # Добавляем позицию
            self.positions[symbol] = position
            
            self.logger.info(f"📊 Позиция добавлена: {symbol} {side} @ {entry_price:.4f}, SL: {stop_loss_price:.4f}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка добавления позиции {symbol}: {e}")
            return False
    
    async def update_position_pnl(self, position: PositionInfo):
        """Обновление PnL позиции"""
        try:
            if position.side == 'long':
                position.unrealized_pnl = (position.current_price - position.entry_price) * position.quantity
            else:
                position.unrealized_pnl = (position.entry_price - position.current_price) * position.quantity
            
            position.unrealized_pnl_pct = (position.unrealized_pnl / (position.entry_price * position.quantity)) * 100
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка обновления PnL для {position.symbol}: {e}")
    
    async def check_position_limit(self, symbol: str, price: float, quantity: float) -> bool:
        """
        Проверка лимита позиции на пару
        
        Args:
            symbol: Торговая пара
            price: Цена
            quantity: Количество
            
        Returns:
            bool: True если лимит не превышен
        """
        try:
            # Рассчитываем стоимость позиции
            position_value = price * quantity
            
            # Проверяем лимит на пару
            if position_value > self.current_balance * (self.limits.max_position_pct / 100):
                self.logger.warning(f"⚠️ {symbol}: Превышен лимит позиции. Стоимость: ${position_value:.2f}, Лимит: ${self.current_balance * (self.limits.max_position_pct / 100):.2f}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка проверки лимита позиции для {symbol}: {e}")
            return False
    
    async def check_stop_losses(self) -> List[str]:
        """
        Проверка всех стоп-лоссов
        
        Returns:
            List[str]: Список символов, по которым сработал стоп-лосс
        """
        triggered = []
        
        try:
            for symbol, position in self.positions.items():
                # Обновляем PnL
                await self.update_position_pnl(position)
                
                # Проверяем стоп-лосс
                stop_triggered = False
                
                if position.side == 'long':
                    if position.current_price <= position.stop_loss_price:
                        stop_triggered = True
                else:
                    if position.current_price >= position.stop_loss_price:
                        stop_triggered = True
                
                if stop_triggered:
                    triggered.append(symbol)
                    self.logger.warning(f"🛑 Стоп-лосс сработал для {symbol}: {position.side} @ {position.current_price:.4f} <= {position.stop_loss_price:.4f}")
                    
                    # Обновляем статистику
                    if position.unrealized_pnl > 0:
                        self.winning_trades += 1
                    else:
                        self.losing_trades += 1
                    self.total_trades += 1
                    
        except Exception as e:
            self.logger.error(f"❌ Ошибка проверки стоп-лоссов: {e}")
        
        return triggered
    
    async def update_trailing_stops(self, symbol: str, current_price: float):
        """
        Обновление трейлинг стопов
        
        Args:
            symbol: Торговая пара
            current_price: Текущая цена
        """
        try:
            if symbol not in self.positions:
                return
                
            position = self.positions[symbol]
            position.current_price = current_price
            
            # Обновляем PnL
            await self.update_position_pnl(position)
            
            # Обновляем трейлинг стоп
            if position.side == 'long':
                # Для лонга: поднимаем стоп-лосс при росте цены
                new_trailing_stop = current_price * (1 - self.limits.trailing_stop_pct / 100)
                if new_trailing_stop > position.trailing_stop_price:
                    position.trailing_stop_price = new_trailing_stop
                    position.stop_loss_price = new_trailing_stop
                    self.logger.info(f"📈 {symbol}: Трейлинг стоп обновлен до {new_trailing_stop:.4f}")
            else:
                # Для шорта: опускаем стоп-лосс при падении цены
                new_trailing_stop = current_price * (1 + self.limits.trailing_stop_pct / 100)
                if new_trailing_stop < position.trailing_stop_price:
                    position.trailing_stop_price = new_trailing_stop
                    position.stop_loss_price = new_trailing_stop
                    self.logger.info(f"📉 {symbol}: Трейлинг стоп обновлен до {new_trailing_stop:.4f}")
                    
        except Exception as e:
            self.logger.error(f"❌ Ошибка обновления трейлинг стопа для {symbol}: {e}")
    
    async def remove_position(self, symbol: str):
        """Удаление позиции"""
        try:
            if symbol in self.positions:
                position = self.positions[symbol]
                self.logger.info(f"🗑️ Позиция удалена: {symbol} {position.side}, PnL: {position.unrealized_pnl:.2f} ({position.unrealized_pnl_pct:.2f}%)")
                del self.positions[symbol]
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка удаления позиции {symbol}: {e}")
    
    async def calculate_correlation(self, symbol1: str, symbol2: str, ohlcv1: List, ohlcv2: List) -> float:
        """
        Расчет корреляции между двумя парами
        
        Args:
            symbol1: Первая пара
            symbol2: Вторая пара
            ohlcv1: Данные первой пары
            ohlcv2: Данные второй пары
            
        Returns:
            float: Коэффициент корреляции (-1 до 1)
        """
        try:
            if len(ohlcv1) < 20 or len(ohlcv2) < 20:
                return 0.0
            
            # Берем последние 20 свечей
            closes1 = np.array([candle[4] for candle in ohlcv1[-20:]])
            closes2 = np.array([candle[4] for candle in ohlcv2[-20:]])
            
            # Рассчитываем процентные изменения
            returns1 = np.diff(closes1) / closes1[:-1]
            returns2 = np.diff(closes2) / closes2[:-1]
            
            # Корреляция
            correlation = np.corrcoef(returns1, returns2)[0, 1]
            
            return correlation if not np.isnan(correlation) else 0.0
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка расчета корреляции {symbol1}-{symbol2}: {e}")
            return 0.0
    
    async def check_correlation_limits(self, new_symbol: str, existing_symbols: List[str], 
                                     ohlcv_data: Dict[str, List]) -> bool:
        """
        Проверка лимитов корреляции
        
        Args:
            new_symbol: Новая пара
            existing_symbols: Существующие пары
            ohlcv_data: Данные OHLCV для всех пар
            
        Returns:
            bool: True если лимиты не превышены
        """
        try:
            if new_symbol not in ohlcv_data:
                return True
                
            new_ohlcv = ohlcv_data[new_symbol]
            
            for existing_symbol in existing_symbols:
                if existing_symbol in ohlcv_data:
                    correlation = await self.calculate_correlation(
                        new_symbol, existing_symbol, 
                        new_ohlcv, ohlcv_data[existing_symbol]
                    )
                    
                    if abs(correlation) > self.limits.max_correlation:
                        self.logger.warning(f"⚠️ Высокая корреляция {new_symbol}-{existing_symbol}: {correlation:.3f} > {self.limits.max_correlation}")
                        return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка проверки корреляции для {new_symbol}: {e}")
            return True
    
    def get_risk_summary(self) -> Dict[str, Any]:
        """Получение сводки по рискам"""
        try:
            total_unrealized_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())
            total_unrealized_pnl_pct = (total_unrealized_pnl / self.initial_balance * 100) if self.initial_balance > 0 else 0
            
            win_rate = (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0
            
            return {
                'global_stop_loss_triggered': self.global_stop_loss_triggered,
                'current_drawdown': self.current_drawdown,
                'max_drawdown': self.max_drawdown,
                'total_positions': len(self.positions),
                'total_unrealized_pnl': total_unrealized_pnl,
                'total_unrealized_pnl_pct': total_unrealized_pnl_pct,
                'total_trades': self.total_trades,
                'winning_trades': self.winning_trades,
                'losing_trades': self.losing_trades,
                'win_rate': win_rate,
                'current_mode': self.current_mode,
                'mode_config': self.mode_config,
                'positions': {
                    symbol: {
                        'side': pos.side,
                        'entry_price': pos.entry_price,
                        'current_price': pos.current_price,
                        'unrealized_pnl': pos.unrealized_pnl,
                        'unrealized_pnl_pct': pos.unrealized_pnl_pct,
                        'stop_loss_price': pos.stop_loss_price,
                        'trailing_stop_price': pos.trailing_stop_price
                    }
                    for symbol, pos in self.positions.items()
                }
            }
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения сводки рисков: {e}")
            return {}

    def set_risk_mode(self, mode: str):
        """Установка режима риска"""
        if mode in self.risk_modes:
            self.current_mode = mode
            self.mode_config = self.risk_modes[mode]
            
            # Обновляем лимиты
            self.limits.max_drawdown_pct = self.mode_config['max_drawdown_pct']
            self.limits.stop_loss_pct = self.mode_config['stop_loss_pct']
            self.limits.max_position_pct = self.mode_config['max_position_pct']
            self.limits.max_correlation = self.mode_config['max_correlation']
            
            self.logger.info(f"🔄 Режим риска изменен на: {mode}")
        else:
            self.logger.error(f"❌ Неизвестный режим риска: {mode}")

    def get_recommended_mode(self, total_capital: float) -> str:
        """Рекомендация режима на основе капитала"""
        if total_capital < 800:
            return 'conservative'
        elif total_capital < 2000:
            return 'automatic'
        else:
            return 'aggressive'

    def get_adaptive_pair_count(self, total_capital: float) -> int:
        """Адаптивное количество пар на основе капитала"""
        if total_capital < 400:
            return 1
        elif total_capital < 800:
            return 1
        elif total_capital < 1500:
            return 2
        elif total_capital < 3000:
            return 3
        else:
            return 4

    def get_min_capital_per_pair(self, total_capital: float) -> float:
        """Минимальный капитал на пару на основе баланса"""
        if total_capital < 800:
            return 400.0
        else:
            return 200.0

    def check_volatility_range(self, volatility: float) -> bool:
        """Проверка волатильности в допустимом диапазоне"""
        vol_min, vol_max = self.mode_config['volatility_range']
        return vol_min <= volatility <= vol_max

    def check_correlation_limit(self, correlation: float) -> bool:
        """Проверка лимита корреляции"""
        return abs(correlation) <= self.mode_config['max_correlation']

    def get_mode_limits(self) -> Dict[str, Any]:
        """Получение лимитов текущего режима"""
        return self.mode_config.copy()

    def should_expand_pairs(self, current_pairs: int, total_capital: float, 
                          profit_threshold: float = 200.0) -> bool:
        """Проверка необходимости расширения количества пар"""
        try:
            # Проверяем прибыль
            if profit_threshold > 0:
                total_profit = sum(pos.unrealized_pnl for pos in self.positions.values())
                if total_profit < profit_threshold:
                    return False
            
            # Проверяем капитал
            recommended_pairs = self.get_adaptive_pair_count(total_capital)
            if current_pairs >= recommended_pairs:
                return False
            
            # Проверяем лимит режима
            if current_pairs >= self.mode_config['max_pairs']:
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка проверки расширения пар: {e}")
            return False

    def get_expansion_recommendation(self, total_capital: float, 
                                   current_pairs: int) -> Dict[str, Any]:
        """Рекомендация по расширению торговли"""
        try:
            recommended_pairs = self.get_adaptive_pair_count(total_capital)
            min_capital = self.get_min_capital_per_pair(total_capital)
            
            can_expand = (
                current_pairs < recommended_pairs and
                current_pairs < self.mode_config['max_pairs'] and
                total_capital >= min_capital * (current_pairs + 1)
            )
            
            return {
                'can_expand': can_expand,
                'recommended_pairs': recommended_pairs,
                'current_pairs': current_pairs,
                'min_capital_per_pair': min_capital,
                'required_capital': min_capital * (current_pairs + 1),
                'available_capital': total_capital
            }
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения рекомендации расширения: {e}")
            return {'can_expand': False}
