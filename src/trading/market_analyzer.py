# v1.0 (+MACD, Bollinger Bands, Volume Profile, улучшенный анализ тренда)
"""
Модуль для расширенного анализа рынка.
v1.0: MACD, Bollinger Bands, Volume Profile, комбинированные фильтры.
"""
import numpy as np
import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class MarketRegime:
    """Режим рынка"""
    name: str
    confidence: float  # Уверенность в определении (0-1)
    trend_strength: float  # Сила тренда (-1 до 1)
    volatility: float  # Волатильность (0-1)
    volume_strength: float  # Сила объема (0-1)
    recommendation: str  # Рекомендация для торговли

@dataclass
class TechnicalIndicators:
    """Технические индикаторы"""
    rsi: float
    macd_line: float
    macd_signal: float
    macd_histogram: float
    bb_upper: float
    bb_middle: float
    bb_lower: float
    bb_width: float
    bb_position: float  # Позиция цены в BB (0-1)
    atr: float
    volume_sma: float
    volume_ratio: float  # Отношение текущего объема к среднему
    trend_direction: str  # 'up', 'down', 'sideways'
    trend_strength: float  # 0-1

class MarketAnalyzer:
    """
    Расширенный анализатор рынка.
    Включает MACD, Bollinger Bands, Volume Profile и комбинированные фильтры.
    """
    
    def __init__(self, user_id: int):
        """
        Инициализация Market Analyzer
        
        Args:
            user_id: ID пользователя
        """
        self.user_id = user_id
        self.logger = logging.getLogger(f"market_analyzer_{user_id}")
        
        # Параметры индикаторов
        self.rsi_period = 14
        self.macd_fast = 12
        self.macd_slow = 26
        self.macd_signal = 9
        self.bb_period = 20
        self.bb_std = 2
        self.atr_period = 14
        self.volume_sma_period = 20
        
    def calculate_rsi(self, closes: np.ndarray, period: int = None) -> float:
        """
        Расчет RSI
        
        Args:
            closes: Массив цен закрытия
            period: Период RSI
            
        Returns:
            float: Значение RSI (0-100)
        """
        try:
            if period is None:
                period = self.rsi_period
                
            if len(closes) < period + 1:
                return 50.0
            
            deltas = np.diff(closes)
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)
            
            avg_gains = np.mean(gains[-period:])
            avg_losses = np.mean(losses[-period:])
            
            if avg_losses == 0:
                return 100.0
            
            rs = avg_gains / avg_losses
            rsi = 100 - (100 / (1 + rs))
            
            return rsi
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка расчета RSI: {e}")
            return 50.0
    
    def calculate_macd(self, closes: np.ndarray) -> Tuple[float, float, float]:
        """
        Расчет MACD
        
        Args:
            closes: Массив цен закрытия
            
        Returns:
            Tuple[float, float, float]: (MACD line, Signal line, Histogram)
        """
        try:
            if len(closes) < self.macd_slow:
                return 0.0, 0.0, 0.0
            
            # EMA для быстрой и медленной линий
            ema_fast = self.calculate_ema(closes, self.macd_fast)
            ema_slow = self.calculate_ema(closes, self.macd_slow)
            
            macd_line = ema_fast - ema_slow
            
            # Для сигнальной линии нужна история MACD
            if len(closes) < self.macd_slow + self.macd_signal:
                return macd_line, 0.0, 0.0
            
            # Упрощенный расчет сигнальной линии
            macd_signal = macd_line * 0.9  # Упрощение
            macd_histogram = macd_line - macd_signal
            
            return macd_line, macd_signal, macd_histogram
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка расчета MACD: {e}")
            return 0.0, 0.0, 0.0
    
    def calculate_ema(self, data: np.ndarray, period: int) -> float:
        """
        Расчет EMA
        
        Args:
            data: Массив данных
            period: Период EMA
            
        Returns:
            float: Значение EMA
        """
        try:
            if len(data) < period:
                return np.mean(data)
            
            alpha = 2.0 / (period + 1)
            ema = data[0]
            
            for i in range(1, len(data)):
                ema = alpha * data[i] + (1 - alpha) * ema
            
            return ema
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка расчета EMA: {e}")
            return np.mean(data) if len(data) > 0 else 0.0
    
    def calculate_bollinger_bands(self, closes: np.ndarray) -> Tuple[float, float, float, float, float]:
        """
        Расчет Bollinger Bands
        
        Args:
            closes: Массив цен закрытия
            
        Returns:
            Tuple[float, float, float, float, float]: (Upper, Middle, Lower, Width, Position)
        """
        try:
            if len(closes) < self.bb_period:
                current_price = closes[-1] if len(closes) > 0 else 0
                return current_price, current_price, current_price, 0.0, 0.5
            
            # Берем последние N периодов
            recent_closes = closes[-self.bb_period:]
            
            # Средняя линия (SMA)
            middle = np.mean(recent_closes)
            
            # Стандартное отклонение
            std = np.std(recent_closes)
            
            # Верхняя и нижняя полосы
            upper = middle + (self.bb_std * std)
            lower = middle - (self.bb_std * std)
            
            # Ширина полос (в %)
            width = ((upper - lower) / middle) * 100 if middle > 0 else 0
            
            # Позиция цены в полосах (0-1)
            current_price = closes[-1]
            if upper != lower:
                position = (current_price - lower) / (upper - lower)
                position = max(0, min(1, position))  # Ограничиваем 0-1
            else:
                position = 0.5
            
            return upper, middle, lower, width, position
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка расчета Bollinger Bands: {e}")
            current_price = closes[-1] if len(closes) > 0 else 0
            return current_price, current_price, current_price, 0.0, 0.5
    
    def calculate_atr(self, ohlcv: List) -> float:
        """
        Расчет ATR (Average True Range)
        
        Args:
            ohlcv: Данные OHLCV
            
        Returns:
            float: Значение ATR
        """
        try:
            if len(ohlcv) < self.atr_period + 1:
                return 0.0
            
            true_ranges = []
            for i in range(1, len(ohlcv)):
                high = ohlcv[i][2]
                low = ohlcv[i][3]
                prev_close = ohlcv[i-1][4]
                
                tr = max(
                    high - low,
                    abs(high - prev_close),
                    abs(low - prev_close)
                )
                true_ranges.append(tr)
            
            # Берем последние N значений
            recent_tr = true_ranges[-self.atr_period:]
            atr = np.mean(recent_tr)
            
            return atr
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка расчета ATR: {e}")
            return 0.0
    
    def calculate_volume_indicators(self, ohlcv: List) -> Tuple[float, float]:
        """
        Расчет индикаторов объема
        
        Args:
            ohlcv: Данные OHLCV
            
        Returns:
            Tuple[float, float]: (Volume SMA, Volume Ratio)
        """
        try:
            if len(ohlcv) < self.volume_sma_period:
                current_volume = ohlcv[-1][5] if len(ohlcv) > 0 else 0
                return current_volume, 1.0
            
            volumes = [candle[5] for candle in ohlcv]
            current_volume = volumes[-1]
            
            # SMA объема
            volume_sma = np.mean(volumes[-self.volume_sma_period:])
            
            # Отношение текущего объема к среднему
            volume_ratio = current_volume / volume_sma if volume_sma > 0 else 1.0
            
            return volume_sma, volume_ratio
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка расчета индикаторов объема: {e}")
            return 0.0, 1.0
    
    def analyze_trend(self, closes: np.ndarray, macd_line: float, macd_signal: float) -> Tuple[str, float]:
        """
        Анализ тренда
        
        Args:
            closes: Массив цен закрытия
            macd_line: Линия MACD
            macd_signal: Сигнальная линия MACD
            
        Returns:
            Tuple[str, float]: (Направление тренда, Сила тренда)
        """
        try:
            if len(closes) < 20:
                return 'sideways', 0.0
            
            # Анализ по MACD
            macd_bullish = macd_line > macd_signal
            macd_strength = abs(macd_line - macd_signal)
            
            # Анализ по наклону цены
            recent_closes = closes[-20:]
            x = np.arange(len(recent_closes))
            slope = np.polyfit(x, recent_closes, 1)[0]
            price_trend = slope / recent_closes[-1] * 100 if recent_closes[-1] > 0 else 0
            
            # Комбинированный анализ
            if macd_bullish and price_trend > 0.1:
                direction = 'up'
                strength = min(1.0, (macd_strength + abs(price_trend)) / 2)
            elif not macd_bullish and price_trend < -0.1:
                direction = 'down'
                strength = min(1.0, (macd_strength + abs(price_trend)) / 2)
            else:
                direction = 'sideways'
                strength = 0.0
            
            return direction, strength
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка анализа тренда: {e}")
            return 'sideways', 0.0
    
    def analyze_market_regime(self, ohlcv: List) -> MarketRegime:
        """
        Комплексный анализ режима рынка
        
        Args:
            ohlcv: Данные OHLCV
            
        Returns:
            MarketRegime: Режим рынка
        """
        try:
            if len(ohlcv) < 20:
                return MarketRegime(
                    name='insufficient_data',
                    confidence=0.0,
                    trend_strength=0.0,
                    volatility=0.0,
                    volume_strength=0.0,
                    recommendation='wait'
                )
            
            # Извлекаем данные
            closes = np.array([candle[4] for candle in ohlcv])
            highs = np.array([candle[2] for candle in ohlcv])
            lows = np.array([candle[3] for candle in ohlcv])
            
            # Рассчитываем индикаторы
            rsi = self.calculate_rsi(closes)
            macd_line, macd_signal, macd_histogram = self.calculate_macd(closes)
            bb_upper, bb_middle, bb_lower, bb_width, bb_position = self.calculate_bollinger_bands(closes)
            atr = self.calculate_atr(ohlcv)
            volume_sma, volume_ratio = self.calculate_volume_indicators(ohlcv)
            trend_direction, trend_strength = self.analyze_trend(closes, macd_line, macd_signal)
            
            # Анализ волатильности
            volatility = min(1.0, atr / closes[-1] * 100) if closes[-1] > 0 else 0.0
            
            # Анализ силы объема
            volume_strength = min(1.0, volume_ratio)
            
            # Определение режима рынка
            regime_name = 'neutral'
            confidence = 0.5
            recommendation = 'caution'
            
            # Трендовый режим
            if trend_strength > 0.6 and abs(rsi - 50) > 20:
                if trend_direction == 'up' and rsi < 70:
                    regime_name = 'strong_uptrend'
                    confidence = min(1.0, trend_strength + (70 - rsi) / 70)
                    recommendation = 'buy' if bb_position < 0.8 else 'hold'
                elif trend_direction == 'down' and rsi > 30:
                    regime_name = 'strong_downtrend'
                    confidence = min(1.0, trend_strength + (rsi - 30) / 70)
                    recommendation = 'sell' if bb_position > 0.2 else 'hold'
            
            # Боковой режим
            elif trend_strength < 0.3 and 0.3 < bb_position < 0.7:
                regime_name = 'sideways'
                confidence = 0.7
                recommendation = 'grid_trading' if volatility > 0.5 else 'wait'
            
            # Высокая волатильность
            elif volatility > 0.8:
                regime_name = 'high_volatility'
                confidence = min(1.0, volatility)
                recommendation = 'avoid' if volume_ratio < 0.5 else 'caution'
            
            # Низкая волатильность
            elif volatility < 0.2:
                regime_name = 'low_volatility'
                confidence = 0.8
                recommendation = 'wait'
            
            # Перекупленность/перепроданность
            elif rsi > 80:
                regime_name = 'overbought'
                confidence = 0.8
                recommendation = 'sell'
            elif rsi < 20:
                regime_name = 'oversold'
                confidence = 0.8
                recommendation = 'buy'
            
            return MarketRegime(
                name=regime_name,
                confidence=confidence,
                trend_strength=trend_strength if trend_direction == 'up' else -trend_strength,
                volatility=volatility,
                volume_strength=volume_strength,
                recommendation=recommendation
            )
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка анализа режима рынка: {e}")
            return MarketRegime(
                name='error',
                confidence=0.0,
                trend_strength=0.0,
                volatility=0.0,
                volume_strength=0.0,
                recommendation='wait'
            )
    
    def get_technical_indicators(self, ohlcv: List) -> TechnicalIndicators:
        """
        Получение всех технических индикаторов
        
        Args:
            ohlcv: Данные OHLCV
            
        Returns:
            TechnicalIndicators: Все индикаторы
        """
        try:
            if len(ohlcv) < 20:
                current_price = ohlcv[-1][4] if len(ohlcv) > 0 else 0
                return TechnicalIndicators(
                    rsi=50.0,
                    macd_line=0.0,
                    macd_signal=0.0,
                    macd_histogram=0.0,
                    bb_upper=current_price,
                    bb_middle=current_price,
                    bb_lower=current_price,
                    bb_width=0.0,
                    bb_position=0.5,
                    atr=0.0,
                    volume_sma=0.0,
                    volume_ratio=1.0,
                    trend_direction='sideways',
                    trend_strength=0.0
                )
            
            closes = np.array([candle[4] for candle in ohlcv])
            
            # Рассчитываем все индикаторы
            rsi = self.calculate_rsi(closes)
            macd_line, macd_signal, macd_histogram = self.calculate_macd(closes)
            bb_upper, bb_middle, bb_lower, bb_width, bb_position = self.calculate_bollinger_bands(closes)
            atr = self.calculate_atr(ohlcv)
            volume_sma, volume_ratio = self.calculate_volume_indicators(ohlcv)
            trend_direction, trend_strength = self.analyze_trend(closes, macd_line, macd_signal)
            
            return TechnicalIndicators(
                rsi=rsi,
                macd_line=macd_line,
                macd_signal=macd_signal,
                macd_histogram=macd_histogram,
                bb_upper=bb_upper,
                bb_middle=bb_middle,
                bb_lower=bb_lower,
                bb_width=bb_width,
                bb_position=bb_position,
                atr=atr,
                volume_sma=volume_sma,
                volume_ratio=volume_ratio,
                trend_direction=trend_direction,
                trend_strength=trend_strength
            )
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения технических индикаторов: {e}")
            current_price = ohlcv[-1][4] if len(ohlcv) > 0 else 0
            return TechnicalIndicators(
                rsi=50.0,
                macd_line=0.0,
                macd_signal=0.0,
                macd_histogram=0.0,
                bb_upper=current_price,
                bb_middle=current_price,
                bb_lower=current_price,
                bb_width=0.0,
                bb_position=0.5,
                atr=0.0,
                volume_sma=0.0,
                volume_ratio=1.0,
                trend_direction='sideways',
                trend_strength=0.0
            )
    
    def should_trade(self, regime: MarketRegime, indicators: TechnicalIndicators) -> Tuple[bool, str]:
        """
        Определение, стоит ли торговать
        
        Args:
            regime: Режим рынка
            indicators: Технические индикаторы
            
        Returns:
            Tuple[bool, str]: (Стоит ли торговать, Причина)
        """
        try:
            # Базовые проверки
            if regime.confidence < 0.1:
                return False, f"Низкая уверенность в режиме: {regime.confidence:.2f}"
            
            if regime.volatility > 0.95:
                return False, f"Слишком высокая волатильность: {regime.volatility:.2f}"
            
            # В демо-режиме волатильность может быть очень низкой, поэтому используем более мягкий порог
            if regime.volatility < 0.0001:  # Более мягкий порог для демо-режима
                return False, f"Слишком низкая волатильность: {regime.volatility:.2f}"
            
            # В демо-режиме объемы могут быть нулевыми, поэтому пропускаем эту проверку
            if indicators.volume_ratio < 0.001 and indicators.volume_ratio > 0:  # Только если объем не равен точно 0
                return False, f"Слишком низкий объем: {indicators.volume_ratio:.2f}"
            
            # Проверки по режиму
            if regime.name == 'strong_uptrend':
                if indicators.bb_position > 0.9:  # Цена у верхней полосы BB
                    return False, "Цена у верхней полосы Bollinger Bands"
                return True, "Сильный восходящий тренд"
            
            elif regime.name == 'strong_downtrend':
                if indicators.bb_position < 0.1:  # Цена у нижней полосы BB
                    return False, "Цена у нижней полосы Bollinger Bands"
                return True, "Сильный нисходящий тренд"
            
            elif regime.name == 'sideways':
                if 0.2 < indicators.bb_position < 0.8:  # Цена в середине BB
                    return True, "Боковое движение - идеально для грид-торговли"
                return False, "Цена у границ Bollinger Bands"
            
            elif regime.name == 'overbought':
                return False, "Перекупленность - избегать покупок"
            
            elif regime.name == 'oversold':
                return False, "Перепроданность - избегать продаж"
            
            elif regime.name == 'high_volatility':
                return False, "Высокая волатильность - рискованно"
            
            elif regime.name == 'low_volatility':
                return False, "Низкая волатильность - мало возможностей"
            
            # По умолчанию
            return False, f"Неопределенный режим: {regime.name}"
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка определения торговли: {e}")
            return False, f"Ошибка анализа: {e}"

