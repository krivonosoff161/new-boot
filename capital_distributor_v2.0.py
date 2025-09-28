#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Capital Distributor v2.0
Enhanced Trading System v3.0 Commercial
"""

class CapitalDistributor:
    """Распределитель капитала v2.0"""
    
    def __init__(self):
        """Инициализация распределителя капитала"""
        self.total_capital = 0
        self.allocations = {}
    
    def set_total_capital(self, capital: float) -> None:
        """
        Установка общего капитала
        
        Args:
            capital: Общий капитал
        """
        self.total_capital = capital
    
    def allocate_capital(self, asset: str, percentage: float) -> float:
        """
        Распределение капитала по активу
        
        Args:
            asset: Название актива
            percentage: Процент от общего капитала
            
        Returns:
            Выделенный капитал
        """
        allocated = self.total_capital * percentage / 100
        self.allocations[asset] = allocated
        return allocated
    
    def get_allocation(self, asset: str) -> float:
        """
        Получение выделенного капитала для актива
        
        Args:
            asset: Название актива
            
        Returns:
            Выделенный капитал
        """
        return self.allocations.get(asset, 0)
    
    def get_total_allocated(self) -> float:
        """
        Получение общего выделенного капитала
        
        Returns:
            Общий выделенный капитал
        """
        return sum(self.allocations.values())
    
    def reset_allocations(self) -> None:
        """Сброс всех распределений"""
        self.allocations.clear()






