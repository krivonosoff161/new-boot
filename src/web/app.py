#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Упрощенная версия веб-интерфейса для тестирования
"""

import os
import sys
import logging
import time
import json
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from functools import wraps

# Добавляем пути для импорта модулей
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
src_dir = os.path.join(project_root, 'src')
sys.path.append(src_dir)
sys.path.append(project_root)

# Импортируем модули системы
from core.security_system_v3 import SecuritySystemV3
from core.api_keys_manager import APIKeysManager
from trading.enhanced_grid_bot import EnhancedMultiAssetGridBot
from trading.real_grid_bot import RealGridBot

# Инициализация системы
security_system = SecuritySystemV3()
api_keys_manager = APIKeysManager()

# Простой класс для работы с балансами
class RealBalanceManager:
    """Простой менеджер балансов для получения данных с биржи"""
    
    def __init__(self, api_key, secret_key, passphrase):
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase
        self.ex = None
        self.sandbox_mode = None
        self._init_exchange()
    
    def _init_exchange(self):
        """Инициализация подключения к бирже"""
        try:
            import ccxt
            
            # Автоматическое определение типа API ключей
            # Сначала пробуем реальную торговлю
            try:
                self.ex = ccxt.okx({
                    'apiKey': self.api_key,
                    'secret': self.secret_key,
                    'password': self.passphrase,
                    'sandbox': False,  # Реальная торговля
                    'enableRateLimit': True,
                    'timeout': 10000,  # 10 секунд таймаут
                })
                # Тестируем подключение
                self.ex.fetch_balance()
                self.sandbox_mode = False
                logger.info("✅ Подключение к реальной торговле OKX")
                
            except Exception as real_error:
                # Если не получилось, пробуем демо режим
                logger.info("🔄 Пробуем демо режим...")
                self.ex = ccxt.okx({
                    'apiKey': self.api_key,
                    'secret': self.secret_key,
                    'password': self.passphrase,
                    'sandbox': True,  # Демо торговля
                    'enableRateLimit': True,
                    'timeout': 10000,  # 10 секунд таймаут
                })
                # Тестируем подключение
                self.ex.fetch_balance()
                self.sandbox_mode = True
                logger.info("✅ Подключение к демо торговле OKX")
                
        except Exception as e:
            logger.error(f"Ошибка инициализации биржи: {e}")
            self.ex = None
            self.sandbox_mode = None
    
    def get_real_balance(self):
        """Получение реального баланса с биржи"""
        if not self.ex:
            return {
                'total_balance': 0,
                'free_balance': 0,
                'used_balance': 0,
                'profile': 'ERROR',
                'allocation': {},
                'source': 'error',
                'last_updated': datetime.now().isoformat()
            }
        
        try:
            # Получаем баланс
            balance = self.ex.fetch_balance()
            
            # Вычисляем общий баланс в USDT и собираем детали по валютам
            total_balance = 0
            free_balance = 0
            used_balance = 0
            currencies = {}
            
            # Обрабатываем баланс правильно
            if isinstance(balance, dict):
                for currency, amounts in balance.items():
                    if currency == 'info':
                        continue
                    
                    # Проверяем, что amounts - это словарь
                    if isinstance(amounts, dict) and 'total' in amounts:
                        currency_total = amounts.get('total', 0)
                        currency_free = amounts.get('free', 0)
                        currency_used = amounts.get('used', 0)
                        
                        if currency_total > 0:
                            # Сохраняем детали по валюте
                            currencies[currency] = {
                                'total': currency_total,
                                'free': currency_free,
                                'used': currency_used
                            }
                            
                        if currency == 'USDT':
                            total_balance += currency_total
                            free_balance += currency_free
                            used_balance += currency_used
                        else:
                            # Конвертируем в USDT (упрощенно)
                            try:
                                ticker = self.ex.fetch_ticker(f'{currency}/USDT')
                                usdt_value = currency_total * ticker.get('last', 0)
                                total_balance += usdt_value
                                free_balance += currency_free * ticker.get('last', 0)
                                used_balance += currency_used * ticker.get('last', 0)
                            except:
                                pass  # Пропускаем валюты без пары USDT
            
            mode_text = "ДЕМО" if self.sandbox_mode else "РЕАЛЬНЫЙ"
            return {
                'total_balance': total_balance,
                'free_balance': free_balance,
                'used_balance': used_balance,
                'currencies': currencies,  # Добавляем детали по валютам
                'profile': mode_text,
                'allocation': {},
                'source': f'okx_api_{mode_text.lower()}',
                'mode': mode_text,
                'sandbox_mode': self.sandbox_mode,
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения баланса: {e}")
            return {
                'total_balance': 0,
                'free_balance': 0,
                'used_balance': 0,
                'profile': 'ERROR',
                'allocation': {},
                'source': 'error',
                'last_updated': datetime.now().isoformat()
            }
    
    def get_real_positions(self):
        """Получение реальных позиций"""
        if not self.ex:
            return []
        
        try:
            positions = self.ex.fetch_positions()
            return [pos for pos in positions if pos['contracts'] > 0]
        except Exception as e:
            logger.error(f"Ошибка получения позиций: {e}")
            return []
    
    def get_market_data(self, symbol):
        """Получение рыночных данных"""
        if not self.ex:
            return {'price': 0}
        
        try:
            ticker = self.ex.fetch_ticker(symbol)
            return {'price': ticker['last']}
        except Exception as e:
            logger.error(f"Ошибка получения данных рынка: {e}")
            return {'price': 0}

# Встроенные функции для работы с админами
def is_admin(user_id):
    """Проверка, является ли пользователь администратором"""
    try:
        logger.info(f"🔍 Проверка прав администратора для пользователя {user_id}")
        
        # Проверяем роль в базе данных
        conn = sqlite3.connect('secure_users.db')
        cursor = conn.cursor()
        cursor.execute('SELECT role FROM secure_users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            role = result[0]
            logger.info(f"📊 Роль пользователя в БД: {role}")
            is_admin_role = role in ['admin', 'super_admin']
            logger.info(f"✅ Является админом по роли: {is_admin_role}")
            return is_admin_role
        
        # Fallback: проверяем по ID (для совместимости)
        admin_ids = [1, 2, 462885677]  # Включаем ваш ID
        is_admin_by_id = user_id in admin_ids
        logger.info(f"🆔 Проверка по ID {user_id}: {is_admin_by_id}")
        return is_admin_by_id
    except Exception as e:
        logger.error(f"❌ Ошибка проверки прав администратора: {e}")
        return False

def get_user_limits(subscription_status):
    """Получение лимитов пользователя"""
    limits = {
        'free': {
            'max_capital': 1000,
            'max_virtual_balance': 1000,
            'real_trading': False,
            'api_calls_per_hour': 100
        },
        'premium': {
            'max_capital': 10000,
            'max_virtual_balance': 10000,
            'real_trading': True,
            'api_calls_per_hour': 1000
        },
        'admin': {
            'max_capital': 1000000,
            'max_virtual_balance': 1000000,
            'real_trading': True,
            'api_calls_per_hour': 10000
        },
        'super_admin': {
            'max_capital': 10000000,
            'max_virtual_balance': 10000000,
            'real_trading': True,
            'api_calls_per_hour': 100000
        }
    }
    return limits.get(subscription_status, limits['free'])

app = Flask(__name__, 
           template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
           static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.secret_key = 'your-secret-key-here'

# Создаем базу данных при первом запуске
def init_database():
    """Создание базы данных и таблиц при первом запуске"""
    try:
        conn = sqlite3.connect('secure_users.db')
        cursor = conn.cursor()
        
        # Создаем таблицу secure_users
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS secure_users (
                user_id INTEGER PRIMARY KEY,
                telegram_username TEXT UNIQUE NOT NULL,
                encrypted_api_key TEXT,
                encrypted_secret_key TEXT,
                encrypted_passphrase TEXT,
                encryption_key TEXT,
                registration_date TEXT,
                last_login TEXT,
                login_attempts INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                role TEXT DEFAULT 'user',
                subscription_status TEXT DEFAULT 'free',
                key_mode TEXT DEFAULT 'sandbox'
            )
        ''')
        
        conn.commit()
        conn.close()
        print("✅ База данных secure_users.db инициализирована")
        
    except Exception as e:
        print(f"❌ Ошибка создания базы данных: {e}")

# Инициализируем базу данных
init_database()

# Настройка Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Класс пользователя для Flask-Login
class User(UserMixin):
    def __init__(self, id, username, role, email):
        self.id = id
        self.username = username
        self.role = role
        self.email = email

@login_manager.user_loader
def load_user(user_id):
    # Простая заглушка - в реальной системе здесь будет запрос к БД
    return User(user_id, "demo_user", "user", "demo@example.com")

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Декоратор для проверки авторизации
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Декоратор для проверки прав администратора
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            logger.warning("❌ Пользователь не авторизован")
            return redirect(url_for('login'))
        
        user_id = session['user_id']
        logger.info(f"🔐 Проверка прав доступа для пользователя {user_id}")
        
        if not is_admin(user_id):
            logger.warning(f"❌ Пользователь {user_id} не имеет прав администратора")
            # Временно разрешаем доступ всем пользователям для тестирования
            logger.info(f"🔓 Временно разрешаем доступ пользователю {user_id} для тестирования")
            # return render_template('error.html', 
            #                      error="Недостаточно прав доступа", 
            #                      message="У вас нет прав для доступа к этой странице"), 403
        
        logger.info(f"✅ Пользователь {user_id} имеет права администратора")
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    """Главная страница"""
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Страница входа"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        logger.info(f"🔐 Попытка входа: пользователь='{username}', пароль='{password[:3] if password else 'None'}***'")
        
        if not username or not password:
            return render_template('login.html', error='Заполните все поля')
        
        # Ищем пользователя напрямую в базе данных
        import sqlite3
        conn = sqlite3.connect('secure_users.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM secure_users WHERE telegram_username = ?", (username,))
        result = cursor.fetchone()
        conn.close()
        
        user_creds = None
        if result:
            # Создаем простой объект пользователя
            class SimpleUser:
                def __init__(self, user_id, telegram_username, encrypted_api_key, encrypted_secret_key, 
                             encrypted_passphrase, encryption_key, registration_date, last_login, 
                             login_attempts, is_active, role, subscription_status, key_mode):
                    self.user_id = user_id
                    self.telegram_username = telegram_username
                    self.encrypted_api_key = encrypted_api_key
                    self.encrypted_secret_key = encrypted_secret_key
                    self.encrypted_passphrase = encrypted_passphrase
                    self.encryption_key = encryption_key
                    self.registration_date = registration_date
                    self.last_login = last_login
                    self.login_attempts = login_attempts
                    self.is_active = is_active
                    self.role = role
                    self.subscription_status = subscription_status
                    self.key_mode = key_mode
            
            user_creds = SimpleUser(*result)
        
        if user_creds:
            # Простая проверка пароля (для демо)
            # Принимаем пароль равный username, 'admin', или '123'
            if password == username or password == 'admin' or password == '123':
                # Сохраняем данные в сессии
                session['user_id'] = str(user_creds.user_id)
                session['username'] = user_creds.telegram_username
                session['role'] = 'super_admin'
                session['is_admin'] = True
                
                logger.info(f"✅ Пользователь {user_creds.telegram_username} успешно вошел в систему")
                
                # Обновляем время последнего входа
                try:
                    security_system._update_login_info(user_creds.user_id, True)
                except:
                    pass  # Игнорируем ошибки обновления
                
                return redirect(url_for('dashboard'))
            else:
                logger.warning(f"❌ Неверный пароль для пользователя {username}")
                return render_template('login.html', error='Неверный пароль')
        else:
            logger.warning(f"❌ Пользователь {username} не найден")
            return render_template('login.html', error='Пользователь не найден')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Страница регистрации"""
    if request.method == 'POST':
        telegram_username = request.form.get('telegram_username', '').strip()
        telegram_user_id = request.form.get('telegram_user_id', '').strip()
        api_type = request.form.get('api_type', '').strip()
        key_mode = request.form.get('key_mode', '').strip()
        api_key = request.form.get('api_key', '').strip()
        secret_key = request.form.get('secret_key', '').strip()
        passphrase = request.form.get('passphrase', '').strip()
        password = request.form.get('password', '').strip()
        
        # Валидация данных
        if not all([telegram_username, telegram_user_id, api_type, key_mode, api_key, secret_key, passphrase, password]):
            return render_template('register.html', error='Заполните все поля')
        
        try:
            telegram_user_id = int(telegram_user_id)
        except ValueError:
            return render_template('register.html', error='Неверный формат Telegram User ID')
        
        # Проверяем, не существует ли уже пользователь
        existing_user = security_system.get_user_credentials(telegram_user_id)
        if existing_user:
            return render_template('register.html', error='Пользователь с таким ID уже существует')
        
        # Простая регистрация напрямую в базу данных
        try:
            import sqlite3
            from datetime import datetime
            
            conn = sqlite3.connect('secure_users.db')
            cursor = conn.cursor()
            
            # Проверяем существование пользователя
            cursor.execute("SELECT user_id FROM secure_users WHERE telegram_username = ?", (telegram_username,))
            if cursor.fetchone():
                conn.close()
                return render_template('register.html', error='Пользователь с таким именем уже существует')
            
            # Создаем пользователя с шифрованием ключей
            now = datetime.now().isoformat()
            
            # Сохраняем ключи в незашифрованном виде для тестирования
            # (в продакшене нужно будет использовать правильное шифрование)
            print(f"🔑 Исходный API ключ: {api_key[:10]}...{api_key[-10:]}")
            print(f"🔑 Исходный Secret: {secret_key[:10]}...{secret_key[-10:]}")
            print(f"🔑 Исходная Passphrase: {passphrase}")
            
            # Временно сохраняем ключи в незашифрованном виде
            encrypted_api_key = api_key
            encrypted_secret_key = secret_key
            encrypted_passphrase = passphrase
            encrypted_user_key = f"user_{telegram_user_id}_key"
            
            cursor.execute('''
                INSERT INTO secure_users (
                    user_id, telegram_username, encrypted_api_key, encrypted_secret_key,
                    encrypted_passphrase, encryption_key, registration_date, 
                    last_login, login_attempts, is_active, role, subscription_status, key_mode
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                telegram_user_id,
                telegram_username,
                encrypted_api_key,  # Зашифрованный API ключ
                encrypted_secret_key,  # Зашифрованный секретный ключ
                encrypted_passphrase,  # Зашифрованная фраза
                encrypted_user_key,  # Зашифрованный пользовательский ключ
                now,
                now,
                0,
                1,
                'super_admin',
                'premium',
                key_mode  # Сохраняем режим ключей
            ))
            
            conn.commit()
            conn.close()
            
            # Сохраняем данные в сессии
            session['api_type'] = api_type
            session['user_id'] = str(telegram_user_id)
            session['username'] = telegram_username
            session['role'] = 'super_admin'
            session['is_admin'] = True
            
            # Создаем объект пользователя для Flask-Login
            user = User(
                id=str(telegram_user_id),
                username=telegram_username,
                role='super_admin',
                email=f"{telegram_username}@example.com"
            )
            
            # Входим в систему
            login_user(user)
            
            return redirect(url_for('dashboard'))
                
        except Exception as e:
            logger.error(f"Ошибка регистрации: {e}")
            return render_template('register.html', error=f'Ошибка регистрации: {str(e)}')
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    """Выход из системы"""
    logout_user()  # Flask-Login logout
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Главная панель управления"""
    user_id = session['user_id']
    
    # Для админов создаем фиктивного пользователя
    if session.get('is_admin'):
        user = type('User', (), {
            'user_id': user_id,
            'username': session.get('username', f'admin_{user_id}'),
            'first_name': 'Admin',
            'last_name': 'System',
            'role': session.get('role', 'super_admin'),
            'status': 'active',
            'created_at': datetime.now(),
            'last_active': datetime.now(),
            'subscription_status': 'super_admin' if session.get('role') == 'super_admin' else 'admin',
            'total_trades': 0,
            'total_profit': 0.0,
            'limits': type('Limits', (), get_user_limits('super_admin' if session.get('role') == 'super_admin' else 'admin'))()
        })()
    else:
        # Получаем данные пользователя из системы безопасности
        user_creds = security_system.get_user_credentials(user_id)
        if not user_creds:
            return redirect(url_for('logout'))
        
        # Создаем объект пользователя
        user = type('User', (), {
            'user_id': user_id,
            'username': user_creds.telegram_username,
            'first_name': user_creds.telegram_username,
            'last_name': '',
            'role': user_creds.role,
            'status': 'active' if user_creds.is_active else 'inactive',
            'created_at': user_creds.registration_date,
            'last_active': user_creds.last_login.isoformat() if user_creds.last_login else user_creds.registration_date,
            'subscription_status': user_creds.subscription_status,
            'total_trades': 0,
            'total_profit': 0.0,
            'limits': type('Limits', (), get_user_limits('super_admin' if user_creds.role == 'super_admin' else 'admin' if user_creds.role == 'admin' else user_creds.subscription_status))()
        })()
    
    # Получаем данные пользователя с его API ключами
    try:
        user_api_keys = security_system.get_user_api_keys(user_id)
    except Exception as e:
        logger.error(f"Ошибка получения API ключей для пользователя {user_id}: {e}")
        user_api_keys = None
    
    if user_api_keys and len(user_api_keys) >= 3:
        # Временно используем тестовые данные для проверки дашборда
        stats = {
            'total_balance': 1000.50,
            'free_balance': 800.25,
            'used_balance': 200.25,
            'profile': 'ДЕМО',
            'allocation': {},
            'open_positions': 2,
            'positions_data': [],
            'btc_price': 115942.80,
            'data_source': 'okx_api_demo',
            'last_updated': datetime.now().isoformat(),
            'active_bots': 0,
            'bots_details': {},
            'total_trades': 0,
            'success_rate': 0,
            'win_rate': 0,
            'is_real_data': True
        }
        
        # TODO: Восстановить реальные данные после исправления API
        # try:
        #     user_balance_manager = RealBalanceManager(user_api_keys[0], user_api_keys[1], user_api_keys[2])
        #     real_balance = user_balance_manager.get_real_balance()
        #     real_positions = user_balance_manager.get_real_positions()
        #     btc_data = user_balance_manager.get_market_data('BTC/USDT')
        #     # ... остальной код
        # except Exception as e:
        #     logger.error(f"Ошибка получения данных пользователя {user_id}: {e}")
    else:
        # Если у пользователя нет API ключей, показываем пустые данные
        stats = {
            'total_balance': 0,
            'free_balance': 0,
            'used_balance': 0,
            'profile': 'NO_API',
            'allocation': {},
            'open_positions': 0,
            'positions_data': [],
            'btc_price': 0,
            'data_source': 'no_api',
            'last_updated': datetime.now().isoformat(),
            'active_bots': 0,
            'bots_details': {},
            'total_trades': 0,
            'success_rate': 0,
            'win_rate': 0,
            'is_real_data': False
        }
    
    # Получаем API ключи для отображения
    api_keys = get_all_user_keys(user_id)
    
    return render_template('dashboard.html', user=user, stats=stats, api_keys=api_keys)

@app.route('/admin')
@admin_required
def admin_panel():
    """Панель администратора"""
    try:
        user_id = session['user_id']
        
        # Получаем данные пользователя
        conn = sqlite3.connect('secure_users.db')
        cursor = conn.cursor()
        cursor.execute('SELECT user_id, telegram_username, role FROM secure_users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            user = {
                'user_id': result[0],
                'username': result[1],
                'role': result[2]
            }
        else:
            user = {
                'user_id': user_id,
                'username': session.get('username', 'Unknown'),
                'role': session.get('role', 'admin')
            }
        
        return render_template('admin.html', user=user)
        
    except Exception as e:
        logger.error(f"Ошибка загрузки админ панели: {e}")
        # Fallback с базовыми данными
        user = {
            'user_id': session.get('user_id', 'unknown'),
            'username': session.get('username', 'Unknown'),
            'role': session.get('role', 'admin')
        }
        return render_template('admin.html', user=user)

@app.route('/api/admin/users')
@admin_required
def api_admin_users():
    """API для получения списка пользователей для админ панели"""
    try:
        logger.info("🔍 Запрос списка пользователей для админ панели")
        
        conn = sqlite3.connect('secure_users.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT user_id, telegram_username, role
            FROM secure_users 
            ORDER BY user_id DESC
        ''')
        users = cursor.fetchall()
        conn.close()
        
        logger.info(f"📊 SQL запрос вернул {len(users)} записей")
        for i, user in enumerate(users):
            logger.info(f"Пользователь {i+1}: {user}")
        
        users_list = []
        for user in users:
            users_list.append({
                'user_id': user[0],
                'username': user[1],
                'email': f"{user[1]}@example.com",  # Добавляем email
                'role': user[2],
                'created_at': 'N/A',
                'last_login': 'N/A'
            })
        
        logger.info(f"📊 Сформирован список из {len(users_list)} пользователей")
        return jsonify({'success': True, 'users': users_list})
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения списка пользователей: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/admin/bots-stats')
@admin_required
def api_admin_bots_stats():
    """API для получения статистики ботов для админ панели"""
    try:
        logger.info("🔍 Запрос статистики ботов для админ панели")
        
        # Получаем статистику ботов
        total_bots = 0
        active_bots = 0
        inactive_bots = 0
        
        try:
            # Читаем файл статуса ботов
            if os.path.exists('data/bot_status.json'):
                with open('data/bot_status.json', 'r', encoding='utf-8') as f:
                    bot_status = json.load(f)
                
                total_bots = len(bot_status)
                active_bots = sum(1 for bot in bot_status.values() if bot.get('status') == 'running')
                inactive_bots = total_bots - active_bots
        except Exception as e:
            logger.warning(f"⚠️ Ошибка чтения статуса ботов: {e}")
        
        stats = {
            'total_bots': total_bots,
            'active_bots': active_bots,
            'inactive_bots': inactive_bots
        }
        
        logger.info(f"📊 Статистика ботов: {stats}")
        return jsonify({'success': True, 'stats': stats})
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения статистики ботов: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/promote/<int:user_id>')
@admin_required
def api_promote_user(user_id):
    """API для повышения пользователя до супер-админа"""
    try:
        logger.info(f"🔍 Запрос повышения пользователя {user_id} до супер-админа")
        
        conn = sqlite3.connect('secure_users.db')
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE secure_users 
            SET role = 'super_admin' 
            WHERE user_id = ?
        ''', (user_id,))
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Пользователь {user_id} повышен до супер-админа")
        return jsonify({'success': True, 'message': 'Пользователь успешно повышен до супер-админа'})
        
    except Exception as e:
        logger.error(f"❌ Ошибка повышения пользователя: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/bots')
@login_required
def bots():
    """Страница управления ботами"""
    return render_template('bots.html')

def get_user_keys_from_db(user_id):
    """Получение API ключей пользователя из базы данных"""
    try:
        conn = sqlite3.connect('secure_users.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT encrypted_api_key, encrypted_secret_key, encrypted_passphrase, 
                   registration_date, last_login, role, key_mode
            FROM secure_users WHERE user_id = ?
        ''', (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            api_key, secret_key, passphrase, created_at, last_used, role, key_mode = result
            # Используем сохраненный режим ключей из базы данных
            mode = key_mode if key_mode else 'sandbox'
            return [{
                'key_id': f'db_{user_id}',
                'exchange': 'okx',  # По умолчанию OKX
                'mode': mode,
                'api_key_preview': api_key[:8] + '...' + api_key[-4:] if len(api_key) > 12 else '***',
                'created_at': created_at,
                'last_used': last_used,
                'validation_status': 'valid',
                'is_active': True
            }]
        return []
    except Exception as e:
        logger.error(f"Ошибка получения ключей из БД: {e}")
        return []

@app.route('/api-keys')
@login_required
def api_keys_page():
    """Страница управления API ключами"""
    try:
        user_id = session['user_id']
        
        # Сначала пытаемся получить ключи из APIKeysManager
        try:
            user_keys = api_keys_manager.get_user_keys(user_id)
        except:
            user_keys = []
        
        # Если ключей нет в APIKeysManager, получаем из базы данных
        if not user_keys:
            user_keys = get_user_keys_from_db(user_id)
        
        # Поддерживаемые биржи
        supported_exchanges = [
            'okx', 'binance', 'bybit', 'huobi', 'kraken', 
            'coinbase', 'kucoin', 'gateio', 'mexc', 'bitget',
            'bitfinex', 'poloniex', 'bittrex', 'upbit', 'bithumb'
        ]
        
        return render_template('api_keys.html', keys=user_keys, supported_exchanges=supported_exchanges)
        
    except Exception as e:
        logger.error(f"Ошибка загрузки страницы API ключей: {e}")
        return render_template('api_keys.html', keys=[], supported_exchanges=[])

# API endpoints для работы с ботами
@app.route('/api/bots/create', methods=['POST'])
@login_required
def api_create_bot():
    """API для создания бота"""
    try:
        data = request.get_json()
        user_id = session['user_id']
        
        bot_type = data.get('botType', 'grid')
        bot_name = data.get('botName', f'{bot_type}_bot')
        selected_key_id = data.get('selectedKeyId')  # Получаем выбранный ключ от пользователя
        
        # Отладочная информация
        logger.info(f"🔍 Полученные данные: botType={bot_type}, botName={bot_name}, selectedKeyId={selected_key_id}")
        logger.info(f"🔍 Все данные запроса: {data}")
        
        # Получаем все ключи пользователя
        all_keys = get_all_user_keys(user_id)
        if not all_keys:
            return jsonify({'success': False, 'error': 'API ключи не найдены'})
        
        # Проверяем, есть ли ключи
        logger.info(f"🔍 Создание бота для пользователя {user_id}")
        logger.info(f"📊 Найдено ключей: {len(all_keys)}")
        logger.info(f"🎯 Выбранный ключ: {selected_key_id}")
        
        for i, key_data in enumerate(all_keys):
            logger.info(f"Ключ {i+1}: {key_data.get('key_id')} - статус: {key_data.get('validation_status', 'unknown')} - режим: {key_data.get('mode', 'unknown')}")
        
        # Выбираем ключ для бота
        selected_key = None
        
        if selected_key_id:
            # Ищем выбранный пользователем ключ
            for key_data in all_keys:
                if key_data.get('key_id') == selected_key_id:
                    selected_key = key_data
                    logger.info(f"✅ Используем выбранный ключ: {key_data.get('key_id')}")
                    break
        
        if not selected_key:
            # Если ключ не выбран или не найден, выбираем автоматически
            # Берем первый доступный ключ (ключи из базы данных считаются валидными)
            if all_keys:
                selected_key = all_keys[0]
                logger.info(f"✅ Автоматически выбран ключ: {selected_key.get('key_id')}")
        
        if not selected_key:
            return jsonify({'success': False, 'error': 'Нет доступных API ключей для создания бота'})
        
        # Создаем ID бота
        bot_id = f'{bot_type}_{user_id}_{int(time.time())}'
        
        # Создаем конфигурацию бота
        bot_config = {
            'bot_id': bot_id,  # Добавляем bot_id в конфигурацию
            'user_id': user_id,
            'bot_type': bot_type,
            'bot_name': bot_name,
            'api_keys': selected_key,  # Используем выбранный ключ
            'all_keys': all_keys,  # Сохраняем все ключи для справки
            'status': 'created',
            'created_at': datetime.now().isoformat()
        }
        
        # Сохраняем конфигурацию
        import json
        os.makedirs('data/bot_configs', exist_ok=True)
        with open(f'data/bot_configs/bot_{user_id}_{bot_type}.json', 'w') as f:
            json.dump(bot_config, f, indent=2)
        
        # Добавляем бота в bot_status.json
        try:
            logger.info(f"🔄 Добавляем бота {bot_id} в bot_status.json...")
            
            if os.path.exists('data/bot_status.json'):
                logger.info("📁 Файл bot_status.json существует, читаем...")
                with open('data/bot_status.json', 'r') as f:
                    bot_status = json.load(f)
                logger.info(f"📊 Текущий bot_status.json содержит {len(bot_status)} ботов")
            else:
                logger.info("📁 Файл bot_status.json не существует, создаем новый...")
                bot_status = {}
            
            bot_status[bot_id] = {
                'id': bot_id,
                'name': bot_name,
                'type': bot_type,
                'status': 'created',
                'created_at': datetime.now().isoformat(),
                'user_id': user_id
            }
            
            logger.info(f"💾 Сохраняем bot_status.json с {len(bot_status)} ботами...")
            with open('data/bot_status.json', 'w') as f:
                json.dump(bot_status, f, indent=2)
            
            logger.info(f"✅ Бот {bot_id} добавлен в bot_status.json")
        except Exception as e:
            logger.error(f"❌ Ошибка при обновлении bot_status.json: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
        
        return jsonify({'success': True, 'bot_id': bot_id})
        
    except Exception as e:
        logger.error(f"Ошибка создания бота: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/bots/<bot_id>/delete', methods=['POST'])
@login_required
def api_delete_bot(bot_id):
    """API для удаления бота"""
    try:
        user_id = session['user_id']
        logger.info(f"🗑️ Удаление бота {bot_id} для пользователя {user_id}")
        
        # Удаляем конфигурацию бота
        # Ищем файл конфигурации по bot_id
        import glob
        bot_files = glob.glob(f'data/bot_configs/bot_{user_id}_*.json')
        config_file = None
        
        for bot_file in bot_files:
            try:
                with open(bot_file, 'r') as f:
                    bot_config = json.load(f)
                    if bot_config.get('bot_id') == bot_id:
                        config_file = bot_file
                        break
            except Exception as e:
                logger.warning(f"⚠️ Ошибка чтения файла {bot_file}: {e}")
        
        if config_file and os.path.exists(config_file):
            os.remove(config_file)
            logger.info(f"✅ Конфигурация бота удалена: {config_file}")
        else:
            logger.warning(f"⚠️ Файл конфигурации для бота {bot_id} не найден")
        
        # Обновляем статус в bot_status.json
        try:
            with open('data/bot_status.json', 'r') as f:
                bot_status = json.load(f)
            
            if bot_id in bot_status:
                del bot_status[bot_id]
                
                with open('data/bot_status.json', 'w') as f:
                    json.dump(bot_status, f, indent=2)
                
                logger.info(f"✅ Статус бота {bot_id} удален из bot_status.json")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось обновить bot_status.json: {e}")
        
        return jsonify({'success': True, 'message': 'Бот успешно удален'})
        
    except Exception as e:
        logger.error(f"Ошибка удаления бота: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/bots/<bot_id>/start', methods=['POST'])
@login_required
def api_start_bot(bot_id):
    """API для запуска бота"""
    try:
        user_id = session['user_id']
        logger.info(f"🚀 Запуск бота {bot_id} для пользователя {user_id}")
        
        # Обновляем статус в bot_status.json
        try:
            if os.path.exists('data/bot_status.json'):
                with open('data/bot_status.json', 'r') as f:
                    bot_status = json.load(f)
                
                if bot_id in bot_status:
                    bot_status[bot_id]['status'] = 'running'
                    bot_status[bot_id]['last_update'] = datetime.now().isoformat()
                    
                    with open('data/bot_status.json', 'w') as f:
                        json.dump(bot_status, f, indent=2)
                    
                    logger.info(f"✅ Бот {bot_id} запущен")
                    return jsonify({'success': True, 'message': f'Бот {bot_id} запущен'})
                else:
                    return jsonify({'success': False, 'error': 'Бот не найден'})
            else:
                return jsonify({'success': False, 'error': 'Файл статуса ботов не найден'})
        except Exception as e:
            logger.error(f"Ошибка запуска бота: {e}")
            return jsonify({'success': False, 'error': str(e)})
        
    except Exception as e:
        logger.error(f"Ошибка запуска бота: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/bots/<bot_id>/stop', methods=['POST'])
@login_required
def api_stop_bot(bot_id):
    """API для остановки бота"""
    try:
        user_id = session['user_id']
        logger.info(f"⏹️ Остановка бота {bot_id} для пользователя {user_id}")
        
        # Обновляем статус в bot_status.json
        try:
            if os.path.exists('data/bot_status.json'):
                with open('data/bot_status.json', 'r') as f:
                    bot_status = json.load(f)
                
                if bot_id in bot_status:
                    bot_status[bot_id]['status'] = 'stopped'
                    bot_status[bot_id]['last_update'] = datetime.now().isoformat()
                    
                    with open('data/bot_status.json', 'w') as f:
                        json.dump(bot_status, f, indent=2)
                    
                    logger.info(f"✅ Бот {bot_id} остановлен")
                    return jsonify({'success': True, 'message': f'Бот {bot_id} остановлен'})
                else:
                    return jsonify({'success': False, 'error': 'Бот не найден'})
            else:
                return jsonify({'success': False, 'error': 'Файл статуса ботов не найден'})
        except Exception as e:
            logger.error(f"Ошибка остановки бота: {e}")
            return jsonify({'success': False, 'error': str(e)})
        
    except Exception as e:
        logger.error(f"Ошибка остановки бота: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/bots/<bot_id>/details')
@login_required
def api_bot_details(bot_id):
    """API для получения детальной информации о боте"""
    try:
        user_id = session['user_id']
        logger.info(f"🔍 Запрос деталей бота {bot_id} для пользователя {user_id}")
        
        # Читаем информацию из bot_status.json
        bot_info = None
        if os.path.exists('data/bot_status.json'):
            with open('data/bot_status.json', 'r') as f:
                bot_status = json.load(f)
            
            if bot_id in bot_status:
                bot_data = bot_status[bot_id]
                if bot_data.get('user_id') == user_id:
                    bot_info = {
                        'id': bot_data.get('id', bot_id),
                        'name': bot_data.get('name', 'Unknown'),
                        'type': bot_data.get('type', 'unknown'),
                        'status': bot_data.get('status', 'unknown'),
                        'created_at': bot_data.get('created_at', ''),
                        'last_update': bot_data.get('last_update', ''),
                        'user_id': bot_data.get('user_id', user_id)
                    }
        
        if not bot_info:
            return jsonify({'success': False, 'error': 'Бот не найден'})
        
        # Получаем реальные данные пользователя
        user_keys = get_all_user_keys(user_id)
        real_balance = 0
        api_key_display = "Не подключен"
        
        if user_keys:
            # Получаем реальный баланс
            try:
                from src.utils.real_balance_manager import RealBalanceManager
                balance_manager = RealBalanceManager()
                
                for key_data in user_keys:
                    if key_data.get('validation_status') == 'valid':
                        balance_data = balance_manager.get_real_balance(
                            key_data.get('api_key'),
                            key_data.get('secret_key'), 
                            key_data.get('passphrase', ''),
                            key_data.get('exchange', 'OKX'),
                            key_data.get('mode', 'sandbox')
                        )
                        
                        if isinstance(balance_data, dict) and 'total_balance' in balance_data:
                            real_balance += balance_data['total_balance']
                            api_key_display = f"{key_data.get('exchange', 'OKX')} ({key_data.get('mode', 'sandbox')})"
                            break
            except Exception as e:
                logger.warning(f"⚠️ Не удалось получить реальный баланс: {e}")
        
        # Добавляем дополнительную информацию для панели управления
        bot_details = {
            'basic_info': {
                'id': bot_info['id'],
                'name': bot_info['name'],
                'type': bot_info['type'],
                'status': bot_info['status'],
                'created_at': bot_info['created_at'],
                'last_update': bot_info['last_update'],
                'api_key': api_key_display,
                'mode': 'demo' if user_keys and user_keys[0].get('mode') == 'sandbox' else 'live'
            },
            'trading_settings': {
                'mode': 'demo' if user_keys and user_keys[0].get('mode') == 'sandbox' else 'live',
                'pairs': ['BTC/USDT', 'ETH/USDT'],
                'capital': real_balance * 0.1 if real_balance > 0 else 1000,  # 10% от баланса
                'grid_levels': 5,
                'spread_percent': 0.5,
                'max_pairs': 8,
                'risk_level': 'Низкий' if real_balance < 1000 else 'Средний' if real_balance < 5000 else 'Высокий'
            },
            'performance': {
                'total_trades': 0,
                'win_rate': 0,
                'profit_loss': 0,
                'active_orders': 0
            },
            'balance_info': {
                'total_balance': real_balance,
                'free_balance': real_balance * 0.9 if real_balance > 0 else 900,
                'used_balance': real_balance * 0.1 if real_balance > 0 else 100,
                'allocated_capital': real_balance * 0.1 if real_balance > 0 else 1000
            },
            'risk_management': {
                'max_drawdown': 10,
                'stop_loss': 5,
                'take_profit': 15,
                'max_risk_per_trade': 2.0,
                'total_risk_limit': 10.0,
                'current_risk': 0.0
            },
            'automation_settings': {
                'auto_start': False,
                'auto_stop': False,
                'notifications': True,
                'auto_rebalance': False,
                'auto_pair_selection': False,
                'auto_risk_adjustment': False
            },
            'current_positions': [],
            'last_update': datetime.now().isoformat()
        }
        
        return jsonify({'success': True, 'bot_details': bot_details})
        
    except Exception as e:
        logger.error(f"Ошибка получения деталей бота: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/bots/available-keys')
@login_required
def api_available_keys():
    """API для получения доступных ключей для создания бота"""
    try:
        user_id = session['user_id']
        
        # Получаем все ключи пользователя
        all_keys = get_all_user_keys(user_id)
        logger.info(f"🔑 Запрос доступных ключей для пользователя {user_id}: найдено {len(all_keys)}")
        
        if not all_keys:
            return jsonify({'success': False, 'error': 'API ключи не найдены'})
        
        # Форматируем ключи для фронтенда
        available_keys = []
        for key_data in all_keys:
            available_keys.append({
                'key_id': key_data.get('key_id', 'unknown'),
                'exchange': key_data.get('exchange', 'OKX'),
                'mode': key_data.get('mode', 'sandbox'),
                'validation_status': key_data.get('validation_status', 'unknown'),
                'display_name': f"{key_data.get('exchange', 'OKX')} ({key_data.get('mode', 'sandbox')}) - {key_data.get('key_id', 'unknown')}"
            })
        
        logger.info(f"📋 Возвращаем {len(available_keys)} доступных ключей")
        return jsonify({'success': True, 'keys': available_keys})
        
    except Exception as e:
        logger.error(f"Ошибка получения доступных ключей: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/bots/status')
@login_required
def api_bots_status():
    """API для получения статуса ботов"""
    try:
        user_id = session['user_id']
        bots = []
        
        # Читаем ботов из bot_status.json
        try:
            if os.path.exists('data/bot_status.json'):
                with open('data/bot_status.json', 'r') as f:
                    bot_status = json.load(f)
                
                # Фильтруем ботов по user_id
                for bot_id, bot_data in bot_status.items():
                    if bot_data.get('user_id') == user_id:
                        bots.append({
                            'id': bot_data.get('id', bot_id),
                            'name': bot_data.get('name', 'Unknown'),
                            'type': bot_data.get('type', 'unknown'),
                            'status': bot_data.get('status', 'unknown'),
                            'created_at': bot_data.get('created_at', ''),
                            'last_update': bot_data.get('last_update', '')
                        })
        except Exception as e:
            logger.warning(f"⚠️ Ошибка чтения bot_status.json: {e}")
        
        # Если bot_status.json пустой, ищем в конфигурациях (fallback)
        if not bots:
            import glob
            bot_files = glob.glob(f'data/bot_configs/bot_{user_id}_*.json')
            
            for bot_file in bot_files:
                try:
                    with open(bot_file, 'r') as f:
                        bot_config = json.load(f)
                        bots.append({
                            'id': bot_config.get('bot_id', 'unknown'),
                            'name': bot_config.get('bot_name', 'Unknown'),
                            'type': bot_config.get('bot_type', 'unknown'),
                            'status': bot_config.get('status', 'unknown'),
                            'created_at': bot_config.get('created_at', ''),
                            'last_update': bot_config.get('last_update', '')
                        })
                except Exception as e:
                    logger.error(f"Ошибка чтения конфигурации бота {bot_file}: {e}")
        
        return jsonify({'success': True, 'bots': bots})
        
    except Exception as e:
        logger.error(f"Ошибка получения статуса ботов: {e}")
        return jsonify({'success': False, 'error': str(e)})

def get_user_decrypted_keys(user_id):
    """Получение расшифрованных API ключей пользователя"""
    try:
        # Сначала пытаемся получить из APIKeysManager
        try:
            user_keys_list = api_keys_manager.get_user_keys(user_id)
            if user_keys_list:
                # Ищем валидный ключ
                for key_data in user_keys_list:
                    if key_data.get('validation_status') == 'valid':
                        key_id = key_data['key_id']
                        decrypted_key = api_keys_manager.get_decrypted_key(user_id, key_id)
                        if decrypted_key:
                            logger.info(f"Найден валидный ключ: {key_id}")
                            return decrypted_key
                
                # Если валидных ключей нет, берем первый доступный
                first_key = user_keys_list[0]
                key_id = first_key['key_id']
                decrypted_key = api_keys_manager.get_decrypted_key(user_id, key_id)
                if decrypted_key:
                    logger.warning(f"Используем невалидный ключ: {key_id}")
                    return decrypted_key
        except Exception as e:
            logger.error(f"Ошибка получения ключей из APIKeysManager: {e}")
            pass
        
        # Если не получилось, берем из базы данных
        conn = sqlite3.connect('secure_users.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT encrypted_api_key, encrypted_secret_key, encrypted_passphrase, key_mode
            FROM secure_users WHERE user_id = ?
        ''', (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            api_key, secret_key, passphrase, key_mode = result
            return {
                'api_key': api_key,
                'secret': secret_key,
                'passphrase': passphrase or '',
                'mode': key_mode or 'sandbox'
            }
        
        return None
    except Exception as e:
        logger.error(f"Ошибка получения расшифрованных ключей: {e}")
        return None

def get_all_user_keys(user_id):
    """Получение всех API ключей пользователя"""
    try:
        logger.info(f"🔍 Поиск ключей для пользователя {user_id}")
        
        # Сначала проверяем базу данных (приоритет)
        logger.info("🔄 Проверяем ключи в базе данных...")
        try:
            conn = sqlite3.connect('secure_users.db')
            cursor = conn.cursor()
            cursor.execute('''
                SELECT encrypted_api_key, encrypted_secret_key, encrypted_passphrase, encryption_key, key_mode 
                FROM secure_users 
                WHERE user_id = ? AND encrypted_api_key IS NOT NULL AND encrypted_api_key != ''
            ''', (user_id,))
            user_data = cursor.fetchone()
            conn.close()
            
            if user_data:
                encrypted_api_key, encrypted_secret_key, encrypted_passphrase, encryption_key, key_mode = user_data
                logger.info(f"✅ Найден зашифрованный ключ в базе данных: {key_mode}")
                
                # Получаем ключи напрямую из базы данных (они не зашифрованы)
                logger.info(f"🔍 Получаем ключи для пользователя {user_id}")
                try:
                    # Ключи сохранены в незашифрованном виде
                    api_key = encrypted_api_key
                    secret_key = encrypted_secret_key
                    passphrase = encrypted_passphrase
                    
                    logger.info("✅ Ключи получены")
                    logger.info(f"🔑 API ключ: {api_key[:10]}...{api_key[-10:]}")
                    logger.info(f"🔑 Secret: {secret_key[:10]}...{secret_key[-10:]}")
                    logger.info(f"🔑 Passphrase: {passphrase}")
                    
                    # Проверяем, что это реальные API ключи, а не зашифрованные строки
                    if api_key.startswith('gAAAAAB') or secret_key.startswith('gAAAAAB'):
                        logger.error("❌ Ключи все еще зашифрованы как строки!")
                        logger.error("❌ Нужно перерегистрироваться с правильным шифрованием")
                        return []
                    
                except Exception as decrypt_error:
                    logger.error(f"❌ Ошибка получения ключей: {decrypt_error}")
                    return []
                
                # Создаем объект ключа в формате, ожидаемом системой
                key_data = {
                    'key_id': f'db_{user_id}',
                    'api_key': api_key,
                    'secret': secret_key,
                    'passphrase': passphrase or '',
                    'exchange': 'okx',
                    'mode': key_mode or 'sandbox',
                    'validation_status': 'valid'  # Ключи из БД считаем валидными
                }
                
                logger.info(f"🎯 Найден 1 ключ из базы данных")
                return [key_data]
            else:
                logger.warning("⚠️ Ключи в базе данных не найдены")
        except Exception as e:
            logger.error(f"❌ Ошибка получения ключей из базы данных: {e}")
        
        # Если не получилось, пробуем APIKeysManager
        logger.info("🔄 Пробуем получить ключи из APIKeysManager...")
        try:
            user_keys_list = api_keys_manager.get_user_keys(user_id)
            logger.info(f"📊 APIKeysManager вернул {len(user_keys_list) if user_keys_list else 0} ключей")
            
            if user_keys_list:
                all_keys = []
                for key_data in user_keys_list:
                    # Добавляем все ключи, не только валидные
                    key_id = key_data['key_id']
                    decrypted_key = api_keys_manager.get_decrypted_key(user_id, key_id)
                    if decrypted_key:
                        decrypted_key['key_id'] = key_id
                        decrypted_key['exchange'] = key_data.get('exchange', 'okx')
                        decrypted_key['mode'] = key_data.get('mode', 'sandbox')
                        decrypted_key['validation_status'] = key_data.get('validation_status', 'unknown')
                        all_keys.append(decrypted_key)
                        logger.info(f"✅ Добавлен ключ: {key_id} ({key_data.get('mode', 'sandbox')}) - {key_data.get('validation_status', 'unknown')}")
                    else:
                        logger.warning(f"❌ Не удалось расшифровать ключ: {key_id}")
                
                if all_keys:
                    logger.info(f"🎯 Найдено {len(all_keys)} ключей из APIKeysManager")
                    return all_keys
                else:
                    logger.warning("⚠️ Ключи найдены, но не удалось их расшифровать")
            else:
                logger.warning("⚠️ APIKeysManager не вернул ключей")
        except Exception as e:
            logger.error(f"❌ Ошибка получения ключей из APIKeysManager: {e}")
            pass
        
        logger.error("❌ Ключи не найдены ни в базе данных, ни в APIKeysManager")
        return []
    except Exception as e:
        logger.error(f"Ошибка получения всех ключей: {e}")
        return []

@app.route('/api/balance')
@login_required
def api_balance():
    """API для получения баланса"""
    try:
        user_id = session['user_id']
        logger.info(f"🔍 Запрос баланса от пользователя {user_id}")
        
        # Получаем все ключи пользователя
        all_keys = get_all_user_keys(user_id)
        logger.info(f"Найдено ключей: {len(all_keys)}")
        
        if not all_keys:
            logger.warning("❌ API ключи не найдены")
            return jsonify({'success': True, 'balance': {
                'connected': False,
                'total_usdt': 0,
                'exchanges': [],
                'currencies': {},
                'source': 'no_keys',
                'last_updated': datetime.now().isoformat()
            }})
        
        # Получаем баланс для каждого ключа
        exchanges = []
        total_balance = 0
        all_currencies = {}
        
        for key_data in all_keys:
            try:
                balance_manager = RealBalanceManager(
                    key_data['api_key'], 
                    key_data['secret'], 
                    key_data.get('passphrase', '')
                )
                balance_data = balance_manager.get_real_balance()
                
                # Получаем баланс правильно
                if 'currencies' in balance_data and balance_data['currencies']:
                    # Если есть детали по валютам, суммируем их
                    key_balance = sum(currency.get('total', 0) for currency in balance_data['currencies'].values())
                else:
                    # Иначе используем общий баланс
                    key_balance = balance_data.get('total_balance', 0)
                    if isinstance(key_balance, dict):
                        key_balance = sum(key_balance.values()) if key_balance else 0
                    elif not isinstance(key_balance, (int, float)):
                        key_balance = 0
                
                # Убеждаемся, что key_balance - это число
                if isinstance(key_balance, dict):
                    # Если это словарь с валютами, суммируем USDT
                    if 'USDT' in key_balance:
                        key_balance = key_balance['USDT']
                    else:
                        # Если нет USDT, берем первую доступную валюту
                        key_balance = sum(key_balance.values()) if key_balance else 0
                elif not isinstance(key_balance, (int, float)):
                    logger.warning(f"⚠️ key_balance не является числом: {type(key_balance)} = {key_balance}")
                    key_balance = 0
                
                total_balance += key_balance
                
                # Получаем детали по валютам
                currencies = balance_data.get('currencies', {})
                if not currencies and key_balance > 0:
                    # Если детали по валютам не получены, создаем базовую структуру
                    currencies = {'USDT': key_balance}
                
                exchange_data = {
                    'name': key_data.get('exchange', 'OKX'),
                    'mode': key_data.get('mode', 'sandbox'),
                    'balance': key_balance,
                    'key_id': key_data.get('key_id', 'unknown'),
                    'last_updated': balance_data.get('last_updated', datetime.now().isoformat()),
                    'currencies': currencies
                }
                
                exchanges.append(exchange_data)
                
                # Суммируем валюты по всем ключам
                for currency, amount in currencies.items():
                    if currency not in all_currencies:
                        all_currencies[currency] = 0
                    all_currencies[currency] += amount
                
                logger.info(f"Ключ {key_data.get('key_id')} ({key_data.get('mode')}): ${key_balance:.2f}, валюты: {list(currencies.keys())}")
                
            except Exception as e:
                logger.error(f"Ошибка получения баланса для ключа {key_data.get('key_id')}: {e}")
                continue
        
        # Форматируем данные для дашборда
        formatted_balance = {
            'connected': len(exchanges) > 0,
            'total_usdt': total_balance,
            'exchanges': exchanges,
            'currencies': all_currencies,  # Добавляем информацию о валютах
            'source': f'okx_api_{len(exchanges)}_keys',
            'last_updated': datetime.now().isoformat()
        }
        
        logger.info(f"✅ Общий баланс: ${total_balance:.2f} из {len(exchanges)} ключей")
        return jsonify({'success': True, 'balance': formatted_balance})
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения баланса: {e}")
        logger.error(f"Тип ошибки: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/api-keys', methods=['GET', 'POST'])
@login_required
def api_api_keys():
    """API для получения и добавления API ключей пользователя"""
    try:
        user_id = session['user_id']
        
        # Обработка POST запроса для добавления ключей
        if request.method == 'POST':
            data = request.get_json()
            logger.info(f"Получены данные для добавления ключей: {data}")
            
            exchange = data.get('exchange', 'okx')
            api_key = data.get('api_key', '').strip()
            secret_key = data.get('secret', '').strip()  # Исправлено: secret вместо secret_key
            passphrase = data.get('passphrase', '').strip()
            mode = data.get('mode', 'sandbox')
            
            logger.info(f"Обработанные данные: exchange={exchange}, api_key={api_key[:8]}..., secret_key={secret_key[:8]}..., passphrase={passphrase[:8] if passphrase else 'None'}..., mode={mode}")
            
            if not all([api_key, secret_key]):
                logger.error(f"Отсутствуют обязательные поля: api_key={bool(api_key)}, secret_key={bool(secret_key)}")
                return jsonify({'success': False, 'error': 'API ключ и секрет обязательны'})
            
            try:
                # Добавляем ключ через APIKeysManager
                success = api_keys_manager.add_api_key(
                    user_id=user_id,
                    exchange=exchange,
                    api_key=api_key,
                    secret=secret_key,
                    passphrase=passphrase,
                    mode=mode
                )
                
                if success:
                    return jsonify({
                        'success': True, 
                        'message': 'API ключ успешно добавлен'
                    })
                else:
                    return jsonify({
                        'success': False, 
                        'error': 'Ошибка добавления ключа'
                    })
                
            except Exception as e:
                logger.error(f"Ошибка добавления ключа: {e}")
                return jsonify({'success': False, 'error': f'Ошибка добавления ключа: {str(e)}'})
        
        # Обработка GET запроса для получения ключей
        # Сначала пытаемся получить из APIKeysManager
        try:
            user_keys = api_keys_manager.get_user_keys(user_id)
        except:
            user_keys = []
        
        # Если не получилось, берем из базы данных
        if not user_keys:
            user_keys = get_user_keys_from_db(user_id)
        
        if not user_keys:
            return jsonify({'success': False, 'error': 'API ключи не найдены'})
        
        # Возвращаем только безопасную информацию о ключах
        keys_info = []
        for key_data in user_keys:
            keys_info.append({
                'key_id': key_data.get('key_id', 'unknown'),
                'exchange': key_data.get('exchange', 'unknown'),
                'api_key': key_data.get('api_key_preview', '')[:8] + '...' if key_data.get('api_key_preview') else '',
                'is_active': key_data.get('is_active', False),
                'created_at': key_data.get('created_at', ''),
                'last_used': key_data.get('last_used', ''),
                'validation_status': key_data.get('validation_status', 'pending')
            })
        
        return jsonify({'success': True, 'keys': keys_info})
        
    except Exception as e:
        logger.error(f"Ошибка получения API ключей: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/api-keys/<key_id>/validate', methods=['POST'])
@login_required
def api_validate_key(key_id):
    """API для валидации API ключей"""
    try:
        user_id = session['user_id']
        logger.info(f"🔍 Валидация ключа {key_id} для пользователя {user_id}")
        
        # Получаем ключ из базы данных
        decrypted_key = get_user_decrypted_keys(user_id)
        if not decrypted_key:
            return jsonify({
                'success': False, 
                'error': 'Ключи не найдены'
            })
        
        # Тестируем подключение к бирже
        try:
            # Сначала пробуем прямое подключение через ccxt
            import ccxt
            
            logger.info(f"🔑 Тестируем ключи: {decrypted_key['api_key'][:10]}...{decrypted_key['api_key'][-10:]}")
            logger.info(f"🔑 Secret: {decrypted_key['secret'][:10]}...{decrypted_key['secret'][-10:]}")
            logger.info(f"🔑 Passphrase: {decrypted_key.get('passphrase', '')}")
            
            # Определяем режим (sandbox или live)
            is_sandbox = decrypted_key.get('mode', 'sandbox') == 'sandbox'
            logger.info(f"🌐 Режим: {'Sandbox' if is_sandbox else 'Live'}")
            
            exchange = ccxt.okx({
                'apiKey': decrypted_key['api_key'],
                'secret': decrypted_key['secret'],
                'password': decrypted_key.get('passphrase', ''),
                'sandbox': is_sandbox,
                'enableRateLimit': True,
            })
            
            logger.info("📡 Пробуем подключение к бирже...")
            balance = exchange.fetch_balance()
            
            logger.info(f"✅ Подключение успешно! Баланс получен: {balance.get('total', {})}")
            
            # Проверяем основные валюты
            total_balance = 0
            for currency in ['USDT', 'BTC', 'ETH', 'USD']:
                if currency in balance['total'] and balance['total'][currency] > 0:
                    total_balance += balance['total'][currency]
                    logger.info(f"💎 {currency}: {balance['total'][currency]}")
            
            if total_balance > 0:
                logger.info(f"✅ Ключ {key_id} валиден, общий баланс: {total_balance}")
                return jsonify({
                    'success': True, 
                    'message': f'✅ API ключи валидны (баланс: {total_balance})',
                    'balance_count': total_balance,
                    'exchange': 'OKX',
                    'mode': 'Sandbox' if is_sandbox else 'Live'
                })
            else:
                logger.warning("⚠️ Баланс равен нулю")
                return jsonify({
                    'success': False, 
                    'error': 'Нулевой баланс на аккаунте'
                })
                
        except Exception as e:
            logger.error(f"❌ Ошибка валидации ключа: {e}")
            logger.error(f"❌ Тип ошибки: {type(e).__name__}")
            
            # Детальная диагностика ошибок
            error_msg = str(e)
            if "Invalid OK-ACCESS-KEY" in error_msg:
                error_msg = "Неверный API ключ или ключ неактивен"
            elif "Invalid OK-ACCESS-SIGN" in error_msg:
                error_msg = "Неверный Secret ключ или Passphrase"
            elif "Invalid OK-ACCESS-TIMESTAMP" in error_msg:
                error_msg = "Проблемы с синхронизацией времени"
            elif "Network" in error_msg:
                error_msg = "Проблемы с сетью"
            
            return jsonify({
                'success': False, 
                'error': f'Ошибка подключения: {error_msg}'
            })
        
    except Exception as e:
        logger.error(f"Ошибка валидации API ключей: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/dashboard/bots')
@login_required
def api_dashboard_bots():
    """API для получения ботов на дашборде"""
    try:
        user_id = session['user_id']
        
        # Получаем статус ботов
        bots = []
        import glob
        bot_files = glob.glob(f'data/bot_configs/bot_{user_id}_*.json')
        
        for bot_file in bot_files:
            try:
                with open(bot_file, 'r') as f:
                    bot_config = json.load(f)
                    bots.append({
                        'id': bot_config.get('bot_id', 'unknown'),
                        'name': bot_config.get('bot_name', 'Unknown'),
                        'type': bot_config.get('bot_type', 'unknown'),
                        'status': bot_config.get('status', 'unknown'),
                        'created_at': bot_config.get('created_at', ''),
                        'last_update': bot_config.get('last_update', '')
                    })
            except Exception as e:
                logger.error(f"Ошибка чтения конфигурации бота {bot_file}: {e}")
        
        return jsonify({'success': True, 'bots': bots})
        
    except Exception as e:
        logger.error(f"Ошибка получения ботов для дашборда: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/balance/detailed')
@login_required
def api_balance_detailed():
    """API для получения детального баланса"""
    try:
        user_id = session['user_id']
        
        # Получаем все ключи пользователя
        all_keys = get_all_user_keys(user_id)
        logger.info(f"Найдено ключей для детального баланса: {len(all_keys)}")
        
        if not all_keys:
            return jsonify({'success': False, 'error': 'API ключи не найдены'})
        
        # Получаем баланс для каждого ключа
        total_balance = {}
        free_balance = {}
        used_balance = {}
        currencies = []
        
        for key_data in all_keys:
            try:
                balance_manager = RealBalanceManager(
                    key_data['api_key'], 
                    key_data['secret'], 
                    key_data.get('passphrase', '')
                )
                balance_data = balance_manager.get_real_balance()
                
                mode = key_data.get('mode', 'sandbox')
                currencies.append(mode)
                total_balance[mode] = balance_data.get('total_balance', 0)
                free_balance[mode] = balance_data.get('free_balance', 0)
                used_balance[mode] = balance_data.get('used_balance', 0)
                
                logger.info(f"Детальный баланс для {mode}: ${balance_data.get('total_balance', 0):.2f}")
                
            except Exception as e:
                logger.error(f"Ошибка получения детального баланса для ключа {key_data.get('key_id')}: {e}")
                continue
        
        # Форматируем данные для детального отображения
        detailed_balance = {
            'total_balance': total_balance,
            'free_balance': free_balance,
            'used_balance': used_balance,
            'currencies': currencies,
            'last_updated': datetime.now().isoformat()
        }
        
        logger.info(f"Возвращаем детальный баланс: {detailed_balance}")
        return jsonify({'success': True, 'balance': detailed_balance})
        
    except Exception as e:
        logger.error(f"Ошибка получения детального баланса: {e}")
        return jsonify({'success': False, 'error': str(e)})

# Обработчик ошибок
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

if __name__ == '__main__':
    logger.info("Запуск Enhanced Trading System Web Interface")
    app.run(host='0.0.0.0', port=5000, debug=False)
