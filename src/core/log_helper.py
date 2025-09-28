#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Logging Helper
Enhanced Trading System v3.0 Commercial
"""

import os
import sys
from loguru import logger
from typing import Optional

def build_logger(
    name: str = "enhanced_trading_system",
    level: str = "INFO",
    log_file: Optional[str] = None,
    rotation: str = "10 MB",
    retention: str = "7 days"
) -> logger:
    """
    Создание и настройка логгера
    
    Args:
        name: Имя логгера
        level: Уровень логирования
        log_file: Путь к файлу логов (если None, логи только в консоль)
        rotation: Ротация логов
        retention: Время хранения логов
        
    Returns:
        Настроенный логгер
    """
    # Удаляем стандартный обработчик
    logger.remove()
    
    # Добавляем обработчик для консоли
    logger.add(
        sys.stdout,
        level=level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True
    )
    
    # Добавляем обработчик для файла если указан
    if log_file:
        # Создаем директорию для логов если не существует
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        logger.add(
            log_file,
            level=level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation=rotation,
            retention=retention,
            encoding="utf-8"
        )
    
    return logger

def get_logger(name: str = "enhanced_trading_system") -> logger:
    """
    Получение логгера по имени
    
    Args:
        name: Имя логгера
        
    Returns:
        Логгер
    """
    return logger.bind(name=name)

# Создаем глобальный логгер
main_logger = build_logger(
    name="enhanced_trading_system",
    level="INFO",
    log_file="logs/system.log"
)








