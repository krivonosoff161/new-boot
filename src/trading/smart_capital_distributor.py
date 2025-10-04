#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Умное распределение капитала
"""

import logging
from typing import Dict, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class CapitalAllocation:
    """Распределение капитала"""
    total_capital: float
    trading_capital: float
    reserve_capital: float
    buy_capital: float
    sell_capital: float

class SmartCapitalDistributor:
    """Умное распределение капитала"""
    
    def __init__(self):
        self.reserve_ratio = 0.1  # 10% в резерв
        self.buy_sell_ratio = 0.5  # 50/50 на покупку/продажу
    
    def distribute_capital(self, total_balance: float, pairs: List[str]) -> CapitalAllocation:
        """Распределить капитал"""
        # 90% в торговлю, 10% в резерв
        trading_capital = total_balance * (1 - self.reserve_ratio)
        reserve_capital = total_balance * self.reserve_ratio
        
        # 50/50 на покупку/продажу
        buy_capital = trading_capital * self.buy_sell_ratio
        sell_capital = trading_capital * self.buy_sell_ratio
        
        return CapitalAllocation(
            total_capital=total_balance,
            trading_capital=trading_capital,
            reserve_capital=reserve_capital,
            buy_capital=buy_capital,
            sell_capital=sell_capital
        )











