#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Простая версия веб-интерфейса без предварительных учетных записей
Enhanced Trading System v3.0 Commercial
"""

import os
import sys
import json
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import datetime

# Добавляем пути для импорта модулей
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

# Создаем Flask приложение
app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-in-production'

# Настройка Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Пожалуйста, войдите в систему для доступа к этой странице.'
login_manager.login_message_category = 'info'

# Простой класс пользователя
class User:
    def __init__(self, user_id, username, email, role='user'):
        self.id = user_id
        self.username = username
        self.email = email
        self.role = role
        self.is_authenticated = True
        self.is_active = True
        self.is_anonymous = False
    
    def get_id(self):
        return str(self.id)

@login_manager.user_loader
def load_user(user_id):
    """Загрузка пользователя для Flask-Login"""
    try:
        conn = sqlite3.connect('data/database/auth_users.db')
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, email, role FROM users WHERE id = ?', (user_id,))
        user_data = cursor.fetchone()
        conn.close()
        
        if user_data:
            return User(user_data[0], user_data[1], user_data[2], user_data[3])
        return None
    except Exception as e:
        print(f"Ошибка загрузки пользователя: {e}")
        return None

def init_database():
    """Инициализация базы данных"""
    try:
        # Создаем директорию если не существует
        os.makedirs('data/database', exist_ok=True)
        
        conn = sqlite3.connect('data/database/auth_users.db')
        cursor = conn.cursor()
        
        # Создаем таблицу пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                api_keys TEXT DEFAULT '{}'
            )
        ''')
        
        # Добавляем колонку api_keys если она не существует (для существующих баз)
        try:
            cursor.execute('ALTER TABLE users ADD COLUMN api_keys TEXT DEFAULT "{}"')
            print("✅ Колонка api_keys добавлена")
        except sqlite3.OperationalError:
            # Колонка уже существует
            pass
        
        conn.commit()
        conn.close()
        print("✅ База данных инициализирована")
        
    except Exception as e:
        print(f"❌ Ошибка инициализации базы данных: {e}")

@app.route('/')
def index():
    """Главная страница"""
    if current_user.is_authenticated:
        return render_template('dashboard.html', user=current_user)
    return render_template('index.html')

@app.route('/bots')
@login_required
def bots():
    """Страница управления ботами"""
    return render_template('bots.html', user=current_user)

@app.route('/api-keys')
@login_required
def api_keys_page():
    """Страница управления API ключами"""
    # Список поддерживаемых бирж
    supported_exchanges = [
        'binance', 'okx', 'bybit', 'kucoin', 'gateio', 
        'huobi', 'bitget', 'mexc', 'bitfinex', 'kraken',
        'coinbase', 'cryptocom', 'bitmex', 'deribit', 'ftx'
    ]
    return render_template('api_keys.html', user=current_user, supported_exchanges=supported_exchanges)

@app.route('/api/api-keys', methods=['POST'])
@login_required
def save_api_keys():
    """API для сохранения API ключей"""
    try:
        data = request.get_json()
        exchange = data.get('exchange')
        api_key = data.get('api_key')
        secret = data.get('secret')
        passphrase = data.get('passphrase', '')
        mode = data.get('mode', 'sandbox')
        
        if not exchange or not api_key or not secret:
            return jsonify({'success': False, 'error': 'Не все поля заполнены'}), 400
        
        # Получаем текущие ключи пользователя
        conn = sqlite3.connect('data/database/auth_users.db')
        cursor = conn.cursor()
        cursor.execute('SELECT api_keys FROM users WHERE id = ?', (current_user.id,))
        result = cursor.fetchone()
        
        # Парсим существующие ключи
        if result and result[0]:
            api_keys = json.loads(result[0])
        else:
            api_keys = {}
        
        # Добавляем новые ключи
        api_keys[exchange] = {
            'api_key': api_key,
            'secret': secret,
            'passphrase': passphrase,
            'mode': mode
        }
        
        # Сохраняем в базу
        cursor.execute('UPDATE users SET api_keys = ? WHERE id = ?', (json.dumps(api_keys), current_user.id))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': f'API ключи для {exchange} сохранены'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/api-keys', methods=['GET'])
@login_required
def get_api_keys():
    """API для получения API ключей пользователя"""
    try:
        conn = sqlite3.connect('data/database/auth_users.db')
        cursor = conn.cursor()
        cursor.execute('SELECT api_keys FROM users WHERE id = ?', (current_user.id,))
        result = cursor.fetchone()
        conn.close()
        
        if result and result[0]:
            api_keys = json.loads(result[0])
            # Скрываем секретные ключи для безопасности
            safe_keys = {}
            for exchange, keys in api_keys.items():
                safe_keys[exchange] = {
                    'api_key': keys['api_key'][:8] + '...',
                    'mode': keys['mode'],
                    'has_secret': bool(keys.get('secret'))
                }
            return jsonify({'success': True, 'keys': safe_keys})
        else:
            return jsonify({'success': True, 'keys': {}})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Страница входа"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        try:
            conn = sqlite3.connect('data/database/auth_users.db')
            cursor = conn.cursor()
            cursor.execute('SELECT id, username, email, password_hash, role FROM users WHERE username = ?', (username,))
            user_data = cursor.fetchone()
            conn.close()
            
            if user_data and check_password_hash(user_data[3], password):
                user = User(user_data[0], user_data[1], user_data[2], user_data[4])
                login_user(user)
                flash('Успешный вход в систему!', 'success')
                return redirect(url_for('index'))
            else:
                flash('Неверное имя пользователя или пароль', 'error')
        except Exception as e:
            flash('Ошибка входа в систему', 'error')
            print(f"Ошибка входа: {e}")
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Страница регистрации"""
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        # Простая валидация
        if len(password) < 8:
            flash('Пароль должен содержать минимум 8 символов', 'error')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('Пароли не совпадают', 'error')
            return render_template('register.html')
        
        try:
            conn = sqlite3.connect('data/database/auth_users.db')
            cursor = conn.cursor()
            
            # Проверяем, существует ли пользователь
            cursor.execute('SELECT id FROM users WHERE username = ? OR email = ?', (username, email))
            if cursor.fetchone():
                flash('Пользователь с таким именем или email уже существует', 'error')
                conn.close()
                return render_template('register.html')
            
            # Создаем нового пользователя
            password_hash = generate_password_hash(password)
            cursor.execute('''
                INSERT INTO users (username, email, password_hash, role) 
                VALUES (?, ?, ?, ?)
            ''', (username, email, password_hash, 'user'))
            
            conn.commit()
            conn.close()
            
            flash('Регистрация успешна! Теперь вы можете войти в систему.', 'success')
            return redirect(url_for('login'))
            
        except Exception as e:
            flash('Ошибка регистрации', 'error')
            print(f"Ошибка регистрации: {e}")
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    """Выход из системы"""
    logout_user()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Дашборд"""
    return render_template('dashboard.html', user=current_user)

@app.route('/admin')
@login_required
def admin():
    """Админ панель"""
    if current_user.role not in ['admin', 'super_admin']:
        flash('У вас нет прав для доступа к этой странице', 'error')
        return redirect(url_for('index'))
    
    return render_template('admin.html', user=current_user)

@app.route('/api/users')
@login_required
def api_users():
    """API для получения списка пользователей"""
    if current_user.role not in ['admin', 'super_admin']:
        return jsonify({'error': 'Недостаточно прав'}), 403
    
    try:
        conn = sqlite3.connect('data/database/auth_users.db')
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, email, role, created_at FROM users ORDER BY created_at DESC')
        users = cursor.fetchall()
        conn.close()
        
        users_list = []
        for user in users:
            users_list.append({
                'id': user[0],
                'username': user[1],
                'email': user[2],
                'role': user[3],
                'created_at': user[4]
            })
        
        return jsonify({'users': users_list})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/promote/<int:user_id>')
@login_required
def promote_user(user_id):
    """Повышение пользователя до супер-админа"""
    if current_user.role != 'super_admin':
        return jsonify({'error': 'Недостаточно прав'}), 403
    
    try:
        conn = sqlite3.connect('data/database/auth_users.db')
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET role = ? WHERE id = ?', ('super_admin', user_id))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Пользователь повышен до супер-админа'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    init_database()
    print("🚀 Запуск простого веб-интерфейса...")
    print("🌐 Откройте браузер: http://localhost:5000")
    print("📝 Создайте учетную запись через регистрацию")
@app.route('/api/balance')
@login_required
def api_balance():
    """API для получения баланса с биржи (только USDT)"""
    try:
        print(f"🔍 Получение баланса для пользователя {current_user.id}")
        
        # Получаем API ключи пользователя
        conn = sqlite3.connect('data/database/auth_users.db')
        cursor = conn.cursor()
        cursor.execute('SELECT api_keys FROM users WHERE id = ?', (current_user.id,))
        result = cursor.fetchone()
        conn.close()
        
        if not result or not result[0]:
            print("❌ API ключи не найдены")
            return jsonify({'success': False, 'error': 'API ключи не найдены'}), 400
        
        api_keys = json.loads(result[0])
        print(f"🔑 Найдены API ключи: {list(api_keys.keys())}")
        
        # Получаем баланс с каждой биржи
        balances = []
        total_usdt = 0
        
        # Если нет API ключей, возвращаем пустой баланс
        if not api_keys:
            return jsonify({
                'success': True,
                'balance': [],
                'total_usdt': 0
            })
        
        for exchange_name, keys in api_keys.items():
            try:
                print(f"🔄 Подключение к {exchange_name}...")
                
                # Подключаемся к бирже через CCXT
                import ccxt
                
                if exchange_name == 'okx':
                    exchange = ccxt.okx({
                        'apiKey': keys['api_key'],
                        'secret': keys['secret'],
                        'password': keys['passphrase'],
                        'sandbox': keys['mode'] == 'sandbox'
                    })
                elif exchange_name == 'binance':
                    exchange = ccxt.binance({
                        'apiKey': keys['api_key'],
                        'secret': keys['secret'],
                        'sandbox': keys['mode'] == 'sandbox'
                    })
                else:
                    print(f"❌ Биржа {exchange_name} не поддерживается")
                    continue
                
                print(f"📊 Получение баланса с {exchange_name}...")
                balance = exchange.fetch_balance()
                print(f"✅ Баланс получен: {balance}")
                
                # Считаем USDT баланс
                usdt_balance = 0
                if 'USDT' in balance and balance['USDT']:
                    usdt_free = float(balance['USDT'].get('free', 0) or 0)
                    usdt_used = float(balance['USDT'].get('used', 0) or 0)
                    usdt_balance = usdt_free + usdt_used
                    print(f"💰 USDT: {usdt_balance}")
                
                total_usdt += usdt_balance
                
                balances.append({
                    'exchange': exchange_name,
                    'balance': {'USDT': {'free': 1000, 'used': 0}},
                    'usdt_equivalent': usdt_balance
                })
                
            except Exception as e:
                print(f"❌ Ошибка получения баланса с {exchange_name}: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        print(f"💵 Общий USDT баланс: {total_usdt}")
        
        # Возвращаем только USDT эквивалент
        return jsonify({
            'success': True,
            'balance': balances,
            'total_usdt': total_usdt
        })
        
    except Exception as e:
        print(f"❌ Общая ошибка API баланса: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/bots/status')
@login_required
def api_bots_status():
    """API для получения статуса ботов"""
    try:
        # Читаем статус ботов из файла
        try:
            with open('data/bot_status.json', 'r', encoding='utf-8') as f:
                bots_status = json.load(f)
        except:
            bots_status = {}
        
        return jsonify({
            'success': True,
            'bots': bots_status
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/bots/<bot_id>/start', methods=['POST'])
@login_required
def api_start_bot(bot_id):
    """API для запуска бота"""
    try:
        # Простая заглушка для запуска бота
        return jsonify({
            'success': True,
            'message': f'Бот {bot_id} запущен',
            'bot_status': {'status': 'running'}
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/bots/<bot_id>/stop', methods=['POST'])
@login_required
def api_stop_bot(bot_id):
    """API для остановки бота"""
    try:
        # Простая заглушка для остановки бота
        return jsonify({
            'success': True,
            'message': f'Бот {bot_id} остановлен',
            'bot_status': {'status': 'stopped'}
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/bots/<bot_id>/details')
@login_required
def api_bot_details(bot_id):
    """API для получения детальной информации о боте"""
    try:
        # Простая заглушка для деталей бота
        return jsonify({
            'success': True,
            'bot_details': {
                'id': bot_id,
                'name': f'Бот {bot_id}',
                'status': 'running',
                'bot_type': 'grid',
                'mode': 'demo',
                'trading_pairs': ['BTC/USDT', 'ETH/USDT'],
                'started_at': '2025-09-21T20:40:00.000000',
                'runtime_info': {'uptime': '5 минут'},
                'system_metrics': {'cpu_usage': 15, 'memory_usage': 25},
                'grid_info': {'total_orders': 12}
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)



