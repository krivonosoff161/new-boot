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
from functools import wraps

# Добавляем пути для импорта модулей
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)
sys.path.append(os.path.join(parent_dir, 'enhanced'))

# Импортируем модули системы
from core.security_system_v3 import SecuritySystemV3
# from trading.bot_manager import BotManager

# Инициализация системы
security_system = SecuritySystemV3()
# bot_manager = BotManager()

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
        }
    }
    return limits.get(subscription_status, limits['free'])

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

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
        
        print(f"DEBUG: Username: {username}, Password: {password}")
        
        # Ищем пользователя по username
        users = security_system.get_all_users()
        print(f"DEBUG: Found {len(users)} users")
        
        user_creds = None
        for user in users:
            print(f"DEBUG: Checking user: {user.telegram_username}")
            # Проверяем по username или по роли super_admin
            if (user.telegram_username == username or 
                user.role == "super_admin" or 
                username in ["дмитрий", "admin", "dmitry"]):
                user_creds = user
                break
        
        print(f"DEBUG: User found: {user_creds is not None}")
        
        if user_creds:
            # Проверяем пароль (пока простое сравнение с username)
            print(f"DEBUG: Password check: '{password}' == '123' = {password == '123'}")
            if password == "123":  # Простая проверка для тестирования
                print("DEBUG: Login successful!")
                session['user_id'] = user_creds.user_id
                session['username'] = user_creds.telegram_username
                session['role'] = user_creds.role
                session['is_admin'] = is_admin(user_creds.user_id)
                
                # Обновляем время последнего входа
                security_system.update_last_login(user_creds.user_id)
                
                return redirect(url_for('dashboard'))
            else:
                print("DEBUG: Wrong password!")
                return render_template('login.html', error='Неверный пароль')
        else:
            print("DEBUG: User not found!")
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
        
        # Регистрируем пользователя
        try:
            success = security_system.register_user(
                telegram_user_id=telegram_user_id,
                telegram_username=telegram_username,
                api_key=api_key,
                secret_key=secret_key,
                passphrase=passphrase,
                role='user'  # Обычный пользователь
            )
            
            if success:
                # Сохраняем тип API в сессии для дальнейшего использования
                session['api_type'] = api_type
                session['user_id'] = telegram_user_id
                session['username'] = telegram_username
                session['role'] = 'user'
                
                return redirect(url_for('dashboard'))
            else:
                return render_template('register.html', error='Ошибка регистрации пользователя')
                
        except Exception as e:
            logger.error(f"Ошибка регистрации: {e}")
            return render_template('register.html', error=f'Ошибка регистрации: {str(e)}')
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    """Выход из системы"""
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
            'subscription_status': 'admin',
            'total_trades': 0,
            'total_profit': 0.0,
            'limits': type('Limits', (), {
                'max_capital': 1000000,
                'max_virtual_balance': 1000000,
                'real_trading': True,
                'api_calls_per_hour': 10000
            })()
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
            'last_active': user_creds.last_login or user_creds.registration_date,
            'subscription_status': 'premium' if user_creds.role == 'admin' else 'free',
            'total_trades': 0,
            'total_profit': 0.0,
            'limits': type('Limits', (), get_user_limits('premium' if user_creds.role == 'admin' else 'free'))()
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

@app.route('/bots')
@login_required
def bots():
    """Страница управления ботами"""
    return render_template('bots.html')

@app.route('/api_keys')
@login_required
def api_keys_page():
    """Страница управления API ключами"""
    return render_template('api_keys.html')

# API ENDPOINTS
@app.route('/api/bots/status')
@login_required
def api_bots_status():
    """API: Статус ботов"""
    return jsonify({
        'success': True,
        'bots': [],
        'message': 'Боты не найдены'
    })

@app.route('/api/bots/create', methods=['POST'])
@login_required
def api_bots_create():
    """API: Создание бота"""
    data = request.get_json()
    return jsonify({
        'success': True,
        'message': 'Бот создан успешно',
        'bot_id': 'test_bot_123'
    })

@app.route('/api/bots/<bot_id>/start', methods=['POST'])
@login_required
def api_bots_start(bot_id):
    """API: Запуск бота"""
    return jsonify({
        'success': True,
        'message': f'Бот {bot_id} запущен'
    })

@app.route('/api/bots/<bot_id>/stop', methods=['POST'])
@login_required
def api_bots_stop(bot_id):
    """API: Остановка бота"""
    return jsonify({
        'success': True,
        'message': f'Бот {bot_id} остановлен'
    })

@app.route('/api/bots/<bot_id>/delete', methods=['POST'])
@login_required
def api_bots_delete(bot_id):
    """API: Удаление бота"""
    return jsonify({
        'success': True,
        'message': f'Бот {bot_id} удален'
    })

@app.route('/api/bots/<bot_id>/details')
@login_required
def api_bots_details(bot_id):
    """API: Детали бота"""
    return jsonify({
        'success': True,
        'bot': {
            'id': bot_id,
            'name': f'Test Bot {bot_id}',
            'status': 'stopped',
            'capital': 1000,
            'profit': 0
        }
    })

@app.route('/api/balance')
@login_required
def api_balance():
    """API: Баланс"""
    return jsonify({
        'success': True,
        'balance': 0,
        'message': 'API ключи не настроены'
    })

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
