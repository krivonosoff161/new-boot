#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ПРОСТАЯ РАБОЧАЯ СИСТЕМА УПРАВЛЕНИЯ БОТАМИ
Создана с нуля - без сложностей
"""

import os
import json
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

# Создаем простое Flask приложение
app = Flask(__name__)
app.secret_key = 'simple-trading-system-2024'

def get_db_connection():
    """Подключение к базе данных"""
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """Инициализация базы данных"""
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Создаем админа если его нет
    admin = conn.execute('SELECT * FROM users WHERE username = ?', ('admin',)).fetchone()
    if not admin:
        password_hash = generate_password_hash('admin123')
        conn.execute('''
            INSERT INTO users (username, email, password_hash, role)
            VALUES (?, ?, ?, ?)
        ''', ('admin', 'admin@example.com', password_hash, 'admin'))
    
    conn.commit()
    conn.close()

# ============================================================================
# ОСНОВНЫЕ СТРАНИЦЫ
# ============================================================================

@app.route('/')
def index():
    """Главная страница"""
    if 'user_id' in session:
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
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            return redirect(url_for('dashboard'))
        else:
            flash('Неверное имя пользователя или пароль', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Выход из системы"""
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    """Главная страница дашборда"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Получаем баланс пользователя
    balance = get_user_balance(session['user_id'])
    
    # Получаем ботов пользователя
    bots = get_user_bots(session['user_id'])
    
    return render_template('dashboard.html', 
                         username=session['username'],
                         role=session['role'],
                         balance=balance,
                         bots=bots)

@app.route('/bots')
def bots():
    """Страница управления ботами"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    bots = get_user_bots(session['user_id'])
    return render_template('bots.html', 
                         username=session['username'],
                         role=session['role'],
                         bots=bots)

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.route('/api/balance')
def api_balance():
    """API для получения баланса"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Требуется авторизация'})
    
    balance = get_user_balance(session['user_id'])
    return jsonify({'success': True, 'balance': balance})

@app.route('/api/bots')
def api_bots():
    """API для получения ботов"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Требуется авторизация'})
    
    bots = get_user_bots(session['user_id'])
    return jsonify({'success': True, 'bots': bots})

@app.route('/api/bots/create', methods=['POST'])
def api_create_bot():
    """API для создания бота"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Требуется авторизация'})
    
    data = request.get_json()
    bot_id = f"bot_{session['user_id']}_{int(datetime.now().timestamp())}"
    
    bot_data = {
        'id': bot_id,
        'name': data.get('name', f'Бот {bot_id}'),
        'type': data.get('type', 'grid'),
        'status': 'created',
        'created_at': datetime.now().isoformat(),
        'user_id': session['user_id']
    }
    
    # Сохраняем бота
    save_bot(bot_data)
    
    return jsonify({'success': True, 'bot': bot_data})

@app.route('/api/bots/<bot_id>/start', methods=['POST'])
def api_start_bot(bot_id):
    """API для запуска бота"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Требуется авторизация'})
    
    bot = get_bot(bot_id)
    if not bot or bot['user_id'] != session['user_id']:
        return jsonify({'success': False, 'error': 'Бот не найден'})
    
    bot['status'] = 'running'
    bot['started_at'] = datetime.now().isoformat()
    save_bot(bot)
    
    return jsonify({'success': True, 'message': 'Бот запущен'})

@app.route('/api/bots/<bot_id>/stop', methods=['POST'])
def api_stop_bot(bot_id):
    """API для остановки бота"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Требуется авторизация'})
    
    bot = get_bot(bot_id)
    if not bot or bot['user_id'] != session['user_id']:
        return jsonify({'success': False, 'error': 'Бот не найден'})
    
    bot['status'] = 'stopped'
    bot['stopped_at'] = datetime.now().isoformat()
    save_bot(bot)
    
    return jsonify({'success': True, 'message': 'Бот остановлен'})

# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================

def get_user_balance(user_id):
    """Получить баланс пользователя"""
    try:
        # Читаем баланс из файла API ключей
        api_file = f'data/api_keys/user_{user_id}_keys.json'
        if os.path.exists(api_file):
            with open(api_file, 'r', encoding='utf-8') as f:
                keys_data = json.load(f)
            
            total_usdt = 0
            for key_name, key_info in keys_data.items():
                balance_info = key_info.get('balance_info', {})
                if balance_info:
                    total_balance = balance_info.get('total_balance', {})
                    # Считаем USDT эквивалент
                    usdt_equivalent = 0
                    usdt_equivalent += total_balance.get('USDT', 0)
                    usdt_equivalent += total_balance.get('TUSD', 0)
                    usdt_equivalent += total_balance.get('USDC', 0)
                    usdt_equivalent += total_balance.get('PAX', 0)
                    usdt_equivalent += total_balance.get('USDK', 0)
                    total_usdt += usdt_equivalent
            
            return {
                'total_usdt': round(total_usdt, 2),
                'connected_exchanges': len(keys_data),
                'success': True
            }
    except:
        pass
    
    return {
        'total_usdt': 0,
        'connected_exchanges': 0,
        'success': False,
        'error': 'API ключи не найдены'
    }

def get_user_bots(user_id):
    """Получить ботов пользователя"""
    try:
        with open('data/bot_status.json', 'r', encoding='utf-8') as f:
            all_bots = json.load(f)
        
        user_bots = []
        for bot_id, bot_data in all_bots.items():
            if bot_data.get('user_id') == user_id:
                user_bots.append(bot_data)
        
        return user_bots
    except:
        return []

def get_bot(bot_id):
    """Получить конкретного бота"""
    try:
        with open('data/bot_status.json', 'r', encoding='utf-8') as f:
            all_bots = json.load(f)
        return all_bots.get(bot_id)
    except:
        return None

def save_bot(bot_data):
    """Сохранить бота"""
    try:
        # Читаем существующих ботов
        all_bots = {}
        if os.path.exists('data/bot_status.json'):
            with open('data/bot_status.json', 'r', encoding='utf-8') as f:
                all_bots = json.load(f)
        
        # Обновляем бота
        all_bots[bot_data['id']] = bot_data
        
        # Сохраняем
        with open('data/bot_status.json', 'w', encoding='utf-8') as f:
            json.dump(all_bots, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Ошибка сохранения бота: {e}")

# ============================================================================
# ЗАПУСК СЕРВЕРА
# ============================================================================

if __name__ == '__main__':
    # Инициализируем базу данных
    init_database()
    
    print("🚀 Запуск простой системы управления ботами...")
    print("🌐 Откройте браузер: http://localhost:5000")
    print("🔑 Логин: admin, Пароль: admin123")
    print("⏹️ Для остановки нажмите Ctrl+C")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
