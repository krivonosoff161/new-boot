#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Dashboard - ПОЛНОСТЬЮ РАБОЧАЯ ВЕРСИЯ
Enhanced Trading System v3.0 Commercial
"""

import os
import sys
import json
import psutil
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from flask import Flask, render_template, jsonify, request, session, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from functools import wraps

# Добавляем пути для импорта модулей
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Создаем Flask приложение
app = Flask(__name__, template_folder='src/web/templates', static_folder='src/web/static')
app.secret_key = 'enhanced-trading-system-secret-key-2024'

# Настройка Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Модель пользователя
class User(UserMixin):
    def __init__(self, user_id, username, email, role='user'):
        self.id = user_id
        self.username = username
        self.email = email
        self.role = role

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    if user:
        return User(user['id'], user['username'], user['email'], user['role'])
    return None

def get_db_connection():
    """Подключение к базе данных"""
    conn = sqlite3.connect('secure_users.db')
    conn.row_factory = sqlite3.Row
    return conn

def login_required_api(f):
    """Декоратор для API endpoints"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'success': False, 'error': 'Требуется авторизация'}), 401
        return f(*args, **kwargs)
    return decorated_function

# ============================================================================
# ОСНОВНЫЕ СТРАНИЦЫ
# ============================================================================

@app.route('/')
def index():
    """Главная страница"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Страница входа"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password_hash'], password):
            user_obj = User(user['id'], user['username'], user['email'], user['role'])
            login_user(user_obj)
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            return redirect(url_for('dashboard'))
        else:
            flash('Неверное имя пользователя или пароль', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """Выход из системы"""
    logout_user()
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Главная страница дашборда"""
    return render_template('dashboard.html')

@app.route('/bots')
@login_required
def bots():
    """Страница управления ботами"""
    return render_template('bots.html')

@app.route('/clean')
@login_required
def clean_dashboard():
    """Чистая система управления ботами"""
    return render_template('clean_dashboard.html')

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.route('/api/balance')
@login_required_api
def api_balance():
    """API для получения баланса"""
    try:
        from src.utils.balance_calculator import BalanceCalculator
        balance_calc = BalanceCalculator(current_user.id)
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

@app.route('/api/balance/detailed')
@login_required_api
def api_detailed_balance():
    """API для получения детального баланса"""
    try:
        from src.utils.balance_calculator import BalanceCalculator
        balance_calc = BalanceCalculator(current_user.id)
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

@app.route('/api/dashboard/bots')
@login_required_api
def api_dashboard_bots():
    """API для получения данных о ботах для дашборда"""
    try:
        bots_data = []
        try:
            with open('data/bot_status.json', 'r', encoding='utf-8') as f:
                bots_status = json.load(f)
                for bot_id, status in bots_status.items():
                    if status.get('user_id') == current_user.id:
                        try:
                            bots_data.append({
                                'id': bot_id,
                                'status': status.get('status', 'unknown'),
                                'bot_type': status.get('bot_type', 'unknown'),
                                'created_at': status.get('created_at', ''),
                                'last_update': status.get('last_update', '')
                            })
                        except:
                            pass
        except:
            pass
        
        return jsonify({
            'success': True,
            'bots': bots_data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Ошибка получения ботов: {str(e)}'
        })

@app.route('/api/bots/status')
@login_required_api
def api_bots_status():
    """API для получения статуса всех ботов"""
    try:
        bots_data = []
        try:
            with open('data/bot_status.json', 'r', encoding='utf-8') as f:
                bots_status = json.load(f)
                for bot_id, status in bots_status.items():
                    if status.get('user_id') == current_user.id:
                        try:
                            bots_data.append({
                                'id': bot_id,
                                'status': status.get('status', 'unknown'),
                                'bot_type': status.get('bot_type', 'unknown'),
                                'created_at': status.get('created_at', ''),
                                'last_update': status.get('last_update', '')
                            })
                        except:
                            pass
        except:
            pass
        
        return jsonify({
            'success': True,
            'bots': bots_data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Ошибка получения статуса ботов: {str(e)}'
        })

@app.route('/api/bots/<bot_id>/details')
@login_required_api
def api_bot_details(bot_id):
    """API для получения детальной информации о боте"""
    try:
        from src.utils.safe_bot_manager import SafeBotManager
        
        bot_manager = SafeBotManager(current_user.id)
        bot_details = bot_manager.get_bot_details(bot_id)
        
        return jsonify(bot_details)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Ошибка получения деталей бота: {str(e)}'
        })

@app.route('/api/bots/create', methods=['POST'])
@login_required_api
def api_create_bot():
    """API для создания нового бота"""
    try:
        data = request.get_json()
        
        from src.utils.safe_bot_manager import SafeBotManager
        
        bot_manager = SafeBotManager(current_user.id)
        result = bot_manager.create_bot(data)
        
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Ошибка создания бота: {str(e)}'
        })

@app.route('/api/bots/<bot_id>/automation', methods=['POST'])
@login_required_api
def api_bot_automation(bot_id):
    """API для управления автоматизацией бота"""
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
        
        bot_manager = SafeBotManager(current_user.id)
        result = bot_manager.update_automation(bot_id, setting, value)
        
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Ошибка обновления автоматизации: {str(e)}'
        })

@app.route('/api/trading-pairs')
@login_required_api
def api_trading_pairs():
    """API для получения торговых пар"""
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

# ============================================================================
# ЧИСТЫЕ API ENDPOINTS
# ============================================================================

@app.route('/api/clean/status')
@login_required_api
def get_clean_system_status():
    """Получить статус чистой системы"""
    try:
        from src.utils.balance_calculator import BalanceCalculator
        from src.utils.safe_bot_manager import SafeBotManager
        
        balance_calc = BalanceCalculator(current_user.id)
        bot_manager = SafeBotManager(current_user.id)
        
        balance = balance_calc.get_real_balance()
        bots = bot_manager.get_all_bots()
        
        return jsonify({
            'success': True,
            'user_id': current_user.id,
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

@app.route('/api/clean/balance')
@login_required_api
def get_clean_balance():
    """Получить реальный баланс пользователя"""
    try:
        from src.utils.balance_calculator import BalanceCalculator
        
        balance_calc = BalanceCalculator(current_user.id)
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

@app.route('/api/clean/balance/detailed')
@login_required_api
def get_clean_detailed_balance():
    """Получить детальный баланс по биржам"""
    try:
        from src.utils.balance_calculator import BalanceCalculator
        
        balance_calc = BalanceCalculator(current_user.id)
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

@app.route('/api/clean/bots')
@login_required_api
def get_clean_bots():
    """Получить список ботов пользователя"""
    try:
        from src.utils.safe_bot_manager import SafeBotManager
        
        bot_manager = SafeBotManager(current_user.id)
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

@app.route('/api/clean/bots/<bot_id>/details')
@login_required_api
def get_clean_bot_details(bot_id):
    """Получить детальную информацию о боте"""
    try:
        from src.utils.safe_bot_manager import SafeBotManager
        
        bot_manager = SafeBotManager(current_user.id)
        bot_details = bot_manager.get_bot_details(bot_id)
        
        return jsonify(bot_details)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Ошибка получения деталей бота: {str(e)}'
        })

@app.route('/api/clean/bots/create', methods=['POST'])
@login_required_api
def create_clean_bot():
    """Создать нового бота"""
    try:
        data = request.get_json()
        
        from src.utils.safe_bot_manager import SafeBotManager
        
        bot_manager = SafeBotManager(current_user.id)
        result = bot_manager.create_bot(data)
        
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Ошибка создания бота: {str(e)}'
        })

@app.route('/api/clean/bots/<bot_id>/automation', methods=['POST'])
@login_required_api
def update_clean_automation(bot_id):
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
        
        bot_manager = SafeBotManager(current_user.id)
        result = bot_manager.update_automation(bot_id, setting, value)
        
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Ошибка обновления автоматизации: {str(e)}'
        })

@app.route('/api/clean/trading-pairs')
@login_required_api
def get_clean_trading_pairs():
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

# ============================================================================
# ЗАПУСК СЕРВЕРА
# ============================================================================

if __name__ == '__main__':
    print("🚀 Запуск Enhanced Dashboard...")
    print("🌐 Откройте браузер: http://localhost:5000")
    print("⏹️ Для остановки нажмите Ctrl+C")
    
    app.run(host='0.0.0.0', port=5000, debug=True)






