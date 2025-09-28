#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Adaptive Capital Distributor - адаптивная система распределения капитала
с интеграцией управления рисками и плавающим профитом
"""

import asyncio
import time
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from src.core.log_helper import build_logger

class TradingMode(Enum):
    """Режимы торговли"""
    CONSERVATIVE = "conservative"  # 1 пара, $400+ на пару, просадка до 5%
    AGGRESSIVE = "aggressive"     # 2-3 пары, $200+ на пару, просадка до 8%
    AUTOMATIC = "automatic"       # Бот выбирает на основе капитала

@dataclass
class PairAnalysis:
    """Анализ торговой пары"""
    symbol: str
    volatility: float  # 3-6% в день
    liquidity: float   # >$5M в день
    trend: float       # Боковые рынки с легким трендом
    correlation: float # <0.5 с другими парами
    atr: float         # Average True Range
    rsi: float         # RSI индикатор
    volume: float      # Объем торгов
    risk_score: float  # Общий риск (0-1)
    profit_potential: float  # Потенциал прибыли (0-1)

@dataclass
class CapitalAllocation:
    """Распределение капитала"""
    symbol: str
    allocated_amount: float
    min_amount: float
    max_amount: float
    risk_level: str
    profit_target: float
    stop_loss: float
    trailing_stop: bool
    position_size: float

class AdaptiveCapitalDistributor:
    """Адаптивный распределитель капитала с плавающим профитом"""
    
    def __init__(self, exchange, user_id: int, config: Dict[str, Any]):
        self.ex = exchange
        self.user_id = user_id
        self.config = config
        self.logger = build_logger(f"adaptive_capital_distributor_{user_id}")
        
        # Настройки режимов торговли
        self.trading_modes = {
            TradingMode.CONSERVATIVE: {
                'min_pairs': 1,
                'max_pairs': 1,
                'min_capital_per_pair': 400.0,
                'max_drawdown_pct': 5.0,
                'volatility_range': (2.0, 4.0),
                'correlation_limit': 0.5
            },
            TradingMode.AGGRESSIVE: {
                'min_pairs': 2,
                'max_pairs': 3,
                'min_capital_per_pair': 200.0,
                'max_drawdown_pct': 8.0,
                'volatility_range': (4.0, 8.0),
                'correlation_limit': 0.7
            },
            TradingMode.AUTOMATIC: {
                'min_pairs': 1,
                'max_pairs': 5,
                'min_capital_per_pair': 200.0,
                'max_drawdown_pct': 6.0,
                'volatility_range': (1.0, 10.0),  # Более широкий диапазон
                'correlation_limit': 0.8  # Более мягкий лимит
            }
        }
        
        # Настройки плавающего профита
        self.floating_profit_config = {
            'min_profit_for_trailing': 50.0,  # Минимальная прибыль для активации трейлинга
            'trailing_stop_pct': 0.02,        # 2% трейлинг стоп
            'partial_close_pct': 0.5,         # Закрывать 50% при достижении цели
            'profit_target_pct': 0.1,         # 10% цель прибыли
            'reinvestment_threshold': 200.0   # Порог для реинвестирования
        }
        
        # Кэш анализа пар
        self._pair_analysis_cache = {}
        self._cache_ttl = 3600  # 1 час
        
        # История распределения
        self._allocation_history = []
        self._profit_tracking = {}
        
        # Адаптивные пороги
        self._adaptive_thresholds = {
            'balance_400_800': {'pairs': 1, 'min_capital': 400},
            'balance_800_1500': {'pairs': 2, 'min_capital': 200},
            'balance_1500_3000': {'pairs': 3, 'min_capital': 200},
            'balance_3000_plus': {'pairs': 4, 'min_capital': 200}
        }

    async def analyze_trading_pairs(self, symbols: List[str]) -> List[PairAnalysis]:
        """Анализ торговых пар для отбора"""
        try:
            current_time = time.time()
            valid_analyses = []
            
            for symbol in symbols:
                # Проверяем кэш
                cache_key = f"{symbol}_{current_time // self._cache_ttl}"
                if cache_key in self._pair_analysis_cache:
                    analysis = self._pair_analysis_cache[cache_key]
                    if current_time - analysis.get('timestamp', 0) < self._cache_ttl:
                        valid_analyses.append(analysis['data'])
                        continue
                
                # Анализируем пару
                analysis = await self._analyze_single_pair(symbol)
                if analysis:
                    self._pair_analysis_cache[cache_key] = {
                        'data': analysis,
                        'timestamp': current_time
                    }
                    valid_analyses.append(analysis)
            
            # Сортируем по потенциалу прибыли
            valid_analyses.sort(key=lambda x: x.profit_potential, reverse=True)
            
            self.logger.info(f"📊 Проанализировано {len(valid_analyses)} пар из {len(symbols)}")
            return valid_analyses
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка анализа пар: {e}")
            return []

    async def _analyze_single_pair(self, symbol: str) -> Optional[PairAnalysis]:
        """Анализ одной торговой пары"""
        try:
            # Получаем данные за 4 часа
            ohlcv = self.ex.fetch_ohlcv(symbol, '1h', limit=4)
            if len(ohlcv) < 4:
                return None
            
            # Рассчитываем волатильность
            prices = [candle[4] for candle in ohlcv]  # Close prices
            volatility = self._calculate_volatility(prices)
            
            # Рассчитываем ликвидность (объем)
            volumes = [candle[5] for candle in ohlcv]
            avg_volume = sum(volumes) / len(volumes)
            liquidity = avg_volume * prices[-1]  # Примерная ликвидность в USD
            
            # Рассчитываем тренд
            trend = self._calculate_trend(prices)
            
            # Рассчитываем ATR
            atr = self._calculate_atr(ohlcv)
            
            # Рассчитываем RSI
            rsi = self._calculate_rsi(prices)
            
            # Рассчитываем корреляцию с другими парами
            correlation = await self._calculate_correlation(symbol, prices)
            
            # Рассчитываем риск-скор
            risk_score = self._calculate_risk_score(volatility, atr, rsi)
            
            # Рассчитываем потенциал прибыли
            profit_potential = self._calculate_profit_potential(
                volatility, liquidity, trend, risk_score
            )
            
            return PairAnalysis(
                symbol=symbol,
                volatility=volatility,
                liquidity=liquidity,
                trend=trend,
                correlation=correlation,
                atr=atr,
                rsi=rsi,
                volume=avg_volume,
                risk_score=risk_score,
                profit_potential=profit_potential
            )
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка анализа пары {symbol}: {e}")
            return None

    def _calculate_volatility(self, prices: List[float]) -> float:
        """Расчет волатильности"""
        if len(prices) < 2:
            return 0.0
        
        returns = []
        for i in range(1, len(prices)):
            ret = (prices[i] - prices[i-1]) / prices[i-1]
            returns.append(ret)
        
        if not returns:
            return 0.0
        
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        volatility = (variance ** 0.5) * 100  # В процентах
        
        return volatility

    def _calculate_trend(self, prices: List[float]) -> float:
        """Расчет тренда (0-1, где 0.5 = боковой)"""
        if len(prices) < 2:
            return 0.5
        
        first_price = prices[0]
        last_price = prices[-1]
        price_change = (last_price - first_price) / first_price
        
        # Нормализуем к 0-1 (0.5 = боковой)
        trend = 0.5 + (price_change * 10)  # Масштабируем
        trend = max(0.0, min(1.0, trend))  # Ограничиваем
        
        return trend

    def _calculate_atr(self, ohlcv: List[List]) -> float:
        """Расчет Average True Range"""
        if len(ohlcv) < 2:
            return 0.0
        
        true_ranges = []
        for i in range(1, len(ohlcv)):
            high = ohlcv[i][2]
            low = ohlcv[i][3]
            prev_close = ohlcv[i-1][4]
            
            tr1 = high - low
            tr2 = abs(high - prev_close)
            tr3 = abs(low - prev_close)
            
            true_range = max(tr1, tr2, tr3)
            true_ranges.append(true_range)
        
        if not true_ranges:
            return 0.0
        
        atr = sum(true_ranges) / len(true_ranges)
        return atr

    def _calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Расчет RSI"""
        if len(prices) < period + 1:
            return 50.0
        
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        if len(gains) < period:
            return 50.0
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi

    async def _calculate_correlation(self, symbol: str, prices: List[float]) -> float:
        """Расчет корреляции с другими парами (упрощенная версия)"""
        # В реальной реализации здесь был бы расчет корреляции
        # с другими парами из кэша анализа
        return 0.3  # Заглушка

    def _calculate_risk_score(self, volatility: float, atr: float, rsi: float) -> float:
        """Расчет общего риска (0-1)"""
        # Нормализуем волатильность (3-6% = 0.3-0.6)
        vol_score = min(1.0, volatility / 10.0)
        
        # Нормализуем ATR
        atr_score = min(1.0, atr / 100.0)
        
        # RSI риск (экстремальные значения = высокий риск)
        rsi_risk = abs(rsi - 50) / 50.0
        
        # Общий риск
        risk_score = (vol_score + atr_score + rsi_risk) / 3.0
        return min(1.0, risk_score)

    def _calculate_profit_potential(self, volatility: float, liquidity: float, 
                                  trend: float, risk_score: float) -> float:
        """Расчет потенциала прибыли (0-1)"""
        # Волатильность в оптимальном диапазоне (3-6%)
        vol_score = 1.0 if 3.0 <= volatility <= 6.0 else 0.5
        
        # Ликвидность >$5M
        liq_score = 1.0 if liquidity > 5000000 else 0.3
        
        # Тренд в оптимальном диапазоне (0.4-0.6 = боковой с легким трендом)
        trend_score = 1.0 if 0.4 <= trend <= 0.6 else 0.5
        
        # Низкий риск = высокий потенциал
        risk_score_inverted = 1.0 - risk_score
        
        # Общий потенциал
        profit_potential = (vol_score + liq_score + trend_score + risk_score_inverted) / 4.0
        return min(1.0, profit_potential)

    async def select_optimal_pairs(self, analyses: List[PairAnalysis], 
                                 mode: TradingMode, total_capital: float = None) -> List[PairAnalysis]:
        """Выбор оптимальных пар для торговли с адаптивной конфигурацией"""
        try:
            # Для режима AUTOMATIC используем адаптивную конфигурацию
            if mode == TradingMode.AUTOMATIC and total_capital:
                mode_config = self.get_adaptive_mode_config(total_capital)
                self.logger.info(f"🎯 Используем адаптивную конфигурацию для капитала ${total_capital:.2f}")
            else:
                mode_config = self.trading_modes[mode]
            
            selected_pairs = []
            
            # Получаем параметры фильтрации
            vol_min, vol_max = mode_config['volatility_range']
            min_liquidity = mode_config.get('liquidity_threshold', 1000000)
            correlation_limit = mode_config['correlation_limit']
            
            # Фильтруем по критериям режима
            for analysis in analyses:
                self.logger.info(f"🔍 Анализируем {analysis.symbol}: волатильность {analysis.volatility:.2f}%, ликвидность ${analysis.liquidity:,.0f}")
                
                # Проверяем волатильность
                if not (vol_min <= analysis.volatility <= vol_max):
                    self.logger.warning(f"❌ {analysis.symbol}: волатильность {analysis.volatility:.2f}% не в диапазоне {vol_min}-{vol_max}%")
                    continue
                
                # Проверяем ликвидность
                if analysis.liquidity < min_liquidity:
                    self.logger.warning(f"❌ {analysis.symbol}: ликвидность ${analysis.liquidity:,.0f} < ${min_liquidity:,.0f}")
                    continue
                
                # Проверяем корреляцию с уже выбранными
                if self._check_correlation_limit(analysis, selected_pairs, correlation_limit):
                    self.logger.warning(f"❌ {analysis.symbol}: корреляция превышает лимит {correlation_limit}")
                    continue
                
                selected_pairs.append(analysis)
                self.logger.info(f"✅ {analysis.symbol}: выбрана (волатильность: {analysis.volatility:.2f}%, ликвидность: ${analysis.liquidity:,.0f})")
                
                # Ограничиваем количество пар
                if len(selected_pairs) >= mode_config['max_pairs']:
                    break
            
            # Fallback для режима automatic - если ни одна пара не подходит
            if mode == TradingMode.AUTOMATIC and len(selected_pairs) == 0 and len(analyses) > 0:
                self.logger.warning("⚠️ Ни одна пара не подходит под адаптивные критерии, используем fallback")
                # Берем лучшие пары по потенциалу прибыли
                fallback_pairs = sorted(analyses, key=lambda x: x.profit_potential, reverse=True)
                selected_pairs = fallback_pairs[:mode_config['max_pairs']]
                self.logger.info(f"🔄 Fallback: выбрано {len(selected_pairs)} пар по потенциалу прибыли")
            
            # Логируем итоговые критерии
            if mode == TradingMode.AUTOMATIC:
                self.logger.info(f"🎯 Итоговые критерии для режима AUTOMATIC:")
                self.logger.info(f"   📊 Волатильность: {mode_config['volatility_range'][0]}-{mode_config['volatility_range'][1]}%")
                self.logger.info(f"   💰 Ликвидность: >${min_liquidity:,}")
                self.logger.info(f"   🔗 Корреляция: <{correlation_limit}")
                self.logger.info(f"   📈 Максимум пар: {mode_config['max_pairs']}")
                self.logger.info(f"   🎯 Тир капитала: {mode_config.get('tier', 'unknown')}")
            
            self.logger.info(f"🎯 Выбрано {len(selected_pairs)} пар для режима {mode.value}")
            return selected_pairs
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка выбора пар: {e}")
            return []

    def _check_correlation_limit(self, new_pair: PairAnalysis, 
                               existing_pairs: List[PairAnalysis], 
                               limit: float) -> bool:
        """Проверка лимита корреляции"""
        for existing in existing_pairs:
            if abs(new_pair.correlation - existing.correlation) > limit:
                return True
        return False

    async def distribute_capital_adaptively(self, mode: TradingMode, 
                                          selected_pairs: List[PairAnalysis]) -> Dict[str, CapitalAllocation]:
        """Адаптивное распределение капитала с динамической конфигурацией"""
        try:
            # Получаем текущий баланс
            total_capital = await self.get_total_capital()
            if total_capital <= 0:
                self.logger.warning("⚠️ Общий капитал равен нулю")
                return {}
            
            # Для режима AUTOMATIC используем адаптивную конфигурацию
            if mode == TradingMode.AUTOMATIC:
                mode_config = self.get_adaptive_mode_config(total_capital)
                self.logger.info(f"🎯 Адаптивное распределение для капитала ${total_capital:.2f}")
            else:
                mode_config = self.trading_modes[mode]
            
            # Определяем количество пар на основе конфигурации
            pair_count = mode_config['max_pairs']
            
            # Ограничиваем выбранные пары
            pairs_to_use = selected_pairs[:pair_count]
            
            # Рассчитываем распределение
            allocations = {}
            
            for i, pair in enumerate(pairs_to_use):
                # Базовое распределение
                base_allocation = total_capital / len(pairs_to_use)
                
                # Приоритет для "лучшей" пары (60/40)
                if i == 0:
                    allocation = base_allocation * 1.2
                else:
                    allocation = base_allocation * 0.8
                
                # Ограничиваем минимальным порогом
                min_capital = mode_config['min_capital_per_pair']
                if allocation < min_capital:
                    allocation = min_capital
                
                # Рассчитываем параметры риска
                risk_level = mode_config.get('risk_level', 'medium')
                profit_target = allocation * 0.1  # 10% цель
                stop_loss = allocation * (mode_config['max_drawdown_pct'] / 100)
                
                # Создаем распределение
                allocation_obj = CapitalAllocation(
                    symbol=pair.symbol,
                    allocated_amount=allocation,
                    min_amount=min_capital,
                    max_amount=allocation * 2.0,
                    risk_level=risk_level,
                    profit_target=profit_target,
                    stop_loss=stop_loss,
                    trailing_stop=True,
                    position_size=allocation / pair.atr if pair.atr > 0 else 0
                )
                
                allocations[pair.symbol] = allocation_obj
                
                self.logger.info(f"💰 {pair.symbol}: ${allocation:.2f} "
                               f"(риск: {risk_level}, цель: ${profit_target:.2f})")
            
            # Сохраняем в историю
            self._allocation_history.append({
                'timestamp': datetime.now().isoformat(),
                'mode': mode.value,
                'total_capital': total_capital,
                'tier': mode_config.get('tier', 'unknown'),
                'allocations': {k: v.allocated_amount for k, v in allocations.items()}
            })
            
            return allocations
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка распределения капитала: {e}")
            return {}

    def _determine_pair_count(self, total_capital: float, mode: TradingMode) -> int:
        """Определение количества пар на основе капитала"""
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

    def _determine_risk_level(self, pair: PairAnalysis, mode: TradingMode) -> str:
        """Определение уровня риска для пары"""
        if pair.risk_score < 0.3:
            return "low"
        elif pair.risk_score < 0.6:
            return "medium"
        else:
            return "high"

    async def get_total_capital(self) -> float:
        """Получение общего капитала"""
        try:
            if not self.ex:
                return 0.0
            
            balance = self.ex.fetch_balance({'type': 'spot'})
            total_usdt = float(balance.get('total', {}).get('USDT', 0.0))
            
            if total_usdt <= 0:
                self.logger.warning("⚠️ Общий капитал в USDT равен нулю")
                return 0.0
            
            self.logger.info(f"💰 Общий капитал: ${total_usdt:.2f} USDT")
            return total_usdt
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения капитала: {e}")
            return 0.0

    async def update_floating_profit(self, symbol: str, current_price: float, 
                                   allocation: CapitalAllocation) -> Dict[str, Any]:
        """Обновление плавающего профита"""
        try:
            if symbol not in self._profit_tracking:
                self._profit_tracking[symbol] = {
                    'entry_price': current_price,
                    'max_profit': 0.0,
                    'trailing_active': False,
                    'partial_closed': False
                }
            
            tracking = self._profit_tracking[symbol]
            entry_price = tracking['entry_price']
            
            # Рассчитываем текущую прибыль
            current_profit = (current_price - entry_price) / entry_price * allocation.allocated_amount
            
            # Обновляем максимальную прибыль
            if current_profit > tracking['max_profit']:
                tracking['max_profit'] = current_profit
            
            # Активируем трейлинг при достижении порога
            if (current_profit >= self.floating_profit_config['min_profit_for_trailing'] and 
                not tracking['trailing_active']):
                tracking['trailing_active'] = True
                self.logger.info(f"🎯 Активирован трейлинг для {symbol} при прибыли ${current_profit:.2f}")
            
            # Частичное закрытие при достижении цели
            if (current_profit >= allocation.profit_target and 
                not tracking['partial_closed']):
                tracking['partial_closed'] = True
                self.logger.info(f"💰 Частичное закрытие {symbol} при прибыли ${current_profit:.2f}")
            
            # Реинвестирование при превышении порога
            if current_profit >= self.floating_profit_config['reinvestment_threshold']:
                self.logger.info(f"🔄 Реинвестирование {symbol} при прибыли ${current_profit:.2f}")
                # Здесь можно добавить логику реинвестирования
            
            return {
                'current_profit': current_profit,
                'max_profit': tracking['max_profit'],
                'trailing_active': tracking['trailing_active'],
                'partial_closed': tracking['partial_closed'],
                'profit_pct': (current_profit / allocation.allocated_amount) * 100
            }
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка обновления плавающего профита для {symbol}: {e}")
            return {}

    async def get_allocation_summary(self) -> Dict[str, Any]:
        """Получение сводки по распределению"""
        try:
            total_allocated = sum(
                allocation.allocated_amount 
                for allocation in self._allocation_history[-1].get('allocations', {}).values()
            ) if self._allocation_history else 0
            
            active_pairs = len(self._profit_tracking)
            total_profit = sum(
                tracking.get('max_profit', 0) 
                for tracking in self._profit_tracking.values()
            )
            
            return {
                'total_allocated': total_allocated,
                'active_pairs': active_pairs,
                'total_profit': total_profit,
                'allocation_history': self._allocation_history[-5:],  # Последние 5
                'profit_tracking': self._profit_tracking
            }
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения сводки: {e}")
            return {}

    def get_trading_mode_recommendation(self, total_capital: float) -> TradingMode:
        """Рекомендация режима торговли на основе капитала"""
        if total_capital < 800:
            return TradingMode.CONSERVATIVE
        elif total_capital < 2000:
            return TradingMode.AUTOMATIC
        else:
            return TradingMode.AGGRESSIVE

    def get_adaptive_mode_config(self, total_capital: float, market_conditions: Dict[str, Any] = None) -> Dict[str, Any]:
        """Адаптивная конфигурация режима на основе капитала и рыночных условий"""
        
        # Базовые пороги капитала - увеличены лимиты пар
        capital_tiers = [
            {'min': 0, 'max': 400, 'tier': 'micro', 'pairs': 2, 'min_capital': 200, 'risk': 'low'},
            {'min': 400, 'max': 800, 'tier': 'small', 'pairs': 3, 'min_capital': 200, 'risk': 'low'},
            {'min': 800, 'max': 1500, 'tier': 'medium', 'pairs': 4, 'min_capital': 200, 'risk': 'medium'},
            {'min': 1500, 'max': 3000, 'tier': 'large', 'pairs': 5, 'min_capital': 200, 'risk': 'medium'},
            {'min': 3000, 'max': 5000, 'tier': 'xlarge', 'pairs': 6, 'min_capital': 200, 'risk': 'high'},
            {'min': 5000, 'max': float('inf'), 'tier': 'mega', 'pairs': 8, 'min_capital': 200, 'risk': 'high'}
        ]
        
        # Определяем текущий тир капитала
        current_tier = None
        for tier in capital_tiers:
            if tier['min'] <= total_capital < tier['max']:
                current_tier = tier
                break
        
        if not current_tier:
            current_tier = capital_tiers[-1]  # Максимальный тир
        
        # Адаптивные настройки на основе тира
        adaptive_config = {
            'tier': current_tier['tier'],
            'min_pairs': current_tier['pairs'],
            'max_pairs': current_tier['pairs'],
            'min_capital_per_pair': current_tier['min_capital'],
            'risk_level': current_tier['risk'],
            'volatility_range': self._get_volatility_range(current_tier['risk']),
            'correlation_limit': self._get_correlation_limit(current_tier['risk']),
            'liquidity_threshold': self._get_liquidity_threshold(current_tier['tier']),
            'max_drawdown_pct': self._get_drawdown_limit(current_tier['risk'])
        }
        
        # Адаптация к рыночным условиям
        if market_conditions:
            adaptive_config = self._adapt_to_market_conditions(adaptive_config, market_conditions)
        
        self.logger.info(f"🎯 Адаптивная конфигурация для капитала ${total_capital:.2f}:")
        self.logger.info(f"   📊 Тир: {adaptive_config['tier']}")
        self.logger.info(f"   📈 Пар: {adaptive_config['min_pairs']}-{adaptive_config['max_pairs']}")
        self.logger.info(f"   💰 Минимум на пару: ${adaptive_config['min_capital_per_pair']}")
        self.logger.info(f"   ⚠️ Риск: {adaptive_config['risk_level']}")
        self.logger.info(f"   📊 Волатильность: {adaptive_config['volatility_range'][0]}-{adaptive_config['volatility_range'][1]}%")
        self.logger.info(f"   💰 Ликвидность: >${adaptive_config['liquidity_threshold']:,}")
        
        return adaptive_config

    def _get_volatility_range(self, risk_level: str) -> Tuple[float, float]:
        """Получение диапазона волатильности на основе уровня риска"""
        ranges = {
            'low': (0.1, 8.0),      # Консервативный - очень широкий диапазон
            'medium': (0.1, 10.0),  # Умеренный - очень широкий диапазон  
            'high': (0.1, 15.0)     # Агрессивный - очень широкий диапазон
        }
        return ranges.get(risk_level, (0.1, 10.0))

    def _get_correlation_limit(self, risk_level: str) -> float:
        """Получение лимита корреляции на основе уровня риска"""
        limits = {
            'low': 0.7,     # Смягченный контроль корреляции
            'medium': 0.8,  # Смягченный контроль
            'high': 0.9     # Очень мягкий контроль
        }
        return limits.get(risk_level, 0.8)

    def _get_liquidity_threshold(self, tier: str) -> float:
        """Получение порога ликвидности на основе тира капитала"""
        thresholds = {
            'micro': 50000,     # $50K - очень низкие требования
            'small': 100000,    # $100K - очень низкие требования
            'medium': 200000,   # $200K - очень низкие требования
            'large': 500000,    # $500K - очень низкие требования
            'xlarge': 1000000,  # $1M - очень низкие требования
            'mega': 2000000     # $2M - очень низкие требования
        }
        return thresholds.get(tier, 100000)

    def _get_drawdown_limit(self, risk_level: str) -> float:
        """Получение лимита просадки на основе уровня риска"""
        limits = {
            'low': 3.0,     # 3% максимальная просадка
            'medium': 5.0,  # 5% максимальная просадка
            'high': 8.0     # 8% максимальная просадка
        }
        return limits.get(risk_level, 5.0)

    def _adapt_to_market_conditions(self, config: Dict[str, Any], market_conditions: Dict[str, Any]) -> Dict[str, Any]:
        """Адаптация конфигурации к рыночным условиям"""
        # Если рынок волатильный, увеличиваем требования к ликвидности
        if market_conditions.get('high_volatility', False):
            config['liquidity_threshold'] *= 1.5
            config['volatility_range'] = (config['volatility_range'][0], config['volatility_range'][1] * 1.2)
        
        # Если рынок стабильный, можем снизить требования
        if market_conditions.get('low_volatility', False):
            config['liquidity_threshold'] *= 0.8
            config['correlation_limit'] = min(0.9, config['correlation_limit'] + 0.1)
        
        # Если рынок трендовый, увеличиваем количество пар
        if market_conditions.get('trending_market', False):
            config['max_pairs'] = min(5, config['max_pairs'] + 1)
        
        return config
