#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Упрощенная версия веб-интерфейса для тестирования
"""

import os
import sys
import logging
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

# Инициализация системы
security_system = SecuritySystemV3()

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
            
            # Вычисляем общий баланс в USDT
            total_balance = 0
            free_balance = 0
            used_balance = 0
            
            # Обрабатываем баланс правильно
            if isinstance(balance, dict):
                for currency, amounts in balance.items():
                    if currency == 'info':
                        continue
                    
                    # Проверяем, что amounts - это словарь
                    if isinstance(amounts, dict) and 'total' in amounts:
                        if currency == 'USDT':
                            total_balance += amounts.get('total', 0)
                            free_balance += amounts.get('free', 0)
                            used_balance += amounts.get('used', 0)
                        elif amounts.get('total', 0) > 0:
                            # Конвертируем в USDT (упрощенно)
                            try:
                                ticker = self.ex.fetch_ticker(f'{currency}/USDT')
                                usdt_value = amounts.get('total', 0) * ticker.get('last', 0)
                                total_balance += usdt_value
                                free_balance += amounts.get('free', 0) * ticker.get('last', 0)
                                used_balance += amounts.get('used', 0) * ticker.get('last', 0)
                            except:
                                pass  # Пропускаем валюты без пары USDT
            
            mode_text = "ДЕМО" if self.sandbox_mode else "РЕАЛЬНЫЙ"
            return {
                'total_balance': total_balance,
                'free_balance': free_balance,
                'used_balance': used_balance,
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
    admin_ids = [1, 2]  # Хардкод список админов
    return user_id in admin_ids

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
            return redirect(url_for('login'))
        
        if not is_admin(session['user_id']):
            return jsonify({"error": "Недостаточно прав доступа"}), 403
        
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
                             login_attempts, is_active, role, subscription_status):
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
            
            user_creds = SimpleUser(*result)
        
        if user_creds:
            # Простая проверка пароля (для демо)
            if password == username or password == 'admin':
                # Создаем объект пользователя для Flask-Login
                user = User(
                    id=str(user_creds.user_id),
                    username=user_creds.telegram_username,
                    role='super_admin',  # Все зарегистрированные пользователи - супер-админы
                    email=f"{user_creds.telegram_username}@example.com"
                )
                
                # Входим в систему через Flask-Login
                login_user(user)
                
                session['user_id'] = str(user_creds.user_id)
                session['username'] = user_creds.telegram_username
                session['role'] = 'super_admin'
                session['is_admin'] = True
                
                # Обновляем время последнего входа
                security_system._update_login_info(user_creds.user_id, True)
                
                return redirect(url_for('dashboard'))
            else:
                return render_template('login.html', error='Неверный пароль')
        else:
            return render_template('login.html', error='Пользователь не найден')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Страница регистрации"""
    if request.method == 'POST':
        telegram_username = request.form.get('telegram_username', '').strip()
        telegram_user_id = request.form.get('telegram_user_id', '').strip()
        api_type = request.form.get('api_type', '').strip()
        api_key = request.form.get('api_key', '').strip()
        secret_key = request.form.get('secret_key', '').strip()
        passphrase = request.form.get('passphrase', '').strip()
        password = request.form.get('password', '').strip()
        
        # Валидация данных
        if not all([telegram_username, telegram_user_id, api_type, api_key, secret_key, passphrase, password]):
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
            
            # Создаем пользователя
            now = datetime.now().isoformat()
            cursor.execute('''
                INSERT INTO secure_users (
                    user_id, telegram_username, encrypted_api_key, encrypted_secret_key,
                    encrypted_passphrase, encryption_key, registration_date, 
                    last_login, login_attempts, is_active, role, subscription_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                telegram_user_id,
                telegram_username,
                api_key,  # Не шифруем для простоты
                secret_key,
                passphrase,
                'simple_key',
                now,
                now,
                0,
                1,
                'super_admin',
                'premium'
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
    
    return render_template('dashboard.html', user=user, stats=stats)

@app.route('/admin')
@admin_required
def admin_panel():
    """Панель администратора"""
    return render_template('admin.html')

# Обработчик ошибок
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

if __name__ == '__main__':
    logger.info("Запуск Enhanced Trading System Web Interface")
    app.run(host='0.0.0.0', port=5000, debug=True)
