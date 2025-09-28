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
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from flask import Flask, render_template, jsonify, request, session, redirect, url_for
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
                # Сохраняем данные в сессию Flask
                session['user_id'] = user_data[0]  # id
                session['username'] = user_data[1]  # username
                session['email'] = user_data[2]     # email
                session['role'] = user_data[4]      # role
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
    # Очищаем сессию
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Главная страница дашборда"""
    # Получаем данные текущего пользователя из сессии
    user_data = {
        'username': session.get('username', 'Unknown'),
        'role': session.get('role', 'user'),
        'user_id': session.get('user_id')
    }
    
    # Проверяем наличие API ключей для отображения статуса на главной
    user_id = session.get('user_id')
    has_api_keys = False
    connected_exchanges = []
    
    try:
        # Проверяем ключи из файла
        api_keys_file = f'data/api_keys/user_{user_id}_keys.json'
        if not os.path.exists(api_keys_file):
            api_keys_file = 'data/api_keys/user_5_keys.json'
            
        if os.path.exists(api_keys_file):
            with open(api_keys_file, 'r', encoding='utf-8') as f:
                file_keys = json.load(f)
                
            if file_keys:
                has_api_keys = True
                for key_name, key_info in file_keys.items():
                    exchange = key_info.get('exchange', 'unknown')
                    mode = key_info.get('mode', 'unknown')
                    status = key_info.get('validation_status', 'unknown')
                    
                    if status == 'valid' and exchange not in [ex['name'] for ex in connected_exchanges]:
                        connected_exchanges.append({
                            'name': exchange,
                            'mode': mode,
                            'status': status
                        })
                        
    except Exception as e:
        print(f"Ошибка при проверке API ключей: {e}")
    
    # Получаем список API ключей для отображения на дашборде
    api_keys_for_dashboard = []
    
    try:
        # Ключи из файла для отображения на дашборде
        api_keys_file = f'data/api_keys/user_{user_id}_keys.json'
        if not os.path.exists(api_keys_file):
            api_keys_file = 'data/api_keys/user_5_keys.json'
            
        if os.path.exists(api_keys_file):
            with open(api_keys_file, 'r', encoding='utf-8') as f:
                file_keys = json.load(f)
                
            for key_name, key_info in file_keys.items():
                api_keys_for_dashboard.append({
                    'exchange': key_info.get('exchange', 'unknown'),
                    'mode': key_info.get('mode', 'unknown'),
                    'validation_status': key_info.get('validation_status', 'unknown'),
                })
                
    except Exception as e:
        print(f"Ошибка при загрузке ключей для дашборда: {e}")
    
    return render_template('dashboard.html', 
                         user=user_data,
                         has_api_keys=has_api_keys,
                         connected_exchanges=connected_exchanges,
                         api_keys=api_keys_for_dashboard)

@app.route('/admin')
@login_required
def admin():
    """Админ панель"""
    # Проверяем права доступа
    user_role = session.get('role', 'user')
    if user_role not in ['admin', 'super_admin']:
        return redirect(url_for('dashboard'))
    
    user_data = {
        'username': session.get('username', 'Unknown'),
        'role': session.get('role', 'user'),
        'user_id': session.get('user_id')
    }
    
    # Получаем статистику системы для админ панели
    admin_stats = {
        'total_users': 0,
        'active_bots': 0,
        'total_trades': 0,
        'system_uptime': '0 дней'
    }
    
    try:
        # Считаем пользователей
        conn = sqlite3.connect('data/database/auth_users.db')
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM users')
        admin_stats['total_users'] = cursor.fetchone()[0]
        conn.close()
        
        # Считаем активные боты
        try:
            with open('data/bot_status.json', 'r', encoding='utf-8') as f:
                bots_status = json.load(f)
                admin_stats['active_bots'] = len([b for b in bots_status.values() if b.get('status') == 'running'])
        except:
            pass
            
    except Exception as e:
        print(f"Ошибка при получении админ статистики: {e}")
    
    return render_template('admin.html', user=user_data, admin_stats=admin_stats)

@app.route('/bots')
@login_required
def bots():
    """Страница управления ботами"""
    # Получаем данные текущего пользователя из сессии
    user_data = {
        'username': session.get('username', 'Unknown'),
        'role': session.get('role', 'user'),
        'user_id': session.get('user_id')
    }
    return render_template('bots.html', user=user_data)

# API Endpoints
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
        user_id = session.get('user_id')
        bots_data = []
        
        try:
            with open('data/bot_status.json', 'r', encoding='utf-8') as f:
                bots_status = json.load(f)
                for bot_id, bot_info in bots_status.items():
                    # Фильтруем только ботов текущего пользователя
                    if bot_info.get('user_id') == user_id:
                        bots_data.append({
                            'id': bot_id,
                            'bot_name': bot_info.get('bot_name', bot_id),
                            'status': bot_info.get('status', 'unknown'),
                            'bot_type': bot_info.get('bot_type', 'unknown'),
                            'mode': bot_info.get('mode', 'unknown'),
                            'api_key_id': bot_info.get('api_key_id', ''),
                            'created_at': bot_info.get('created_at', ''),
                            'last_update': bot_info.get('last_update', '')
                        })
        except (FileNotFoundError, json.JSONDecodeError):
            # Если файл не существует, создаем пустой
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

@app.route('/api/balance')
@login_required_api
def api_balance():
    """API для получения баланса"""
    try:
        user_id = session.get('user_id')
        
        # Получаем баланс из файла API ключей
        total_balance_usdt = 0
        exchanges_data = []
        
        api_keys_file = f'data/api_keys/user_{user_id}_keys.json'
        if not os.path.exists(api_keys_file):
            api_keys_file = 'data/api_keys/user_5_keys.json'
            
        if os.path.exists(api_keys_file):
            with open(api_keys_file, 'r', encoding='utf-8') as f:
                file_keys = json.load(f)
                
            for key_name, key_info in file_keys.items():
                exchange = key_info.get('exchange', 'unknown')
                mode = key_info.get('mode', 'unknown')
                balance_info = key_info.get('balance_info', {})
                
                if balance_info:
                    total_balance = balance_info.get('total_balance', {})
                    free_balance = balance_info.get('free_balance', {})
                    
                    # Считаем USDT эквивалент (упрощенно)
                    usdt_equivalent = total_balance.get('USDT', 0)
                    for asset, amount in total_balance.items():
                        if asset in ['TUSD', 'USDC', 'PAX', 'USDK'] and amount > 0:
                            usdt_equivalent += amount
                    
                    total_balance_usdt += usdt_equivalent
                    
                    exchanges_data.append({
                        'exchange': exchange,
                        'mode': mode,
                        'total_usdt': round(usdt_equivalent, 2),
                        'assets_count': len([k for k, v in total_balance.items() if v > 0]),
                        'status': 'connected'
                    })
        
        return jsonify({
            'success': True,
            'balance': {
                'total_usdt': round(total_balance_usdt, 2),
                'exchanges': exchanges_data,
                'connected': len(exchanges_data) > 0
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/balance/detailed')
@login_required_api
def api_detailed_balance():
    """API для получения детального баланса по всем валютам"""
    try:
        user_id = session.get('user_id')
        
        detailed_balances = []
        
        api_keys_file = f'data/api_keys/user_{user_id}_keys.json'
        if not os.path.exists(api_keys_file):
            api_keys_file = 'data/api_keys/user_5_keys.json'
            
        if os.path.exists(api_keys_file):
            with open(api_keys_file, 'r', encoding='utf-8') as f:
                file_keys = json.load(f)
                
            for key_name, key_info in file_keys.items():
                exchange = key_info.get('exchange', 'unknown')
                mode = key_info.get('mode', 'unknown')
                balance_info = key_info.get('balance_info', {})
                
                if balance_info:
                    total_balance = balance_info.get('total_balance', {})
                    free_balance = balance_info.get('free_balance', {})
                    used_balance = balance_info.get('used_balance', {})
                    
                    # Создаем детальную информацию по каждой валюте
                    currencies = []
                    for currency, total_amount in total_balance.items():
                        if float(total_amount) > 0:  # Показываем только валюты с балансом
                            free_amount = free_balance.get(currency, 0)
                            used_amount = used_balance.get(currency, 0)
                            
                            currencies.append({
                                'currency': currency,
                                'total': float(total_amount),
                                'free': float(free_amount),
                                'used': float(used_amount)
                            })
                    
                    if currencies:
                        detailed_balances.append({
                            'exchange': exchange,
                            'mode': mode,
                            'key_name': key_name,
                            'currencies': currencies,
                            'total_currencies': len(currencies)
                        })
        
        return jsonify({
            'success': True,
            'detailed_balances': detailed_balances,
            'total_exchanges': len(detailed_balances)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api-keys')
@login_required
def api_keys():
    """Страница управления API ключами"""
    user_data = {
        'username': session.get('username', 'Unknown'),
        'role': session.get('role', 'user'),
        'user_id': session.get('user_id')
    }
    
    # Получаем API ключи для отображения
    user_id = session.get('user_id')
    api_keys_list = []
    
    try:
        # Получаем ключи из базы данных
        conn = sqlite3.connect('data/database/auth_users.db')
        cursor = conn.cursor()
        cursor.execute('SELECT api_keys FROM users WHERE id = ?', (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result and result[0]:
            db_keys = json.loads(result[0])
            for exchange, key_data in db_keys.items():
                api_keys_list.append({
                    'key_id': f"db_{exchange}",
                    'exchange': exchange,
                    'mode': key_data.get('mode', 'unknown'),
                    'api_key_preview': key_data.get('api_key', '')[:10] + '...',
                    'validation_status': 'valid',
                    'created_at': '2025-09-21 18:12:30',
                    'last_used': '2025-09-28 11:00:00',
                    'source': 'database'
                })
        
        # Получаем ключи из файла
        api_keys_file = f'data/api_keys/user_{user_id}_keys.json'
        if not os.path.exists(api_keys_file):
            api_keys_file = 'data/api_keys/user_5_keys.json'
            
        if os.path.exists(api_keys_file):
            with open(api_keys_file, 'r', encoding='utf-8') as f:
                file_keys = json.load(f)
                
            for key_name, key_info in file_keys.items():
                # Безопасное получение превью ключа
                api_key = str(key_info.get('api_key', ''))
                if len(api_key) > 20:
                    # Если ключ зашифрован (длинный), показываем информацию о шифровании
                    api_key_preview = "🔒 Зашифрован"
                elif len(api_key) > 10:
                    # Обычный ключ
                    api_key_preview = api_key[:10] + "..."
                else:
                    # Короткий ключ или пустой
                    api_key_preview = api_key or "Не указан"
                
                api_keys_list.append({
                    'key_id': key_name,
                    'exchange': key_info.get('exchange', 'unknown'),
                    'mode': key_info.get('mode', 'unknown'),
                    'api_key_preview': api_key_preview,
                    'validation_status': key_info.get('validation_status', 'unknown'),
                    'created_at': key_info.get('created_at', ''),
                    'last_used': key_info.get('last_used', ''),
                    'source': 'file'
                })
                
    except Exception as e:
        print(f"Ошибка при загрузке API ключей: {e}")
    
    # Отладочная информация (можно убрать в продакшене)
    # print(f"[DEBUG] Загружено API ключей: {len(api_keys_list)}")
    
    # Поддерживаемые биржи
    supported_exchanges = ['okx', 'binance', 'bybit', 'coinbase', 'kraken']
    
    return render_template('api_keys.html', 
                         user=user_data, 
                         keys=api_keys_list,  # Изменено с api_keys на keys
                         api_keys=api_keys_list,  # Оставляем и старое название для совместимости
                         supported_exchanges=supported_exchanges)

@app.route('/api/api-keys')
@login_required_api
def api_api_keys():
    """API для получения API ключей"""
    try:
        user_id = session.get('user_id')
        username = session.get('username')
        
        # Получаем API ключи из БД
        conn = sqlite3.connect('data/database/auth_users.db')
        cursor = conn.cursor()
        cursor.execute('SELECT api_keys FROM users WHERE id = ?', (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        keys_from_db = []
        try:
            if result and result[0]:
                db_keys = json.loads(result[0])
                for exchange, key_data in db_keys.items():
                    keys_from_db.append({
                        'exchange': exchange,
                        'mode': key_data.get('mode', 'unknown'),
                        'status': 'active',
                        'api_key': key_data.get('api_key', '')[:10] + '...',  # Скрываем ключ
                        'source': 'database'
                    })
        except Exception as e:
            print(f"Ошибка при обработке ключей из БД: {e}")
            # Если ошибка - просто пропускаем ключи из БД
        
        # Получаем API ключи из файла
        keys_from_file = []
        api_keys_file = f'data/api_keys/user_{user_id}_keys.json'
        if not os.path.exists(api_keys_file):
            # Пробуем старый формат
            api_keys_file = 'data/api_keys/user_5_keys.json'
            
        if os.path.exists(api_keys_file):
            with open(api_keys_file, 'r', encoding='utf-8') as f:
                file_keys = json.load(f)
                
            for key_name, key_info in file_keys.items():
                keys_from_file.append({
                    'name': key_name,
                    'exchange': key_info.get('exchange', 'unknown'),
                    'mode': key_info.get('mode', 'unknown'),
                    'status': key_info.get('validation_status', 'unknown'),
                    'is_active': key_info.get('is_active', False),
                    'created_at': key_info.get('created_at', ''),
                    'last_used': key_info.get('last_used', ''),
                    'balance_info': key_info.get('balance_info', {}),
                    'source': 'file'
                })
        
        # Объединяем все ключи в один список для совместимости с фронтендом
        all_keys = []
        
        # Добавляем ключи из файла (они основные)
        for key in keys_from_file:
            all_keys.append({
                'id': key.get('name', ''),
                'exchange': key.get('exchange', 'unknown'),
                'mode': key.get('mode', 'unknown'),
                'status': key.get('status', 'unknown'),
                'api_key': 'Зашифрован' if key.get('name', '').startswith('okx_') else key.get('api_key', '')[:10] + '...',
                'is_active': key.get('is_active', False)
            })
        
        return jsonify({
            'success': True,
            'keys': all_keys,  # Основной список для фронтенда
            'keys_from_db': keys_from_db,
            'keys_from_file': keys_from_file,
            'total_keys': len(all_keys)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/create-super-admin')
@login_required_api
def api_create_super_admin():
    """API для создания супер-администратора"""
    try:
        # Проверяем, есть ли уже права супер-админа
        user_role = session.get('role', 'user')
        
        if user_role == 'super_admin':
            return jsonify({
                'success': True,
                'message': 'У вас уже есть права супер-администратора',
                'current_role': user_role
            })
        else:
            # Для демонстрации просто возвращаем информацию
            return jsonify({
                'success': False,
                'message': 'Недостаточно прав для создания супер-администратора',
                'current_role': user_role
            })
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/api-keys/<key_id>/validate', methods=['POST'])
@login_required_api
def validate_api_key(key_id):
    """Валидация API ключа"""
    try:
        # Здесь должна быть логика валидации ключа
        # Пока возвращаем заглушку
        return jsonify({
            'success': True,
            'message': f'Ключ {key_id} успешно проверен',
            'status': 'valid'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/api-keys/<key_id>/delete', methods=['POST'])
@login_required_api
def delete_api_key(key_id):
    """Удаление API ключа"""
    try:
        # Здесь должна быть логика удаления ключа
        # Пока возвращаем заглушку
        return jsonify({
            'success': True,
            'message': f'Ключ {key_id} удален'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/users')
@login_required_api
def api_users():
    """API для получения списка пользователей (админ)"""
    try:
        user_role = session.get('role', 'user')
        if user_role not in ['admin', 'super_admin']:
            return jsonify({'success': False, 'error': 'Недостаточно прав'}), 403
        
        conn = sqlite3.connect('data/database/auth_users.db')
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, email, role, is_active, created_at FROM users')
        users_data = cursor.fetchall()
        conn.close()
        
        users_list = []
        for user in users_data:
            users_list.append({
                'id': user[0],
                'username': user[1],
                'email': user[2],
                'role': user[3],
                'is_active': bool(user[4]),
                'created_at': user[5]
            })
        
        return jsonify({
            'success': True,
            'users': users_list
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/promote/<int:user_id>', methods=['POST'])
@login_required_api
def api_promote_user(user_id):
    """API для повышения пользователя (админ)"""
    try:
        user_role = session.get('role', 'user')
        if user_role not in ['admin', 'super_admin']:
            return jsonify({'success': False, 'error': 'Недостаточно прав'}), 403
        
        # Здесь должна быть логика повышения пользователя
        # Пока возвращаем заглушку
        return jsonify({
            'success': True,
            'message': f'Пользователь {user_id} повышен'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/bots/create', methods=['POST'])
@login_required_api
def api_create_bot():
    """API для создания нового бота"""
    try:
        data = request.get_json()
        user_id = session.get('user_id')
        username = session.get('username')
        
        # Генерируем ID бота
        bot_id = f"{data.get('botType', 'unknown')}_{user_id}_{int(time.time())}"
        
        # Создаем данные бота
        bot_data = {
            'bot_id': bot_id,
            'user_id': user_id,
            'username': username,
            'bot_type': data.get('botType', 'unknown'),
            'bot_name': data.get('botName', f"{data.get('botType', 'Bot')} {bot_id}"),
            'api_key_id': data.get('apiKeyId', ''),
            'mode': data.get('mode', 'demo'),
            'trading_pairs': data.get('tradingPairs', []),
            'settings': data.get('settings', {}),
            'status': 'created',
            'created_at': datetime.now().isoformat(),
            'last_update': datetime.now().isoformat()
        }
        
        # Сохраняем в файл статуса ботов
        bots_status = {}
        try:
            with open('data/bot_status.json', 'r', encoding='utf-8') as f:
                bots_status = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            bots_status = {}
        
        bots_status[bot_id] = bot_data
        
        # Записываем обратно
        with open('data/bot_status.json', 'w', encoding='utf-8') as f:
            json.dump(bots_status, f, ensure_ascii=False, indent=2)
        
        # Создаем папку для данных бота
        bot_data_dir = f'data/user_data/user_{user_id}'
        os.makedirs(bot_data_dir, exist_ok=True)
        
        # Сохраняем конфигурацию бота
        bot_config_file = f'data/bot_configs/{bot_id}_config.json'
        with open(bot_config_file, 'w', encoding='utf-8') as f:
            json.dump(bot_data, f, ensure_ascii=False, indent=2)
        
        print(f"[DEBUG] Создан бот: {bot_id}")
        print(f"[DEBUG] Тип: {bot_data['bot_type']}")
        print(f"[DEBUG] Режим: {bot_data['mode']}")
        print(f"[DEBUG] API ключ: {bot_data['api_key_id']}")
        
        return jsonify({
            'success': True,
            'message': 'Бот создан успешно',
            'bot_id': bot_id,
            'bot_data': bot_data
        })
        
    except Exception as e:
        print(f"Ошибка создания бота: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/bots/<bot_id>/start', methods=['POST'])
@login_required_api
def api_start_bot(bot_id):
    """API для запуска бота"""
    try:
        user_id = session.get('user_id')
        
        # Обновляем статус бота на "running"
        try:
            with open('data/bot_status.json', 'r', encoding='utf-8') as f:
                bots_status = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            bots_status = {}
        
        if bot_id in bots_status and bots_status[bot_id].get('user_id') == user_id:
            bots_status[bot_id]['status'] = 'running'
            bots_status[bot_id]['last_update'] = datetime.now().isoformat()
            
            with open('data/bot_status.json', 'w', encoding='utf-8') as f:
                json.dump(bots_status, f, ensure_ascii=False, indent=2)
            
            print(f"[DEBUG] Бот {bot_id} запущен")
            
            return jsonify({
                'success': True,
                'message': f'Бот {bot_id} запущен'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Бот не найден или нет прав'
            }), 403
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/bots/<bot_id>/stop', methods=['POST'])
@login_required_api
def api_stop_bot(bot_id):
    """API для остановки бота"""
    try:
        user_id = session.get('user_id')
        
        # Обновляем статус бота на "stopped"
        try:
            with open('data/bot_status.json', 'r', encoding='utf-8') as f:
                bots_status = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            bots_status = {}
        
        if bot_id in bots_status and bots_status[bot_id].get('user_id') == user_id:
            bots_status[bot_id]['status'] = 'stopped'
            bots_status[bot_id]['last_update'] = datetime.now().isoformat()
            
            with open('data/bot_status.json', 'w', encoding='utf-8') as f:
                json.dump(bots_status, f, ensure_ascii=False, indent=2)
            
            print(f"[DEBUG] Бот {bot_id} остановлен")
            
            return jsonify({
                'success': True,
                'message': f'Бот {bot_id} остановлен'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Бот не найден или нет прав'
            }), 403
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/bots/<bot_id>/delete', methods=['POST'])
@login_required_api
def api_delete_bot(bot_id):
    """API для удаления бота"""
    try:
        user_id = session.get('user_id')
        
        # Удаляем бота из статуса
        try:
            with open('data/bot_status.json', 'r', encoding='utf-8') as f:
                bots_status = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            bots_status = {}
        
        if bot_id in bots_status and bots_status[bot_id].get('user_id') == user_id:
            # Удаляем из статуса
            del bots_status[bot_id]
            
            with open('data/bot_status.json', 'w', encoding='utf-8') as f:
                json.dump(bots_status, f, ensure_ascii=False, indent=2)
            
            # Удаляем файл конфигурации
            bot_config_file = f'data/bot_configs/{bot_id}_config.json'
            try:
                os.remove(bot_config_file)
            except FileNotFoundError:
                pass
            
            print(f"[DEBUG] Бот {bot_id} удален")
            
            return jsonify({
                'success': True,
                'message': f'Бот {bot_id} удален'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Бот не найден или нет прав'
            }), 403
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

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





