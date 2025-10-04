#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Dashboard - Улучшенный дашборд с фокусом на функционал и дизайн
Enhanced Trading System v3.0 Commercial
"""

import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from flask import Blueprint, render_template, jsonify, request, session
from functools import wraps

# Импорты системы
from src.core.subscription_manager import subscription_manager, SubscriptionTier
from src.core.plugin_manager import plugin_manager
from src.trading.enhanced_grid_bot import EnhancedMultiAssetGridBot
from src.trading.enhanced_scalp_bot import EnhancedMultiAssetScalpBot

# Создаем Blueprint для дашборда
dashboard_bp = Blueprint('dashboard', __name__)

def login_required(f):
    """Декоратор для проверки авторизации"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({"error": "Требуется авторизация"}), 401
        return f(*args, **kwargs)
    return decorated_function

def subscription_required(tier: SubscriptionTier):
    """Декоратор для проверки подписки"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = session.get('user_id')
            if not user_id:
                return jsonify({"error": "Требуется авторизация"}), 401
            
            subscription = subscription_manager.get_user_subscription(user_id)
            if not subscription:
                return jsonify({"error": "Требуется подписка"}), 403
            
            user_tier = SubscriptionTier(subscription['tier'])
            if user_tier.value != tier.value and user_tier.value != 'enterprise':
                return jsonify({"error": f"Требуется подписка {tier.value}"}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

class DashboardDataProvider:
    """Провайдер данных для дашборда"""
    
    def __init__(self):
        self.cache = {}
        self.cache_timeout = 60  # секунд
    
    async def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """Получение статистики пользователя"""
        cache_key = f"user_stats_{user_id}"
        
        # Проверяем кэш
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if datetime.now().timestamp() - timestamp < self.cache_timeout:
                return cached_data
        
        # Получаем данные
        subscription = subscription_manager.get_user_subscription(user_id)
        limits = subscription_manager.get_user_limits(user_id)
        usage = subscription_manager.check_limits(user_id)
        
        stats = {
            "subscription": {
                "tier": subscription['tier'] if subscription else 'free',
                "status": subscription['status'] if subscription else 'inactive',
                "end_date": subscription['end_date'] if subscription else None
            },
            "limits": limits,
            "usage": usage,
            "timestamp": datetime.now().isoformat()
        }
        
        # Кэшируем данные
        self.cache[cache_key] = (stats, datetime.now().timestamp())
        
        return stats
    
    async def get_trading_data(self, user_id: int) -> Dict[str, Any]:
        """Получение торговых данных"""
        # Здесь будет интеграция с торговыми ботами
        return {
            "active_bots": 0,
            "total_trades": 0,
            "profit_loss": 0.0,
            "win_rate": 0.0,
            "balance": 0.0
        }
    
    async def get_market_data(self) -> Dict[str, Any]:
        """Получение рыночных данных"""
        # Здесь будет интеграция с биржами
        return {
            "btc_price": 50000.0,
            "eth_price": 3000.0,
            "market_cap": 2000000000000,
            "fear_greed_index": 50
        }

# Создаем экземпляр провайдера данных
data_provider = DashboardDataProvider()

@dashboard_bp.route('/')
@login_required
async def dashboard():
    """Главная страница дашборда"""
    user_id = session['user_id']
    
    # Получаем данные
    user_stats = await data_provider.get_user_stats(user_id)
    trading_data = await data_provider.get_trading_data(user_id)
    market_data = await data_provider.get_market_data()
    
    return render_template('dashboard_enhanced.html',
                         user_stats=user_stats,
                         trading_data=trading_data,
                         market_data=market_data)

@dashboard_bp.route('/api/stats')
@login_required
async def api_stats():
    """API для получения статистики"""
    user_id = session['user_id']
    
    try:
        stats = await data_provider.get_user_stats(user_id)
        trading_data = await data_provider.get_trading_data(user_id)
        market_data = await data_provider.get_market_data()
        
        return jsonify({
            "success": True,
            "data": {
                "user_stats": stats,
                "trading_data": trading_data,
                "market_data": market_data
            }
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@dashboard_bp.route('/api/bots')
@login_required
async def api_bots():
    """API для управления ботами"""
    user_id = session['user_id']
    
    # Проверяем подписку
    subscription = subscription_manager.get_user_subscription(user_id)
    if not subscription:
        return jsonify({"error": "Требуется подписка"}), 403
    
    # Получаем доступные боты
    available_bots = plugin_manager.get_available_bots()
    
    return jsonify({
        "success": True,
        "data": {
            "available_bots": available_bots,
            "active_bots": [],  # Здесь будет список активных ботов
            "limits": subscription_manager.get_user_limits(user_id)
        }
    })

@dashboard_bp.route('/api/bots/start', methods=['POST'])
@login_required
@subscription_required(SubscriptionTier.BASIC)
async def api_start_bot():
    """API для запуска бота"""
    user_id = session['user_id']
    data = request.get_json()
    
    bot_type = data.get('bot_type')
    config = data.get('config', {})
    
    if not bot_type:
        return jsonify({"error": "Тип бота не указан"}), 400
    
    try:
        # Создаем бота
        bot = plugin_manager.create_bot(bot_type, config)
        if not bot:
            return jsonify({"error": "Не удалось создать бота"}), 500
        
        # Запускаем бота
        await bot.start()
        
        return jsonify({
            "success": True,
            "message": f"Бот {bot_type} запущен"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@dashboard_bp.route('/api/bots/stop', methods=['POST'])
@login_required
async def api_stop_bot():
    """API для остановки бота"""
    user_id = session['user_id']
    data = request.get_json()
    
    bot_id = data.get('bot_id')
    if not bot_id:
        return jsonify({"error": "ID бота не указан"}), 400
    
    try:
        # Здесь будет логика остановки бота
        return jsonify({
            "success": True,
            "message": f"Бот {bot_id} остановлен"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@dashboard_bp.route('/api/subscription')
@login_required
async def api_subscription():
    """API для информации о подписке"""
    user_id = session['user_id']
    
    subscription = subscription_manager.get_user_subscription(user_id)
    limits = subscription_manager.get_user_limits(user_id)
    
    return jsonify({
        "success": True,
        "data": {
            "subscription": subscription,
            "limits": limits
        }
    })

@dashboard_bp.route('/api/upgrade')
@login_required
async def api_upgrade():
    """API для обновления подписки"""
    user_id = session['user_id']
    
    # Получаем доступные тарифы
    available_tiers = []
    for tier in SubscriptionTier:
        config = subscription_manager.subscription_config[tier]
        available_tiers.append({
            "tier": tier.value,
            "name": config["name"],
            "price": config["price"],
            "features": config["features"]
        })
    
    return jsonify({
        "success": True,
        "data": {
            "available_tiers": available_tiers
        }
    })

# Регистрируем Blueprint
def register_dashboard(app):
    """Регистрация дашборда в приложении"""
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')


















