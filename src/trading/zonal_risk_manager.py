#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Зональный менеджер рисков для Grid стратегии
Управляет рисками в зависимости от расстояния уровней от текущей цены
"""

import numpy as np
import logging
from typing import Dict, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ZoneParams:
    """Параметры для зоны сетки"""
    tp_multiplier: float  # Множитель для take profit
    sl_multiplier: float  # Множитель для stop loss  
    position_size_multiplier: float  # Множитель размера позиции
    spacing_multiplier: float  # Множитель расстояния между уровнями
    max_levels: int  # Максимум уровней в зоне
    
class ZonalRiskManager:
    """
    Зональный менеджер рисков для Grid стратегии
    
    Концепция:
    - Ближние зоны (0-2% от цены): консервативные параметры, частые уровни
    - Средние зоны (2-5% от цены): сбалансированные параметры
    - Дальние зоны (5%+ от цены): агрессивные параметры, редкие уровни
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.ZonalRiskManager")
        
        # Определяем зоны (в процентах от текущей цены)
        self.zones = {
            'close': {
                'range': (0.0, 0.02),  # 0-2%
                'params': ZoneParams(
                    tp_multiplier=0.5,  # Быстрый профит
                    sl_multiplier=0.3,  # Узкий стоп
                    position_size_multiplier=1.5,  # Больше размер
                    spacing_multiplier=0.5,  # Частые уровни
                    max_levels=4
                )
            },
            'medium': {
                'range': (0.02, 0.05),  # 2-5%
                'params': ZoneParams(
                    tp_multiplier=1.0,  # Стандартный профит
                    sl_multiplier=1.0,  # Стандартный стоп
                    position_size_multiplier=1.0,  # Стандартный размер
                    spacing_multiplier=1.0,  # Стандартное расстояние
                    max_levels=3
                )
            },
            'far': {
                'range': (0.05, 0.15),  # 5-15%
                'params': ZoneParams(
                    tp_multiplier=2.0,  # Большой профит
                    sl_multiplier=2.0,  # Широкий стоп
                    position_size_multiplier=0.7,  # Меньше размер
                    spacing_multiplier=2.0,  # Редкие уровни
                    max_levels=2
                )
            }
        }
        
        self.logger.info("✅ Зональный риск-менеджер инициализирован")
    
    def get_zone_for_distance(self, distance_percent: float) -> str:
        """Определяет зону для заданного расстояния от цены"""
        for zone_name, zone_data in self.zones.items():
            min_dist, max_dist = zone_data['range']
            if min_dist <= distance_percent < max_dist:
                return zone_name
        
        # Если расстояние больше максимального, возвращаем дальнюю зону
        return 'far'
    
    def calculate_zone_params(self, current_price: float, target_price: float, 
                            base_volatility: float, market_regime: str) -> ZoneParams:
        """
        Рассчитывает параметры для уровня сетки в зависимости от зоны
        
        Args:
            current_price: Текущая цена
            target_price: Цена уровня сетки
            base_volatility: Базовая волатильность (ATR)
            market_regime: Режим рынка ('bullish', 'bearish', 'neutral', 'volatile')
            
        Returns:
            ZoneParams: Параметры для данного уровня
        """
        # Рассчитываем расстояние в процентах
        distance_percent = abs(target_price - current_price) / current_price
        
        # Определяем зону
        zone_name = self.get_zone_for_distance(distance_percent)
        base_params = self.zones[zone_name]['params']
        
        # Корректируем параметры в зависимости от режима рынка
        adjusted_params = self._adjust_for_market_regime(base_params, market_regime, base_volatility)
        
        # Корректируем под волатильность
        final_params = self._adjust_for_volatility(adjusted_params, base_volatility)
        
        self.logger.debug(f"Зона {zone_name} для расстояния {distance_percent:.3f}: "
                         f"TP×{final_params.tp_multiplier:.2f}, SL×{final_params.sl_multiplier:.2f}")
        
        return final_params
    
    def _adjust_for_market_regime(self, base_params: ZoneParams, regime: str, volatility: float) -> ZoneParams:
        """Корректирует параметры под режим рынка"""
        adjustments = {
            'bullish': {
                'tp_multiplier': 1.2,  # Больше профита в росте
                'sl_multiplier': 0.8,  # Меньше стопы
                'position_size_multiplier': 1.1
            },
            'bearish': {
                'tp_multiplier': 0.8,  # Меньше профита в падении
                'sl_multiplier': 1.2,  # Больше стопы
                'position_size_multiplier': 0.9
            },
            'volatile': {
                'tp_multiplier': 1.5,  # Больше профита в волатильности
                'sl_multiplier': 1.3,  # Больше стопы
                'position_size_multiplier': 0.8  # Меньше риска
            },
            'neutral': {
                'tp_multiplier': 1.0,
                'sl_multiplier': 1.0,
                'position_size_multiplier': 1.0
            }
        }
        
        adj = adjustments.get(regime, adjustments['neutral'])
        
        return ZoneParams(
            tp_multiplier=base_params.tp_multiplier * adj['tp_multiplier'],
            sl_multiplier=base_params.sl_multiplier * adj['sl_multiplier'],
            position_size_multiplier=base_params.position_size_multiplier * adj['position_size_multiplier'],
            spacing_multiplier=base_params.spacing_multiplier,
            max_levels=base_params.max_levels
        )
    
    def _adjust_for_volatility(self, params: ZoneParams, volatility: float) -> ZoneParams:
        """Корректирует параметры под волатильность"""
        # Высокая волатильность = больше стопы и профиты, меньше размеры
        vol_multiplier = min(max(volatility * 100, 0.5), 3.0)  # Ограничиваем от 0.5 до 3.0
        
        if vol_multiplier > 1.5:  # Высокая волатильность
            vol_adj = {
                'tp_multiplier': 1.3,
                'sl_multiplier': 1.4,
                'position_size_multiplier': 0.8
            }
        elif vol_multiplier < 0.8:  # Низкая волатильность
            vol_adj = {
                'tp_multiplier': 0.8,
                'sl_multiplier': 0.7,
                'position_size_multiplier': 1.2
            }
        else:  # Нормальная волатильность
            vol_adj = {
                'tp_multiplier': 1.0,
                'sl_multiplier': 1.0,
                'position_size_multiplier': 1.0
            }
        
        return ZoneParams(
            tp_multiplier=params.tp_multiplier * vol_adj['tp_multiplier'],
            sl_multiplier=params.sl_multiplier * vol_adj['sl_multiplier'],
            position_size_multiplier=params.position_size_multiplier * vol_adj['position_size_multiplier'],
            spacing_multiplier=params.spacing_multiplier,
            max_levels=params.max_levels
        )
    
    def calculate_dynamic_tp_sl(self, entry_price: float, current_price: float, 
                               is_long: bool, base_volatility: float, 
                               market_regime: str) -> Tuple[float, float]:
        """
        Рассчитывает динамические TP и SL для позиции
        
        Args:
            entry_price: Цена входа
            current_price: Текущая цена
            is_long: True для лонга, False для шорта
            base_volatility: Базовая волатильность (ATR)
            market_regime: Режим рынка
            
        Returns:
            Tuple[float, float]: (take_profit_price, stop_loss_price)
        """
        # Получаем параметры для зоны
        zone_params = self.calculate_zone_params(current_price, entry_price, base_volatility, market_regime)
        
        # Базовые размеры TP/SL от волатильности
        base_tp_size = base_volatility * zone_params.tp_multiplier
        base_sl_size = base_volatility * zone_params.sl_multiplier
        
        if is_long:
            tp_price = entry_price + (entry_price * base_tp_size)
            sl_price = entry_price - (entry_price * base_sl_size)
        else:
            tp_price = entry_price - (entry_price * base_tp_size)
            sl_price = entry_price + (entry_price * base_sl_size)
        
        self.logger.debug(f"Динамический TP/SL: entry={entry_price:.4f}, "
                         f"TP={tp_price:.4f}, SL={sl_price:.4f}")
        
        return tp_price, sl_price
    
    def calculate_optimal_position_size(self, symbol: str, entry_price: float, 
                                      current_price: float, available_capital: float,
                                      base_volatility: float, market_regime: str) -> float:
        """
        Рассчитывает оптимальный размер позиции для уровня сетки
        
        Args:
            symbol: Торговая пара
            entry_price: Цена входа
            current_price: Текущая цена
            available_capital: Доступный капитал
            base_volatility: Базовая волатильность
            market_regime: Режим рынка
            
        Returns:
            float: Размер позиции в USDT
        """
        # Получаем параметры зоны
        zone_params = self.calculate_zone_params(current_price, entry_price, base_volatility, market_regime)
        
        # Базовый размер позиции
        base_position_size = available_capital * 0.1  # 10% от доступного капитала
        
        # Корректируем под зону
        adjusted_size = base_position_size * zone_params.position_size_multiplier
        
        # Ограничиваем минимальный и максимальный размер
        min_size = self.config.get('grid', {}).get('min_order_usd', 20)
        max_size = available_capital * 0.3  # Максимум 30% капитала в одну позицию
        
        final_size = max(min_size, min(adjusted_size, max_size))
        
        self.logger.debug(f"Размер позиции для {symbol}: {final_size:.2f} USDT "
                         f"(зона: {zone_params.position_size_multiplier:.2f}×)")
        
        return final_size
    
    def get_zone_statistics(self) -> Dict:
        """Возвращает статистику по зонам"""
        stats = {}
        for zone_name, zone_data in self.zones.items():
            params = zone_data['params']
            stats[zone_name] = {
                'range': zone_data['range'],
                'tp_multiplier': params.tp_multiplier,
                'sl_multiplier': params.sl_multiplier,
                'position_size_multiplier': params.position_size_multiplier,
                'max_levels': params.max_levels
            }
        return stats
    
    def optimize_grid_levels(self, current_price: float, available_capital: float,
                           base_spacing: float, max_levels: int, 
                           volatility: float, market_regime: str) -> Dict:
        """
        Оптимизирует уровни сетки с учетом зон
        
        Returns:
            Dict: {
                'buy_levels': [{'price': float, 'size': float, 'tp': float, 'sl': float}],
                'sell_levels': [{'price': float, 'size': float, 'tp': float, 'sl': float}]
            }
        """
        buy_levels = []
        sell_levels = []
        
        # Рассчитываем уровни для каждой зоны
        for zone_name, zone_data in self.zones.items():
            zone_params = zone_data['params']
            min_dist, max_dist = zone_data['range']
            
            # Уровни покупки (ниже текущей цены)
            for i in range(zone_params.max_levels):
                distance = min_dist + (max_dist - min_dist) * (i / zone_params.max_levels) 
                price = current_price * (1 - distance)
                
                size = self.calculate_optimal_position_size(
                    "BTC/USDT", price, current_price, available_capital / max_levels,
                    volatility, market_regime
                )
                
                tp, sl = self.calculate_dynamic_tp_sl(
                    price, current_price, True, volatility, market_regime
                )
                
                buy_levels.append({
                    'price': price,
                    'size': size,
                    'tp': tp,
                    'sl': sl,
                    'zone': zone_name
                })
            
            # Уровни продажи (выше текущей цены)  
            for i in range(zone_params.max_levels):
                distance = min_dist + (max_dist - min_dist) * (i / zone_params.max_levels)
                price = current_price * (1 + distance)
                
                size = self.calculate_optimal_position_size(
                    "BTC/USDT", price, current_price, available_capital / max_levels,
                    volatility, market_regime
                )
                
                tp, sl = self.calculate_dynamic_tp_sl(
                    price, current_price, False, volatility, market_regime
                )
                
                sell_levels.append({
                    'price': price,
                    'size': size,
                    'tp': tp,
                    'sl': sl,
                    'zone': zone_name
                })
        
        return {
            'buy_levels': sorted(buy_levels, key=lambda x: x['price'], reverse=True),
            'sell_levels': sorted(sell_levels, key=lambda x: x['price'])
        }

# Тестирование модуля
if __name__ == "__main__":
    import json
    
    # Тестовая конфигурация
    test_config = {
        'grid': {
            'min_order_usd': 20,
            'max_position_size': 200
        }
    }
    
    # Создаем менеджер
    risk_manager = ZonalRiskManager(test_config)
    
    # Тестируем оптимизацию уровней
    current_price = 50000.0
    available_capital = 1000.0
    volatility = 0.02
    market_regime = 'neutral'
    
    levels = risk_manager.optimize_grid_levels(
        current_price, available_capital, 0.01, 10, volatility, market_regime
    )
    
    print("🧪 ТЕСТ ЗОНАЛЬНОГО РИСК-МЕНЕДЖЕРА")
    print("=" * 50)
    print(f"Текущая цена: ${current_price:,.2f}")
    print(f"Доступный капитал: ${available_capital:,.2f}")
    print(f"Волатильность: {volatility:.3f}")
    print(f"Режим рынка: {market_regime}")
    
    print("\n📈 УРОВНИ ПОКУПКИ:")
    for level in levels['buy_levels'][:5]:  # Показываем первые 5
        print(f"  ${level['price']:,.2f} | ${level['size']:.2f} | "
              f"TP: ${level['tp']:,.2f} | SL: ${level['sl']:,.2f} | {level['zone']}")
    
    print("\n📉 УРОВНИ ПРОДАЖИ:")
    for level in levels['sell_levels'][:5]:  # Показываем первые 5
        print(f"  ${level['price']:,.2f} | ${level['size']:.2f} | "
              f"TP: ${level['tp']:,.2f} | SL: ${level['sl']:,.2f} | {level['zone']}")
    
    print("\n📊 СТАТИСТИКА ПО ЗОНАМ:")
    stats = risk_manager.get_zone_statistics()
    for zone, data in stats.items():
        print(f"  {zone.upper()}: {data['range'][0]:.1%}-{data['range'][1]:.1%} | "
              f"TP×{data['tp_multiplier']:.1f} | SL×{data['sl_multiplier']:.1f} | "
              f"Size×{data['position_size_multiplier']:.1f}")
    
    print("\n✅ Тест завершен успешно!")
