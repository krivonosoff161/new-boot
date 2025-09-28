#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Dashboard - Рабочая версия дашборда
Enhanced Trading System v3.0 Commercial
"""

import os
import sys
import json
import psutil
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from functools import wraps

# Добавляем пути для импорта модулей
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Импортируем новые чистые API
from src.api.clean_endpoints import clean_api

# Создаем Flask приложение
app = Flask(__name__, template_folder='src/web/templates')
app.secret_key = 'enhanced-trading-system-secret-key-2024'

# Регистрируем новые чистые API
app.register_blueprint(clean_api)

# Настройка Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Пожалуйста, войдите в систему для доступа к этой странице.'

# Простой класс пользователя
class User(UserMixin):
    def __init__(self, user_id, username, email, role='user'):
        self.id = user_id
        self.username = username
        self.email = email
        self.role = role

@login_manager.user_loader
def load_user(user_id):
    """Загрузка пользователя для Flask-Login"""
    try:
        conn = sqlite3.connect('data/database/auth_users.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        user_data = cursor.fetchone()
        conn.close()
        
        if user_data:
            return User(user_data[0], user_data[1], user_data[2], user_data[4])
        return None
    except:
        return None

def login_required_api(f):
    """Декоратор для API endpoints требующих авторизации"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({"error": "Требуется авторизация"}), 401
        return f(*args, **kwargs)
    return decorated_function

# Маршруты
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
        username = request.form.get('username')
        password = request.form.get('password')
        
        try:
            conn = sqlite3.connect('data/database/auth_users.db')
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
            user_data = cursor.fetchone()
            conn.close()
            
            if user_data and check_password_hash(user_data[3], password):
                user = User(user_data[0], user_data[1], user_data[2], user_data[4])
                login_user(user)
                return redirect(url_for('dashboard'))
            else:
                return render_template('login.html', error='Неверные учетные данные')
        except:
            return render_template('login.html', error='Ошибка подключения к базе данных')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """Выход из системы"""
    logout_user()
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

# API Endpoints
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
        # Читаем статус ботов
        bots_data = []
        try:
            with open('data/bot_status.json', 'r', encoding='utf-8') as f:
                bots_status = json.load(f)
                for bot_id, status in bots_status.items():
                    bots_data.append({
                        'id': bot_id,
                        'status': status.get('status', 'unknown'),
                        'bot_type': status.get('bot_type', 'unknown'),
                        'created_at': status.get('created_at', ''),
                        'last_update': status.get('last_update', '')
                    })
        except:
            pass
        
        return jsonify({
            'success': True,
            'bots': bots_data
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

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
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/bots/<bot_id>/details')
@login_required_api
def api_bot_details(bot_id):
    """API для получения детальной информации о боте"""
    try:
        # Базовая информация о боте
        bot_info = {
            'id': bot_id,
            'bot_type': 'grid',  # По умолчанию grid
            'status': 'running',
            'created_at': datetime.now().isoformat(),
            'last_update': datetime.now().isoformat()
        }
        
        # Читаем реальный статус если есть
        try:
            with open('data/bot_status.json', 'r', encoding='utf-8') as f:
                bots_status = json.load(f)
                if bot_id in bots_status:
                    bot_info.update(bots_status[bot_id])
        except:
            pass
        
        # Системные метрики
        bot_info['system_metrics'] = get_system_metrics()
        
        # Торговые пары
        bot_info['trading_pairs'] = get_trading_pairs()
        
        # Графики (заглушки)
        bot_info['charts'] = {
            'price_chart': [],
            'volume_chart': [],
            'pnl_chart': [],
            'system_resources': []
        }
        
        return jsonify({
            'success': True,
            'bot_details': bot_info
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/system/metrics')
@login_required_api
def api_system_metrics():
    """API для получения системных метрик"""
    try:
        metrics = get_system_metrics()
        return jsonify({
            'success': True,
            'metrics': metrics
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/trading-pairs')
@login_required_api
def api_trading_pairs():
    """API для получения торговых пар"""
    try:
        pairs = get_trading_pairs()
        return jsonify({
            'success': True,
            'trading_pairs': pairs
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/recommended-pairs')
@login_required_api
def api_recommended_pairs():
    """API для получения рекомендованных пар"""
    try:
        from src.trading.smart_pair_selector import SmartPairSelector
        from src.core.exchange_mode_manager import ExchangeModeManager
        
        # Получаем баланс пользователя
        balance_data = get_balance()
        balance = balance_data.get('total_usdt', 0) if balance_data.get('success') else 0
        
        # Получаем роль пользователя
        user_role = current_user.role if hasattr(current_user, 'role') else 'user'
        
        # Создаем селектор пар
        exchange_manager = ExchangeModeManager()
        pair_selector = SmartPairSelector(exchange_manager, current_user.id, user_role)
        
        # Получаем рекомендованные пары
        recommended_pairs = asyncio.run(pair_selector.get_recommended_pairs(balance))
        
        # Форматируем данные для фронтенда
        pairs_data = []
        for pair in recommended_pairs:
            pairs_data.append({
                'symbol': pair.symbol,
                'smart_score': round(pair.smart_score, 3),
                'volatility': round(pair.volatility, 3),
                'liquidity': round(pair.liquidity, 3),
                'trend_strength': round(pair.trend_strength, 3),
                'market_regime': pair.market_regime,
                'recommendation': pair.recommendation,
                'risk_level': pair.risk_level,
                'rsi': round(pair.rsi, 2),
                'atr': round(pair.atr, 4)
            })
        
        # Получаем лимиты пользователя
        user_limits = pair_selector.get_user_limits()
        
        return jsonify({
                'success': True,
            'recommended_pairs': pairs_data,
            'user_limits': user_limits,
            'balance': balance
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/check-pair-addition', methods=['POST'])
@login_required_api
def api_check_pair_addition():
    """API для проверки возможности добавления пары"""
    try:
        data = request.get_json()
        new_pair = data.get('pair')
        current_pairs = data.get('current_pairs', [])
        
        if not new_pair:
            return jsonify({'success': False, 'error': 'Не указана пара'}), 400
        
        from src.trading.smart_pair_selector import SmartPairSelector
        from src.core.exchange_mode_manager import ExchangeModeManager
        
        # Получаем роль пользователя
        user_role = current_user.role if hasattr(current_user, 'role') else 'user'
        
        # Создаем селектор пар
        exchange_manager = ExchangeModeManager()
        pair_selector = SmartPairSelector(exchange_manager, current_user.id, user_role)
        
        # Проверяем возможность добавления
        can_add, message = pair_selector.can_add_pair(current_pairs, new_pair)
        
        return jsonify({
            'success': True,
            'can_add': can_add,
            'message': message,
            'user_limits': pair_selector.get_user_limits()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def get_system_metrics():
    """Получение системных метрик"""
    try:
        # CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        
        # Память
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_used_gb = round(memory.used / (1024**3), 2)
        memory_total_gb = round(memory.total / (1024**3), 2)
        
        # Диск
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
        disk_used_gb = round(disk.used / (1024**3), 2)
        disk_total_gb = round(disk.total / (1024**3), 2)
        
        # Процессы
        processes = len(psutil.pids())
        
        return {
            'cpu': {
                'percent': cpu_percent,
                'count': cpu_count
            },
            'memory': {
                'percent': memory_percent,
                'used_gb': memory_used_gb,
                'total_gb': memory_total_gb
            },
            'disk': {
                'percent': disk_percent,
                'used_gb': disk_used_gb,
                'total_gb': disk_total_gb
            },
            'system': {
                'processes': processes,
                'platform': sys.platform,
                'timestamp': datetime.now().isoformat()
            }
        }
    except Exception as e:
        return {
            'cpu': {'percent': 0, 'count': 0},
            'memory': {'percent': 0, 'used_gb': 0, 'total_gb': 0},
            'disk': {'percent': 0, 'used_gb': 0, 'total_gb': 0},
            'system': {'processes': 0, 'platform': 'unknown', 'timestamp': datetime.now().isoformat()}
        }

def get_trading_pairs():
    """Получение списка торговых пар"""
    default_pairs = [
        'ETH/USDT', 'XRP/USDT', 'SOL/USDT', 'BTC/USDT',
        'DOGE/USDT', 'ADA/USDT', 'SUI/USDT', 'BNB-USDT'
    ]
    
    # Читаем из файла если есть
    try:
        with open('data/trading_pairs.json', 'r', encoding='utf-8') as f:
            pairs_data = json.load(f)
            return pairs_data.get('pairs', default_pairs)
    except:
        return default_pairs

if __name__ == '__main__':
    print("🚀 Запуск Enhanced Dashboard...")
    print("🌐 Откройте браузер: http://localhost:5000")
    print("⏹️ Для остановки нажмите Ctrl+C")
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        use_reloader=False
    )





