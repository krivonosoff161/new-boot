#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Trading System Web Interface v1.0
Веб-интерфейс для управления торговыми ботами
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import os
import sys
import json
import logging
from datetime import datetime, timedelta
from functools import wraps

# Добавляем пути для импортов
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
sys.path.append(os.path.join(parent_dir, 'enhanced'))

# Загружаем переменные окружения
from dotenv import load_dotenv
env_path = os.path.join(parent_dir, 'config', '.env')
load_dotenv(env_path)

# Импорты системы
from enhanced.security_system_v3 import SecuritySystemV3
from enhanced.bot_manager import BotManager

# Создаем экземпляры
security_system = SecuritySystemV3()
bot_manager = BotManager()

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
            
            for currency, amounts in balance.items():
                if currency == 'info':
                    continue
                    
                if currency == 'USDT':
                    total_balance += amounts['total']
                    free_balance += amounts['free']
                    used_balance += amounts['used']
                elif amounts['total'] > 0:
                    # Конвертируем в USDT (упрощенно)
                    try:
                        ticker = self.ex.fetch_ticker(f'{currency}/USDT')
                        usdt_value = amounts['total'] * ticker['last']
                        total_balance += usdt_value
                        free_balance += amounts['free'] * ticker['last']
                        used_balance += amounts['used'] * ticker['last']
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
                'last_updated': datetime.now().isoformat(),
                'error': str(e)
            }
    
    def get_real_positions(self):
        """Получение реальных позиций с биржи"""
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
    return security_system.is_admin(user_id)

def get_admin_role(user_id):
    """Получение роли администратора"""
    if is_admin(user_id):
        return 'admin'
    return 'user'

def get_admin_permissions(user_id):
    """Получение разрешений администратора"""
    if is_admin(user_id):
        return ['manage_users', 'view_stats', 'manage_bots', 'telegram_access']
    return ['manage_own_bots']

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
app.secret_key = 'your-secret-key-here'  # В продакшене использовать переменную окружения

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
        
        # Проверяем по хардкод списку админов
        if not is_admin(session['user_id']):
            return jsonify({"error": "Недостаточно прав доступа"}), 403
        
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    """Главная страница"""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Страница регистрации с API ключами"""
    if request.method == 'POST':
        telegram_user_id = request.form.get('telegram_user_id')
        telegram_username = request.form.get('telegram_username')
        api_key = request.form.get('api_key')
        secret_key = request.form.get('secret_key')
        passphrase = request.form.get('passphrase')
        sandbox_mode = request.form.get('sandbox_mode') == 'on'
        
        # Валидация данных
        if not all([telegram_user_id, telegram_username, api_key, secret_key, passphrase]):
            return render_template('register.html', error="Все поля обязательны для заполнения")
        
        try:
            telegram_user_id = int(telegram_user_id)
        except ValueError:
            return render_template('register.html', error="Неверный формат Telegram User ID")
        
        # Валидация API ключей
        if not security_system.validate_api_keys(api_key, secret_key, passphrase):
            return render_template('register.html', error="Неверный формат API ключей")
        
        # Регистрация пользователя
        success = security_system.register_user(
            telegram_user_id=telegram_user_id,
            telegram_username=telegram_username,
            api_key=api_key,
            secret_key=secret_key,
            passphrase=passphrase,
            role='user'  # Новые пользователи - обычные пользователи
        )
        
        if success:
            return render_template('register.html', 
                                 success="Регистрация успешна! Теперь вы можете войти в систему.")
        else:
            return render_template('register.html', 
                                 error="Ошибка регистрации. Возможно, пользователь уже существует.")
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Страница входа с проверкой API ключей"""
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        
        if not user_id:
            return render_template('login.html', error="Введите Telegram User ID")
        
        try:
            user_id = int(user_id)
            
            # Сначала проверяем новую систему безопасности
            user_creds = security_system.get_user_credentials(user_id)
            
            if user_creds and user_creds.is_active:
                # Пользователь в новой системе безопасности
                api_credentials = security_system.get_user_api_keys(user_id)
                if not api_credentials:
                    return render_template('login.html', error="Ошибка доступа к API ключам")
                
                # Создаем безопасную сессию
                ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ['REMOTE_ADDR'])
                user_agent = request.environ.get('HTTP_USER_AGENT', '')
                
                session_id = security_system.authenticate_user(user_id, ip_address, user_agent)
                
                if not session_id:
                    return render_template('login.html', error="Ошибка аутентификации")
                
                # Сохраняем в сессии
                session['session_id'] = session_id
                session['user_id'] = user_id
                session['username'] = user_creds.telegram_username
                session['role'] = get_admin_role(user_id) if is_admin(user_id) else user_creds.role
                session['is_admin'] = is_admin(user_id)
                session['admin_permissions'] = get_admin_permissions(user_id)
                
            else:
                # Проверяем, является ли пользователь админом
                if is_admin(user_id):
                    # Создаем админа на лету
                    username = f"admin_{user_id}"
                    
                    # Сохраняем в сессии как админ
                    session['user_id'] = user_id
                    session['username'] = username
                    session['role'] = get_admin_role(user_id)
                    session['is_admin'] = True
                    session['admin_permissions'] = get_admin_permissions(user_id)
                    
                    return redirect(url_for('dashboard'))
                
                # Пользователь не найден в новой системе
                return render_template('login.html', error="Пользователь не найден. Зарегистрируйтесь для доступа к системе")
            
            return redirect(url_for('dashboard'))
            
        except ValueError:
            return render_template('login.html', error="Неверный формат Telegram User ID")
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Выход"""
    session.clear()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Главная панель управления"""
    user_id = session['user_id']
    
    # Для админов создаем фиктивного пользователя
    if session.get('is_admin'):
        from datetime import datetime
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
                'max_capital': 1000000,  # $1M для админа
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
        # Если у пользователя есть API ключи, получаем реальные данные с биржи
        try:
            # Создаем временный экземпляр для получения данных пользователя
            user_balance_manager = RealBalanceManager(user_api_keys[0], user_api_keys[1], user_api_keys[2])
            
            real_balance = user_balance_manager.get_real_balance()
            real_positions = user_balance_manager.get_real_positions()
            btc_data = user_balance_manager.get_market_data('BTC/USDT')
            
            # Формируем статистику на основе реальных данных пользователя
            stats = {
                'total_balance': real_balance.get('total_balance', 0),
                'free_balance': real_balance.get('free_balance', 0),
                'used_balance': real_balance.get('used_balance', 0),
                'profile': real_balance.get('profile', 'UNKNOWN'),
                'allocation': real_balance.get('allocation', {}),
                'open_positions': len(real_positions),
                'positions_data': real_positions,
                'btc_price': btc_data.get('price', 0),
                'data_source': real_balance.get('source', 'user_api'),
                'last_updated': real_balance.get('last_updated', ''),
                'active_bots': 0,  # Боты управляются через сайт
                'bots_details': {},
                'total_trades': 0,
                'success_rate': 0,
                'win_rate': 0,
                'is_real_data': True
            }
        except Exception as e:
            logger.error(f"Ошибка получения данных пользователя {user_id}: {e}")
            # Fallback к пустым данным
            stats = {
                'total_balance': 0,
                'free_balance': 0,
                'used_balance': 0,
                'profile': 'UNKNOWN',
                'allocation': {},
                'open_positions': 0,
                'positions_data': [],
                'btc_price': 0,
                'data_source': 'error',
                'last_updated': '',
                'active_bots': 0,
                'bots_details': {},
                'total_trades': 0,
                'success_rate': 0,
                'win_rate': 0,
                'is_real_data': False,
                'error': str(e)
            }
    else:
        # Если нет API ключей, показываем пустые данные
        stats = {
            'total_balance': 0,
            'free_balance': 0,
            'used_balance': 0,
            'profile': 'NO_API_KEYS',
            'allocation': {},
            'open_positions': 0,
            'positions_data': [],
            'btc_price': 0,
            'data_source': 'no_api',
            'last_updated': '',
            'active_bots': 0,
            'bots_details': {},
        'total_trades': 0,
        'success_rate': 0,
            'win_rate': 0,
            'is_real_data': False,
            'message': 'Добавьте API ключи для просмотра данных с биржи'
    }
    
    return render_template('dashboard.html', user=user, stats=stats)

@app.route('/api/user/stats')
@login_required
def api_user_stats():
    """API для получения реальной статистики пользователя"""
    user_id = session['user_id']
    user_api_keys = security_system.get_user_api_keys(user_id)
    
    if user_api_keys:
        try:
            # Создаем временный экземпляр для получения данных пользователя
            user_balance_manager = RealBalanceManager(user_api_keys[0], user_api_keys[1], user_api_keys[2])
            
            real_balance = user_balance_manager.get_real_balance()
            real_positions = user_balance_manager.get_real_positions()
            btc_data = user_balance_manager.get_market_data('BTC/USDT')
            
            stats = {
                'total_balance': real_balance.get('total_balance', 0),
                'free_balance': real_balance.get('free_balance', 0),
                'used_balance': real_balance.get('used_balance', 0),
                'profile': real_balance.get('profile', 'UNKNOWN'),
                'allocation': real_balance.get('allocation', {}),
                'open_positions': len(real_positions),
                'positions_data': real_positions,
                'btc_price': btc_data.get('price', 0),
                'data_source': real_balance.get('source', 'user_api'),
                'last_updated': real_balance.get('last_updated', ''),
                'timestamp': datetime.now().isoformat(),
                'is_real_data': True
            }
        except Exception as e:
            logger.error(f"Ошибка получения данных пользователя {user_id}: {e}")
            stats = {
                'total_balance': 0,
                'free_balance': 0,
                'used_balance': 0,
                'profile': 'ERROR',
                'allocation': {},
                'open_positions': 0,
                'positions_data': [],
                'btc_price': 0,
                'data_source': 'error',
                'last_updated': '',
                'timestamp': datetime.now().isoformat(),
                'is_real_data': False,
                'error': str(e)
            }
    else:
        stats = {
            'total_balance': 0,
            'free_balance': 0,
            'used_balance': 0,
            'profile': 'NO_API_KEYS',
            'allocation': {},
            'open_positions': 0,
            'positions_data': [],
            'btc_price': 0,
            'data_source': 'no_api',
            'last_updated': '',
            'timestamp': datetime.now().isoformat(),
            'is_real_data': False,
            'message': 'Добавьте API ключи для просмотра данных с биржи'
    }
    
    return jsonify(stats)

@app.route('/api/user/bots')
@login_required
def api_user_bots():
    """API для получения информации о ботах пользователя"""
    user_id = session['user_id']
    user_api_keys = security_system.get_user_api_keys(user_id)
    
    if not user_api_keys:
        return jsonify({
            "error": "API ключи не найдены",
            "bots": {}
        })
    
    try:
        from enhanced.user_bot_manager import get_user_bot_manager
        user_bot_manager = get_user_bot_manager(user_id, *user_api_keys)
        bots_status = user_bot_manager.get_bots_status()
        
        bot_info = {}
        for bot_type, bot_data in bots_status.items():
            if bot_type != 'summary':
                bot_info[bot_type] = {
                    "active": bot_data['status'] == 'running',
                    "name": bot_data['name'],
                    "status": bot_data['status'],
                    "uptime": bot_data.get('uptime', '0s')
                }
        
        return jsonify(bot_info)
    except Exception as e:
        logger.error(f"Ошибка получения информации о ботах для пользователя {user_id}: {e}")
        return jsonify({
            "error": str(e),
            "bots": {}
        })

@app.route('/api/user/config/<bot_type>', methods=['GET', 'POST'])
@login_required
def api_user_config(bot_type):
    """API для управления конфигурацией ботов"""
    user_id = session['user_id']
    user_api_keys = security_system.get_user_api_keys(user_id)
    
    if not user_api_keys:
        return jsonify({"error": "API ключи не найдены"}), 400
    
    from enhanced.user_bot_manager import get_user_bot_manager
    user_bot_manager = get_user_bot_manager(user_id, *user_api_keys)
    
    if request.method == 'GET':
        try:
            # Получаем конфигурацию из файла пользователя
            config_file = os.path.join(parent_dir, 'user_data', f'user_{user_id}_config.json')
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    import json
                    user_config = json.load(f)
                    
                if bot_type == "grid":
                    return jsonify(user_config.get('grid', {}))
                elif bot_type == "scalp":
                    return jsonify(user_config.get('scalp', {}))
            
            # Дефолтная конфигурация
            if bot_type == "grid":
                config = {
                    "min_order_usd": 20,
                    "max_position_size": 200,
                    "exposure_limit": 0.5,
                    "base_spacing": 0.008,
                    "max_levels": 6,
                    "sleep_interval": 15,
                    "order_timeout_seconds": 600,
                    "cci_block": -150,
                    "grid_mode": "futures"
                }
            elif bot_type == "scalp":
                config = {
                    "min_order_usd": 15,
                    "max_positions": 8,
                    "position_size_percent": 0.05,
                    "sleep_interval": 5,
                    "signal_threshold": 50,
                    "max_hold_seconds": 180,
                    "tp_pct": 0.15,
                    "sl_pct": 0.25,
                    "fee_rate": 0.0004
                }
            else:
                return jsonify({"error": "Неизвестный тип бота"}), 400
            
            return jsonify(config)
        except Exception as e:
            logger.error(f"Ошибка получения конфигурации бота: {e}")
            return jsonify({"error": str(e)}), 500
        
    elif request.method == 'POST':
        try:
            # Обновляем конфигурацию
            config_data = request.json
            
            # Загружаем текущую конфигурацию
            config_file = os.path.join(parent_dir, 'user_data', f'user_{user_id}_config.json')
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    import json
                    user_config = json.load(f)
            else:
                user_config = user_bot_manager.user_config
            
            # Обновляем конфигурацию бота
            if bot_type in ['grid', 'scalp']:
                user_config[bot_type].update(config_data)
                
                # Сохраняем обновленную конфигурацию
                with open(config_file, 'w', encoding='utf-8') as f:
                    import json
                    json.dump(user_config, f, indent=2, ensure_ascii=False)
                
                return jsonify({"success": True})
            else:
                return jsonify({"error": "Неизвестный тип бота"}), 400
        except Exception as e:
            logger.error(f"Ошибка обновления конфигурации бота: {e}")
            return jsonify({"error": str(e)}), 500
    else:
        return jsonify({"error": "Метод не поддерживается"}), 405

@app.route('/bots')
@login_required
def bots():
    """Страница управления ботами"""
    user_id = session['user_id']
    
    # Для админов создаем фиктивного пользователя
    if session.get('is_admin'):
        from datetime import datetime
        user = type('User', (), {
            'user_id': user_id,
            'username': session.get('username', f'admin_{user_id}'),
            'first_name': 'Admin',
            'last_name': 'System',
            'role': session.get('role', 'super_admin'),
            'status': 'active',
            'created_at': datetime.now(),
            'last_active': datetime.now(),
            'subscription_status': 'admin'
        })()
        bots_info = {}  # Заглушка для админов
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
            'subscription_status': 'premium' if user_creds.role == 'admin' else 'free'
        })()
        
        # Получаем информацию о ботах пользователя
        bots_info = {}
    
    return render_template('bots.html', user=user, bots=bots_info)

@app.route('/settings')
@login_required
def settings():
    """Страница настроек"""
    user_id = session['user_id']
    
    # Для админов создаем фиктивного пользователя
    if session.get('is_admin'):
        from datetime import datetime
        user = type('User', (), {
            'user_id': user_id,
            'username': session.get('username', f'admin_{user_id}'),
            'first_name': 'Admin',
            'last_name': 'System',
            'role': session.get('role', 'super_admin'),
            'status': 'active',
            'created_at': datetime.now(),
            'last_active': datetime.now(),
            'subscription_status': 'admin'
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
            'subscription_status': 'premium' if user_creds.role == 'admin' else 'free'
        })()
    
    return render_template('settings.html', user=user)

@app.route('/admin')
@admin_required
def admin():
    """Админ панель"""
    # Получаем статистику из системы безопасности
    security_stats = security_system.get_security_stats()
    stats = {
        'total_users': security_stats.get('active_users', 0),
        'admin_users': security_stats.get('admin_users', 0),
        'active_sessions': security_stats.get('active_sessions', 0),
        'recent_events': security_stats.get('recent_events', []),
        'security_level': security_stats.get('security_level', 'UNKNOWN')
    }
    return render_template('admin.html', stats=stats)

@app.route('/api/admin/users')
@admin_required
def api_admin_users():
    """API для получения списка пользователей (только для админа)"""
    try:
        users = security_system.get_all_users()
        users_list = []
        
        for user in users:
            users_list.append({
                "user_id": user.user_id,
                "username": user.telegram_username,
                "first_name": user.telegram_username,  # Используем username как имя
                "last_name": "",  # Telegram username не содержит фамилию
                "role": user.role,
                "status": "active" if user.is_active else "inactive",
                "created_at": user.registration_date.isoformat(),
                "last_active": user.last_login.isoformat() if user.last_login else None,
                "login_attempts": user.login_attempts,
                "has_api_keys": True  # Если пользователь в системе, значит API ключи есть
            })
        
        return jsonify(users_list)
    except Exception as e:
        logger.error(f"Ошибка получения списка пользователей: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/activate_user/<int:user_id>', methods=['POST'])
@admin_required
def api_admin_activate_user(user_id):
    """API для активации пользователя"""
    if security_system.activate_user(user_id):
        return jsonify({"success": True})
    else:
        return jsonify({"error": "Ошибка активации пользователя"}), 500

@app.route('/api/admin/deactivate_user/<int:user_id>', methods=['POST'])
@admin_required
def api_admin_deactivate_user(user_id):
    """API для деактивации пользователя"""
    if security_system.deactivate_user(user_id):
        return jsonify({"success": True})
    else:
        return jsonify({"error": "Ошибка деактивации пользователя"}), 500

@app.route('/api/admin/update_user_role/<int:user_id>', methods=['POST'])
@admin_required
def api_admin_update_user_role(user_id):
    """API для обновления роли пользователя"""
    new_role = request.json.get('role')
    
    if not new_role or new_role not in ['user', 'admin']:
        return jsonify({"error": "Неверная роль. Допустимые: user, admin"}), 400
    
    if security_system.update_user_role(user_id, new_role):
        return jsonify({"success": True})
    else:
        return jsonify({"error": "Ошибка обновления роли"}), 500

# API эндпоинты для управления ботами пользователя
@app.route('/api/bots/start/<bot_type>', methods=['POST'])
@login_required
def api_start_bot(bot_type):
    """API для запуска бота пользователя"""
    user_id = session['user_id']
    user_api_keys = security_system.get_user_api_keys(user_id)
    
    if not user_api_keys:
        return jsonify({"success": False, "error": "API ключи не найдены"}), 400
    
    try:
        from enhanced.user_bot_manager import get_user_bot_manager
        user_bot_manager = get_user_bot_manager(user_id, *user_api_keys)
        result = user_bot_manager.start_bot(bot_type)
        
        if result["success"]:
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f"Ошибка запуска бота для пользователя {user_id}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/bots/stop/<bot_type>', methods=['POST'])
@login_required
def api_stop_bot(bot_type):
    """API для остановки бота пользователя"""
    user_id = session['user_id']
    user_api_keys = security_system.get_user_api_keys(user_id)
    
    if not user_api_keys:
        return jsonify({"success": False, "error": "API ключи не найдены"}), 400
    
    try:
        from enhanced.user_bot_manager import get_user_bot_manager
        user_bot_manager = get_user_bot_manager(user_id, *user_api_keys)
        result = user_bot_manager.stop_bot(bot_type)
    
    if result["success"]:
        return jsonify(result)
    else:
        return jsonify(result), 400
    except Exception as e:
        logger.error(f"Ошибка остановки бота для пользователя {user_id}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/bots/restart/<bot_type>', methods=['POST'])
@login_required
def api_restart_bot(bot_type):
    """API для перезапуска бота пользователя"""
    user_id = session['user_id']
    user_api_keys = security_system.get_user_api_keys(user_id)
    
    if not user_api_keys:
        return jsonify({"success": False, "error": "API ключи не найдены"}), 400
    
    try:
        from enhanced.user_bot_manager import get_user_bot_manager
        user_bot_manager = get_user_bot_manager(user_id, *user_api_keys)
        result = user_bot_manager.restart_bot(bot_type)
    
    if result["success"]:
        return jsonify(result)
    else:
        return jsonify(result), 400
    except Exception as e:
        logger.error(f"Ошибка перезапуска бота для пользователя {user_id}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/bots/status')
@login_required
def api_bots_status():
    """API для получения статуса ботов пользователя"""
    user_id = session['user_id']
    user_api_keys = security_system.get_user_api_keys(user_id)
    
    if not user_api_keys:
        return jsonify({
            "summary": {
                "total_bots": 0,
                "active_bots": 0,
                "inactive_bots": 0,
                "user_id": user_id,
                "error": "API ключи не найдены"
            }
        })
    
    try:
        from enhanced.user_bot_manager import get_user_bot_manager
        user_bot_manager = get_user_bot_manager(user_id, *user_api_keys)
        return jsonify(user_bot_manager.get_bots_status())
    except Exception as e:
        logger.error(f"Ошибка получения статуса ботов для пользователя {user_id}: {e}")
        return jsonify({
            "summary": {
                "total_bots": 0,
                "active_bots": 0,
                "inactive_bots": 0,
                "user_id": user_id,
                "error": str(e)
            }
        })

@app.route('/api/bots/start_all', methods=['POST'])
@login_required
def api_start_all_bots():
    """API для запуска всех ботов пользователя"""
    user_id = session['user_id']
    user_api_keys = security_system.get_user_api_keys(user_id)
    
    if not user_api_keys:
        return jsonify({"success": False, "error": "API ключи не найдены"}), 400
    
    try:
        from enhanced.user_bot_manager import get_user_bot_manager
        user_bot_manager = get_user_bot_manager(user_id, *user_api_keys)
        result = user_bot_manager.start_all_bots()
    
    if result["success"]:
        return jsonify(result)
    else:
        return jsonify(result), 400
    except Exception as e:
        logger.error(f"Ошибка запуска всех ботов для пользователя {user_id}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/bots/stop_all', methods=['POST'])
@login_required
def api_stop_all_bots():
    """API для остановки всех ботов пользователя"""
    user_id = session['user_id']
    user_api_keys = security_system.get_user_api_keys(user_id)
    
    if not user_api_keys:
        return jsonify({"success": False, "error": "API ключи не найдены"}), 400
    
    try:
        from enhanced.user_bot_manager import get_user_bot_manager
        user_bot_manager = get_user_bot_manager(user_id, *user_api_keys)
        result = user_bot_manager.stop_all_bots()
    
    if result["success"]:
        return jsonify(result)
    else:
        return jsonify(result), 400
    except Exception as e:
        logger.error(f"Ошибка остановки всех ботов для пользователя {user_id}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

# Обработчик ошибок
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

if __name__ == '__main__':
    # Создаем папку для шаблонов, если её нет
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)
    
    logger.info("Запуск Enhanced Trading System Web Interface")
    app.run(debug=True, host='0.0.0.0', port=5000)















