#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Balance Optimizer
Enhanced Trading System v3.0 Commercial
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from loguru import logger

class BalanceOptimizer:
    """Оптимизатор баланса для торговых стратегий"""
    
    def __init__(self):
        """Инициализация оптимизатора"""
        self.optimization_history = []
        
    def optimize_balance_distribution(self, 
                                    total_balance: float,
                                    assets: List[str],
                                    risk_per_asset: float = 0.02,
                                    max_assets: int = 5) -> Dict[str, float]:
        """
        Оптимизация распределения баланса по активам
        
        Args:
            total_balance: Общий баланс
            assets: Список активов
            risk_per_asset: Риск на актив
            max_assets: Максимальное количество активов
            
        Returns:
            Словарь с распределением баланса
        """
        try:
            # Ограничиваем количество активов
            selected_assets = assets[:max_assets]
            
            # Равномерное распределение с учетом риска
            balance_per_asset = total_balance / len(selected_assets)
            
            # Применяем коэффициент риска
            risk_adjusted_balance = balance_per_asset * (1 - risk_per_asset)
            
            distribution = {}
            for asset in selected_assets:
                distribution[asset] = risk_adjusted_balance
            
            # Сохраняем историю оптимизации
            self.optimization_history.append({
                'timestamp': datetime.now(),
                'total_balance': total_balance,
                'distribution': distribution.copy(),
                'risk_per_asset': risk_per_asset
            })
            
            logger.info(f"Баланс оптимизирован: {len(selected_assets)} активов, {risk_per_asset*100}% риск на актив")
            
            return distribution
            
        except Exception as e:
            logger.error(f"Ошибка оптимизации баланса: {e}")
            return {}
    
    def calculate_optimal_position_size(self, 
                                     balance: float,
                                     asset_price: float,
                                     risk_percentage: float = 0.02,
                                     stop_loss_percentage: float = 0.01) -> float:
        """
        Расчет оптимального размера позиции
        
        Args:
            balance: Доступный баланс
            asset_price: Цена актива
            risk_percentage: Процент риска
            stop_loss_percentage: Процент стоп-лосса
            
        Returns:
            Оптимальный размер позиции
        """
        try:
            # Рассчитываем максимальный риск в долларах
            max_risk_usd = balance * risk_percentage
            
            # Рассчитываем размер позиции на основе стоп-лосса
            stop_loss_price = asset_price * (1 - stop_loss_percentage)
            price_difference = asset_price - stop_loss_price
            
            if price_difference > 0:
                position_size = max_risk_usd / price_difference
            else:
                position_size = 0
            
            # Ограничиваем размер позиции доступным балансом
            max_position_size = balance / asset_price
            position_size = min(position_size, max_position_size)
            
            logger.debug(f"Оптимальный размер позиции: {position_size:.6f} для цены {asset_price}")
            
            return position_size
            
        except Exception as e:
            logger.error(f"Ошибка расчета размера позиции: {e}")
            return 0.0
    
    def rebalance_portfolio(self, 
                          current_balances: Dict[str, float],
                          target_distribution: Dict[str, float],
                          total_balance: float) -> Dict[str, float]:
        """
        Ребалансировка портфеля
        
        Args:
            current_balances: Текущие балансы
            target_distribution: Целевое распределение
            total_balance: Общий баланс
            
        Returns:
            Рекомендации по ребалансировке
        """
        try:
            rebalance_actions = {}
            
            for asset, target_percentage in target_distribution.items():
                target_balance = total_balance * target_percentage
                current_balance = current_balances.get(asset, 0)
                
                difference = target_balance - current_balance
                
                if abs(difference) > total_balance * 0.01:  # Минимальный порог 1%
                    rebalance_actions[asset] = {
                        'current': current_balance,
                        'target': target_balance,
                        'difference': difference,
                        'action': 'BUY' if difference > 0 else 'SELL'
                    }
            
            logger.info(f"Ребалансировка: {len(rebalance_actions)} активов требуют корректировки")
            
            return rebalance_actions
            
        except Exception as e:
            logger.error(f"Ошибка ребалансировки: {e}")
            return {}
    
    def get_optimization_history(self) -> List[Dict[str, Any]]:
        """
        Получение истории оптимизации
        
        Returns:
            Список записей оптимизации
        """
        return self.optimization_history.copy()
    
    def clear_history(self) -> None:
        """Очистка истории оптимизации"""
        self.optimization_history.clear()
        logger.info("История оптимизации очищена")














