#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Advanced Signal Generator
Enhanced Trading System v3.0 Commercial
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from loguru import logger

class ScalpSignal:
    """Класс для генерации сигналов скальпинга"""
    
    def __init__(self, symbol: str, timeframe: str = '1m'):
        """
        Инициализация генератора сигналов
        
        Args:
            symbol: Торговая пара
            timeframe: Таймфрейм
        """
        self.symbol = symbol
        self.timeframe = timeframe
        self.signals = []
        
    def generate_signal(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Генерация сигнала на основе данных
        
        Args:
            data: Данные свечей
            
        Returns:
            Словарь с сигналом
        """
        try:
            if len(data) < 20:
                return {'signal': 'HOLD', 'confidence': 0.0, 'reason': 'Недостаточно данных'}
            
            # Простая логика генерации сигналов
            close_prices = data['close'].values
            sma_short = np.mean(close_prices[-5:])
            sma_long = np.mean(close_prices[-20:])
            
            if sma_short > sma_long * 1.001:
                signal = 'BUY'
                confidence = min(0.9, (sma_short - sma_long) / sma_long * 100)
            elif sma_short < sma_long * 0.999:
                signal = 'SELL'
                confidence = min(0.9, (sma_long - sma_short) / sma_long * 100)
            else:
                signal = 'HOLD'
                confidence = 0.0
            
            return {
                'signal': signal,
                'confidence': confidence,
                'reason': f'SMA Short: {sma_short:.4f}, SMA Long: {sma_long:.4f}',
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Ошибка генерации сигнала: {e}")
            return {'signal': 'HOLD', 'confidence': 0.0, 'reason': f'Ошибка: {e}'}

class AdvancedSignalGenerator:
    """Продвинутый генератор сигналов"""
    
    def __init__(self):
        """Инициализация генератора"""
        self.signal_generators = {}
        
    def add_signal_generator(self, symbol: str, timeframe: str = '1m') -> ScalpSignal:
        """
        Добавление генератора сигналов для пары
        
        Args:
            symbol: Торговая пара
            timeframe: Таймфрейм
            
        Returns:
            Генератор сигналов
        """
        generator = ScalpSignal(symbol, timeframe)
        self.signal_generators[f"{symbol}_{timeframe}"] = generator
        return generator
    
    def get_signal(self, symbol: str, timeframe: str, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Получение сигнала для пары
        
        Args:
            symbol: Торговая пара
            timeframe: Таймфрейм
            data: Данные свечей
            
        Returns:
            Словарь с сигналом
        """
        key = f"{symbol}_{timeframe}"
        
        if key not in self.signal_generators:
            self.add_signal_generator(symbol, timeframe)
        
        return self.signal_generators[key].generate_signal(data)
    
    def get_all_signals(self, data_dict: Dict[str, pd.DataFrame]) -> Dict[str, Dict[str, Any]]:
        """
        Получение всех сигналов
        
        Args:
            data_dict: Словарь с данными для каждой пары
            
        Returns:
            Словарь со всеми сигналами
        """
        signals = {}
        
        for symbol, data in data_dict.items():
            try:
                signal = self.get_signal(symbol, '1m', data)
                signals[symbol] = signal
            except Exception as e:
                logger.error(f"Ошибка получения сигнала для {symbol}: {e}")
                signals[symbol] = {'signal': 'HOLD', 'confidence': 0.0, 'reason': f'Ошибка: {e}'}
        
        return signals


















