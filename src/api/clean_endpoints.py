#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Чистые API endpoints для новой системы
"""

from flask import Blueprint, jsonify, request
from functools import wraps
import json

# Создаем blueprint
clean_api = Blueprint('clean_api', __name__)

def login_required_api(f):
    """Декоратор для проверки авторизации"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Простая проверка (в реальной системе здесь будет JWT или сессия)
        user_id = request.headers.get('X-User-ID', 5)  # Временно используем user_id=5
        return f(user_id, *args, **kwargs)
    return decorated_function

@clean_api.route('/api/clean/balance')
@login_required_api
def get_real_balance(user_id):
    """Получить реальный баланс пользователя"""
    try:
        from src.utils.balance_calculator import BalanceCalculator
        
        balance_calc = BalanceCalculator(user_id)
        balance_data = balance_calc.get_real_balance()
        
        return jsonify({
            'success': True,
            'balance': balance_data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Ошибка получения баланса: {str(e)}'
        })

@clean_api.route('/api/clean/balance/detailed')
@login_required_api
def get_detailed_balance(user_id):
    """Получить детальный баланс по биржам"""
    try:
        from src.utils.balance_calculator import BalanceCalculator
        
        balance_calc = BalanceCalculator(user_id)
        detailed_balance = balance_calc.get_detailed_balance()
        
        return jsonify({
            'success': True,
            'detailed_balance': detailed_balance
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Ошибка получения детального баланса: {str(e)}'
        })

@clean_api.route('/api/clean/bots')
@login_required_api
def get_user_bots(user_id):
    """Получить список ботов пользователя"""
    try:
        from src.utils.safe_bot_manager import SafeBotManager
        
        bot_manager = SafeBotManager(user_id)
        bots = bot_manager.get_all_bots()
        
        return jsonify({
            'success': True,
            'bots': bots
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Ошибка получения ботов: {str(e)}'
        })

@clean_api.route('/api/clean/bots/<bot_id>/details')
@login_required_api
def get_bot_details(user_id, bot_id):
    """Получить детальную информацию о боте"""
    try:
        from src.utils.safe_bot_manager import SafeBotManager
        
        bot_manager = SafeBotManager(user_id)
        bot_details = bot_manager.get_bot_details(bot_id)
        
        return jsonify(bot_details)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Ошибка получения деталей бота: {str(e)}'
        })

@clean_api.route('/api/clean/bots/create', methods=['POST'])
@login_required_api
def create_bot(user_id):
    """Создать нового бота"""
    try:
        data = request.get_json()
        
        from src.utils.safe_bot_manager import SafeBotManager
        
        bot_manager = SafeBotManager(user_id)
        result = bot_manager.create_bot(data)
        
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Ошибка создания бота: {str(e)}'
        })

@clean_api.route('/api/clean/bots/<bot_id>/automation', methods=['POST'])
@login_required_api
def update_automation(user_id, bot_id):
    """Обновить настройки автоматизации"""
    try:
        data = request.get_json()
        setting = data.get('setting')
        value = data.get('value')
        
        if not setting or value is None:
            return jsonify({
                'success': False,
                'error': 'Не указаны параметры setting и value'
            })
        
        from src.utils.safe_bot_manager import SafeBotManager
        
        bot_manager = SafeBotManager(user_id)
        result = bot_manager.update_automation(bot_id, setting, value)
        
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Ошибка обновления автоматизации: {str(e)}'
        })

@clean_api.route('/api/clean/trading-pairs')
@login_required_api
def get_trading_pairs(user_id):
    """Получить доступные торговые пары"""
    try:
        with open('data/trading_pairs.json', 'r', encoding='utf-8') as f:
            pairs_data = json.load(f)
        
        return jsonify({
            'success': True,
            'pairs': pairs_data.get('pairs', []),
            'recommended': pairs_data.get('recommended', []),
            'categories': pairs_data.get('categories', {})
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Ошибка получения торговых пар: {str(e)}'
        })

@clean_api.route('/api/clean/status')
@login_required_api
def get_system_status(user_id):
    """Получить статус системы"""
    try:
        from src.utils.balance_calculator import BalanceCalculator
        from src.utils.safe_bot_manager import SafeBotManager
        
        balance_calc = BalanceCalculator(user_id)
        bot_manager = SafeBotManager(user_id)
        
        balance = balance_calc.get_real_balance()
        bots = bot_manager.get_all_bots()
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'balance': balance,
            'bots_count': len(bots),
            'bots': bots,
            'system_status': 'operational',
            'safe_mode': True
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Ошибка получения статуса: {str(e)}'
        })


