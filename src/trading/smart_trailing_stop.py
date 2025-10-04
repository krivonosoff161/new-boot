#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Умный трейлинг стоп
"""

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class SmartTrailingStop:
    """Умный трейлинг стоп"""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.base_stop_percent = 0.02  # 2% базовый стоп
    
    def calculate_stop_percent(self, market_regime: str, trend_strength: float) -> float:
        """Вычислить процент стоп-лосса"""
        if market_regime == "Трендовый" and trend_strength > 0.5:
            return self.base_stop_percent * 0.8  # Более агрессивный
        elif market_regime == "Боковик":
            return self.base_stop_percent * 1.5  # Более консервативный
        else:
            return self.base_stop_percent











