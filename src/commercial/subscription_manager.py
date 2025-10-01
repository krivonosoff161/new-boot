#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Subscription Manager - Система управления подписками
Enhanced Trading System v3.0 Commercial
"""

import os
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum

class SubscriptionTier(Enum):
    """Уровни подписки"""
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"

class SubscriptionStatus(Enum):
    """Статусы подписки"""
    ACTIVE = "active"
    EXPIRED = "expired"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"
    TRIAL = "trial"

class SubscriptionManager:
    """
    Менеджер подписок для коммерческого проекта
    
    Функции:
    - Управление подписками пользователей
    - Контроль доступа к функциям
    - Биллинг и платежи
    - Аналитика и отчеты
    """
    
    def __init__(self, db_path: str = "data/database/subscriptions.db"):
        self.db_path = db_path
        self.init_database()
        
        # Конфигурация подписок
        self.subscription_config = {
            SubscriptionTier.FREE: {
                "name": "Бесплатный",
                "price": 0,
                "duration_days": 30,
                "max_bots": 1,
                "max_capital": 1000,
                "features": ["basic_trading", "web_interface"],
                "api_calls_per_hour": 100,
                "support": "community"
            },
            SubscriptionTier.BASIC: {
                "name": "Базовый",
                "price": 29.99,
                "duration_days": 30,
                "max_bots": 3,
                "max_capital": 10000,
                "features": ["basic_trading", "web_interface", "telegram_bot", "basic_analytics"],
                "api_calls_per_hour": 1000,
                "support": "email"
            },
            SubscriptionTier.PREMIUM: {
                "name": "Премиум",
                "price": 99.99,
                "duration_days": 30,
                "max_bots": 10,
                "max_capital": 100000,
                "features": ["all_trading", "web_interface", "telegram_bot", "advanced_analytics", "ml_signals"],
                "api_calls_per_hour": 5000,
                "support": "priority_email"
            },
            SubscriptionTier.PROFESSIONAL: {
                "name": "Профессиональный",
                "price": 299.99,
                "duration_days": 30,
                "max_bots": 50,
                "max_capital": 1000000,
                "features": ["all_trading", "web_interface", "telegram_bot", "advanced_analytics", "ml_signals", "api_access", "custom_strategies"],
                "api_calls_per_hour": 20000,
                "support": "phone"
            },
            SubscriptionTier.ENTERPRISE: {
                "name": "Корпоративный",
                "price": 999.99,
                "duration_days": 30,
                "max_bots": -1,  # Без ограничений
                "max_capital": -1,  # Без ограничений
                "features": ["all_trading", "web_interface", "telegram_bot", "advanced_analytics", "ml_signals", "api_access", "custom_strategies", "white_label", "dedicated_support"],
                "api_calls_per_hour": -1,  # Без ограничений
                "support": "dedicated"
            }
        }
    
    def init_database(self):
        """Инициализация базы данных подписок"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Таблица подписок
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    tier TEXT NOT NULL,
                    status TEXT NOT NULL,
                    start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    end_date TIMESTAMP,
                    auto_renew BOOLEAN DEFAULT 1,
                    payment_method TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица платежей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subscription_id INTEGER,
                    amount DECIMAL(10,2) NOT NULL,
                    currency TEXT DEFAULT 'USD',
                    status TEXT NOT NULL,
                    payment_method TEXT,
                    transaction_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (subscription_id) REFERENCES subscriptions (id)
                )
            ''')
            
            # Таблица использования
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS usage_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    date DATE NOT NULL,
                    api_calls INTEGER DEFAULT 0,
                    bots_active INTEGER DEFAULT 0,
                    capital_used DECIMAL(15,2) DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
    
    def create_subscription(self, user_id: int, tier: SubscriptionTier, 
                          payment_method: str = "manual") -> bool:
        """Создание новой подписки"""
        try:
            config = self.subscription_config[tier]
            end_date = datetime.now() + timedelta(days=config["duration_days"])
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Деактивируем старые подписки
                cursor.execute('''
                    UPDATE subscriptions 
                    SET status = ?, updated_at = ?
                    WHERE user_id = ? AND status = ?
                ''', (SubscriptionStatus.CANCELLED.value, datetime.now().isoformat(), 
                      user_id, SubscriptionStatus.ACTIVE.value))
                
                # Создаем новую подписку
                cursor.execute('''
                    INSERT INTO subscriptions 
                    (user_id, tier, status, end_date, payment_method)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, tier.value, SubscriptionStatus.ACTIVE.value, 
                      end_date.isoformat(), payment_method))
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"Ошибка создания подписки: {e}")
            return False
    
    def get_user_subscription(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получение активной подписки пользователя"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM subscriptions 
                    WHERE user_id = ? AND status = ?
                    ORDER BY created_at DESC LIMIT 1
                ''', (user_id, SubscriptionStatus.ACTIVE.value))
                
                result = cursor.fetchone()
                if result:
                    return {
                        "id": result[0],
                        "user_id": result[1],
                        "tier": result[2],
                        "status": result[3],
                        "start_date": result[4],
                        "end_date": result[5],
                        "auto_renew": bool(result[6]),
                        "payment_method": result[7]
                    }
                return None
                
        except Exception as e:
            print(f"Ошибка получения подписки: {e}")
            return None
    
    def check_feature_access(self, user_id: int, feature: str) -> bool:
        """Проверка доступа к функции"""
        subscription = self.get_user_subscription(user_id)
        if not subscription:
            return False
        
        tier = SubscriptionTier(subscription["tier"])
        config = self.subscription_config[tier]
        
        return feature in config["features"]
    
    def get_user_limits(self, user_id: int) -> Dict[str, Any]:
        """Получение лимитов пользователя"""
        subscription = self.get_user_subscription(user_id)
        if not subscription:
            # Возвращаем лимиты для бесплатного тарифа
            return self.subscription_config[SubscriptionTier.FREE]
        
        tier = SubscriptionTier(subscription["tier"])
        return self.subscription_config[tier]
    
    def update_usage(self, user_id: int, api_calls: int = 0, 
                    bots_active: int = 0, capital_used: float = 0):
        """Обновление статистики использования"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Обновляем или создаем запись за сегодня
                today = datetime.now().date().isoformat()
                cursor.execute('''
                    INSERT OR REPLACE INTO usage_stats 
                    (user_id, date, api_calls, bots_active, capital_used)
                    VALUES (?, ?, 
                        COALESCE((SELECT api_calls FROM usage_stats WHERE user_id = ? AND date = ?), 0) + ?,
                        COALESCE((SELECT bots_active FROM usage_stats WHERE user_id = ? AND date = ?), 0) + ?,
                        COALESCE((SELECT capital_used FROM usage_stats WHERE user_id = ? AND date = ?), 0) + ?
                    )
                ''', (user_id, today, user_id, today, api_calls, 
                      user_id, today, bots_active, user_id, today, capital_used))
                
                conn.commit()
                
        except Exception as e:
            print(f"Ошибка обновления статистики: {e}")
    
    def check_limits(self, user_id: int) -> Dict[str, bool]:
        """Проверка соблюдения лимитов"""
        limits = self.get_user_limits(user_id)
        subscription = self.get_user_subscription(user_id)
        
        if not subscription:
            return {"api_calls": False, "bots": False, "capital": False}
        
        # Получаем текущее использование
        today = datetime.now().date().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT api_calls, bots_active, capital_used 
                FROM usage_stats 
                WHERE user_id = ? AND date = ?
            ''', (user_id, today))
            
            result = cursor.fetchone()
            if not result:
                return {"api_calls": True, "bots": True, "capital": True}
            
            current_api_calls, current_bots, current_capital = result
            
            return {
                "api_calls": current_api_calls < limits["api_calls_per_hour"],
                "bots": current_bots < limits["max_bots"] if limits["max_bots"] > 0 else True,
                "capital": current_capital < limits["max_capital"] if limits["max_capital"] > 0 else True
            }
    
    def get_subscription_stats(self) -> Dict[str, Any]:
        """Получение статистики подписок"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Общая статистика
                cursor.execute('SELECT COUNT(*) FROM subscriptions WHERE status = ?', 
                             (SubscriptionStatus.ACTIVE.value,))
                active_subscriptions = cursor.fetchone()[0]
                
                # Статистика по тарифам
                cursor.execute('''
                    SELECT tier, COUNT(*) 
                    FROM subscriptions 
                    WHERE status = ? 
                    GROUP BY tier
                ''', (SubscriptionStatus.ACTIVE.value,))
                tier_stats = dict(cursor.fetchall())
                
                # Доходы
                cursor.execute('''
                    SELECT SUM(amount) 
                    FROM payments 
                    WHERE status = 'completed' 
                    AND created_at >= date('now', '-30 days')
                ''')
                monthly_revenue = cursor.fetchone()[0] or 0
                
                return {
                    "active_subscriptions": active_subscriptions,
                    "tier_distribution": tier_stats,
                    "monthly_revenue": monthly_revenue
                }
                
        except Exception as e:
            print(f"Ошибка получения статистики: {e}")
            return {}

# Глобальный экземпляр менеджера подписок
subscription_manager = SubscriptionManager()













