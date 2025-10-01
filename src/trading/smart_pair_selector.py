#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Умный селектор торговых пар
Анализирует все доступные пары и выбирает лучшие для торговли
"""

import asyncio
import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import numpy as np

logger = logging.getLogger(__name__)

@dataclass
class PairAnalysis:
    """Результат анализа торговой пары"""
    symbol: str
    smart_score: float
    volatility: float
    liquidity: float
    trend_strength: float
    market_regime: str
    recommendation: str
    risk_level: str
    rsi: float
    atr: float
    volume_ratio: float
    correlation_score: float

class SmartPairSelector:
    """Умный селектор торговых пар"""
    
    def __init__(self, exchange_manager, user_id: int, user_role: str = 'user'):
        self.exchange_manager = exchange_manager
        self.user_id = user_id
        self.user_role = user_role
        
        # Ограничения по ролям
        if user_role == 'super_admin':
            self.max_recommended_pairs = 50
            self.can_add_unlimited = True
        else:
            self.max_recommended_pairs = 10
            self.can_add_unlimited = False
    
    async def get_recommended_pairs(self, balance: float) -> List[PairAnalysis]:
        """Получить рекомендованные пары для торговли"""
        try:
            # Получаем все доступные пары
            all_pairs = await self._get_all_pairs()
            
            # Анализируем пары
            analyzed_pairs = []
            for pair in all_pairs[:100]:  # Ограничиваем для производительности
                try:
                    analysis = await self._analyze_pair(pair)
                    if analysis:
                        analyzed_pairs.append(analysis)
                except Exception as e:
                    logger.warning(f"Ошибка анализа пары {pair}: {e}")
                    continue
            
            # Сортируем по SmartScore
            analyzed_pairs.sort(key=lambda x: x.smart_score, reverse=True)
            
            # Возвращаем ограниченное количество
            return analyzed_pairs[:self.max_recommended_pairs]
            
        except Exception as e:
            logger.error(f"Ошибка получения рекомендованных пар: {e}")
            return []
    
    async def _get_all_pairs(self) -> List[str]:
        """Получить все доступные пары с биржи"""
        try:
            exchange = self.exchange_manager.create_exchange_instance('okx', 'demo_key', 'demo_secret')
            markets = await exchange.load_markets()
            
            # Фильтруем только USDT пары
            usdt_pairs = [symbol for symbol, market in markets.items() 
                         if market['quote'] == 'USDT' and market['active']]
            
            return usdt_pairs
            
        except Exception as e:
            logger.error(f"Ошибка получения пар с биржи: {e}")
            return []
    
    async def _analyze_pair(self, symbol: str) -> Optional[PairAnalysis]:
        """Анализ торговой пары"""
        try:
            exchange = self.exchange_manager.create_exchange_instance('okx', 'demo_key', 'demo_secret')
            
            # Получаем исторические данные
            ohlcv = await exchange.fetch_ohlcv(symbol, '1h', limit=100)
            if len(ohlcv) < 50:
                return None
            
            # Вычисляем индикаторы
            closes = [candle[4] for candle in ohlcv]
            volumes = [candle[5] for candle in ohlcv]
            
            # RSI
            rsi = self._calculate_rsi(closes)
            
            # ATR
            atr = self._calculate_atr(ohlcv)
            
            # Волатильность
            volatility = self._calculate_volatility(closes)
            
            # Ликвидность
            liquidity = self._calculate_liquidity(volumes)
            
            # Сила тренда
            trend_strength = self._calculate_trend_strength(closes)
            
            # Режим рынка
            market_regime = self._determine_market_regime(volatility, trend_strength)
            
            # SmartScore
            smart_score = self._calculate_smart_score(
                volatility, liquidity, trend_strength, rsi, atr
            )
            
            # Рекомендация
            recommendation = self._get_recommendation(smart_score, market_regime)
            
            # Уровень риска
            risk_level = self._get_risk_level(volatility, rsi)
            
            # Корреляция (заглушка)
            correlation_score = 0.3
            
            # Объем
            volume_ratio = np.mean(volumes) / np.max(volumes) if np.max(volumes) > 0 else 0
            
            return PairAnalysis(
                symbol=symbol,
                smart_score=smart_score,
                volatility=volatility,
                liquidity=liquidity,
                trend_strength=trend_strength,
                market_regime=market_regime,
                recommendation=recommendation,
                risk_level=risk_level,
                rsi=rsi,
                atr=atr,
                volume_ratio=volume_ratio,
                correlation_score=correlation_score
            )
            
        except Exception as e:
            logger.warning(f"Ошибка анализа пары {symbol}: {e}")
            return None
    
    def _calculate_rsi(self, closes: List[float], period: int = 14) -> float:
        """Вычисление RSI"""
        if len(closes) < period + 1:
            return 50.0
        
        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_atr(self, ohlcv: List[List], period: int = 14) -> float:
        """Вычисление ATR"""
        if len(ohlcv) < period + 1:
            return 0.0
        
        tr_values = []
        for i in range(1, len(ohlcv)):
            high = ohlcv[i][2]
            low = ohlcv[i][3]
            prev_close = ohlcv[i-1][4]
            
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            tr_values.append(tr)
        
        return np.mean(tr_values[-period:])
    
    def _calculate_volatility(self, closes: List[float]) -> float:
        """Вычисление волатильности"""
        if len(closes) < 2:
            return 0.0
        
        returns = np.diff(np.log(closes))
        return np.std(returns) * np.sqrt(24)  # Годовая волатильность
    
    def _calculate_liquidity(self, volumes: List[float]) -> float:
        """Вычисление ликвидности"""
        if not volumes:
            return 0.0
        
        return np.mean(volumes)
    
    def _calculate_trend_strength(self, closes: List[float]) -> float:
        """Вычисление силы тренда"""
        if len(closes) < 20:
            return 0.0
        
        # Простой линейный тренд
        x = np.arange(len(closes))
        slope = np.polyfit(x, closes, 1)[0]
        
        # Нормализуем
        price_range = max(closes) - min(closes)
        if price_range == 0:
            return 0.0
        
        return abs(slope) / price_range * 100
    
    def _determine_market_regime(self, volatility: float, trend_strength: float) -> str:
        """Определение режима рынка"""
        if volatility > 0.5 and trend_strength > 0.3:
            return "Трендовый"
        elif volatility > 0.3:
            return "Волатильный"
        elif trend_strength > 0.2:
            return "Стабильный тренд"
        else:
            return "Боковик"
    
    def _calculate_smart_score(self, volatility: float, liquidity: float, 
                             trend_strength: float, rsi: float, atr: float) -> float:
        """Вычисление SmartScore"""
        # Нормализуем показатели
        vol_score = min(volatility * 100, 50) / 50
        liq_score = min(liquidity / 1000000, 1.0)  # Нормализуем к 1M
        trend_score = min(trend_strength, 1.0)
        rsi_score = 1.0 - abs(rsi - 50) / 50  # Ближе к 50 = лучше
        atr_score = min(atr * 100, 1.0)
        
        # Взвешенная сумма
        smart_score = (
            vol_score * 0.25 +
            liq_score * 0.25 +
            trend_score * 0.20 +
            rsi_score * 0.15 +
            atr_score * 0.15
        )
        
        return min(smart_score, 1.0)
    
    def _get_recommendation(self, smart_score: float, market_regime: str) -> str:
        """Получить рекомендацию"""
        if smart_score > 0.8:
            return "Сильная покупка"
        elif smart_score > 0.6:
            return "Покупка"
        elif smart_score > 0.4:
            return "Нейтрально"
        elif smart_score > 0.2:
            return "Продажа"
        else:
            return "Сильная продажа"
    
    def _get_risk_level(self, volatility: float, rsi: float) -> str:
        """Определить уровень риска"""
        if volatility > 0.4 or rsi > 80 or rsi < 20:
            return "Высокий"
        elif volatility > 0.2 or rsi > 70 or rsi < 30:
            return "Средний"
        else:
            return "Низкий"
    
    def can_add_pair(self, current_pairs: List[str], new_pair: str) -> Tuple[bool, str]:
        """Проверить, можно ли добавить новую пару"""
        if self.can_add_unlimited:
            return True, "Супер-админ может добавлять неограниченное количество пар"
        
        if len(current_pairs) >= self.max_recommended_pairs:
            return False, f"Достигнут лимит в {self.max_recommended_pairs} пар для вашей роли"
        
        if new_pair in current_pairs:
            return False, "Пара уже добавлена"
        
        return True, "Пара может быть добавлена"
    
    def get_user_limits(self) -> Dict:
        """Получить лимиты пользователя"""
        return {
            'max_pairs': self.max_recommended_pairs,
            'can_add_unlimited': self.can_add_unlimited,
            'role': self.user_role
        }




