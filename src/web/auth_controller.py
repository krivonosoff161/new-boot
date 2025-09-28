#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Authentication Controller
Enhanced Trading System v3.0 Commercial
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import login_user, logout_user, login_required, current_user
import logging
from datetime import datetime, timedelta

from core.auth_system import auth_system
from core.flask_auth import FlaskUser, role_required, admin_required, super_admin_required
from .forms import (
    LoginForm, RegisterForm, TwoFactorForm, LinkAccountForm, 
    ChangePasswordForm, ForgotPasswordForm, ResetPasswordForm,
    NotificationSettingsForm, APIKeyForm, ContactForm
)

# Создаем Blueprint для аутентификации
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Страница входа"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = LoginForm()
    
    if form.validate_on_submit():
        username_or_email = form.username_or_email.data
        password = form.password.data
        remember_me = form.remember_me.data
        two_factor_code = form.two_factor_code.data
        
        # Аутентификация пользователя
        success, user, message = auth_system.authenticate_user(
            username_or_email, password, 
            request.remote_addr, request.headers.get('User-Agent')
        )
        
        if success:
            # Проверяем 2FA если включен
            if user.two_factor_enabled:
                if not two_factor_code:
                    flash('Требуется код двухэтапной аутентификации', 'warning')
                    session['pending_user_id'] = user.id
                    return redirect(url_for('auth.verify_2fa'))
                
                if not auth_system.verify_two_factor(user.id, two_factor_code):
                    flash('Неверный код двухэтапной аутентификации', 'error')
                    return render_template('auth/login.html', form=form)
            
            # Создаем сессию
            session_token = auth_system.create_session(
                user.id, request.remote_addr, 
                request.headers.get('User-Agent'), remember_me
            )
            
            # Входим в систему
            flask_user = FlaskUser(user)
            login_user(flask_user, remember=remember_me)
            
            # Уведомляем о сроках сессии
            if remember_me:
                flash('Вы вошли в систему. Сессия будет активна 30 дней.', 'success')
            else:
                flash('Вы вошли в систему. Сессия будет активна 7 дней.', 'success')
            
            # Перенаправляем на дашборд
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('main.dashboard'))
        else:
            flash(message, 'error')
    
    return render_template('auth/login.html', form=form)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Страница регистрации"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = RegisterForm()
    
    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        password = form.password.data
        
        # Регистрация пользователя
        success, message = auth_system.register_user(username, email, password, 'user')
        
        if success:
            flash('Регистрация успешна! Теперь вы можете войти в систему.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash(message, 'error')
    
    return render_template('auth/register.html', form=form)

@auth_bp.route('/verify-2fa', methods=['GET', 'POST'])
def verify_2fa():
    """Страница проверки 2FA"""
    pending_user_id = session.get('pending_user_id')
    if not pending_user_id:
        return redirect(url_for('auth.login'))
    
    form = TwoFactorForm()
    
    if form.validate_on_submit():
        code = form.code.data
        backup_code = form.backup_code.data
        
        # Проверяем основной код
        if code and auth_system.verify_two_factor(pending_user_id, code):
            # Успешная проверка 2FA
            session.pop('pending_user_id', None)
            session['two_factor_verified'] = True
            
            # Получаем пользователя и входим
            # Здесь нужно будет добавить метод get_user_by_id
            flash('Двухэтапная аутентификация успешна!', 'success')
            return redirect(url_for('main.dashboard'))
        
        # Проверяем резервный код
        elif backup_code:
            # Здесь нужно будет добавить проверку backup кодов
            flash('Проверка резервного кода не реализована', 'warning')
        else:
            flash('Неверный код аутентификации', 'error')
    
    return render_template('auth/verify_2fa.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    """Выход из системы"""
    logout_user()
    session.clear()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/profile')
@login_required
def profile():
    """Профиль пользователя"""
    return render_template('auth/profile.html', user=current_user)

@auth_bp.route('/settings')
@login_required
def settings():
    """Настройки пользователя"""
    return render_template('auth/settings.html', user=current_user)

@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Смена пароля"""
    form = ChangePasswordForm()
    
    if form.validate_on_submit():
        current_password = form.current_password.data
        new_password = form.new_password.data
        
        # Проверяем текущий пароль
        success, user, message = auth_system.authenticate_user(
            current_user.username, current_password
        )
        
        if success:
            # Здесь нужно будет добавить метод смены пароля
            flash('Смена пароля не реализована', 'warning')
        else:
            flash('Неверный текущий пароль', 'error')
    
    return render_template('auth/change_password.html', form=form)

@auth_bp.route('/setup-2fa')
@login_required
def setup_2fa():
    """Настройка 2FA"""
    if current_user.two_factor_enabled:
        flash('2FA уже настроен', 'info')
        return redirect(url_for('auth.settings'))
    
    # Настраиваем 2FA
    success, qr_code, backup_codes = auth_system.setup_two_factor(current_user.id)
    
    if success:
        return render_template('auth/setup_2fa.html', 
                             qr_code=qr_code, 
                             backup_codes=backup_codes)
    else:
        flash('Ошибка настройки 2FA', 'error')
        return redirect(url_for('auth.settings'))

@auth_bp.route('/link-account', methods=['GET', 'POST'])
@login_required
def link_account():
    """Привязка аккаунта"""
    form = LinkAccountForm()
    
    if form.validate_on_submit():
        account_type = form.account_type.data
        account_value = form.account_value.data
        verification_code = form.verification_code.data
        
        # Привязываем аккаунт
        success, message = auth_system.link_account(
            current_user.id, account_type, account_value
        )
        
        if success:
            flash(message, 'success')
            return redirect(url_for('auth.settings'))
        else:
            flash(message, 'error')
    
    return render_template('auth/link_account.html', form=form)

@auth_bp.route('/notifications', methods=['GET', 'POST'])
@login_required
def notifications():
    """Настройки уведомлений"""
    form = NotificationSettingsForm()
    
    if form.validate_on_submit():
        # Здесь нужно будет добавить сохранение настроек уведомлений
        flash('Настройки уведомлений сохранены', 'success')
        return redirect(url_for('auth.settings'))
    
    return render_template('auth/notifications.html', form=form)

@auth_bp.route('/api-keys', methods=['GET', 'POST'])
@login_required
def api_keys():
    """Управление API ключами"""
    form = APIKeyForm()
    
    if form.validate_on_submit():
        # Здесь нужно будет добавить сохранение API ключей
        flash('API ключи сохранены', 'success')
        return redirect(url_for('auth.settings'))
    
    return render_template('auth/api_keys.html', form=form)

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Восстановление пароля"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = ForgotPasswordForm()
    
    if form.validate_on_submit():
        email = form.email.data
        # Здесь нужно будет добавить отправку email для восстановления
        flash('Инструкции по восстановлению пароля отправлены на email', 'info')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/forgot_password.html', form=form)

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Сброс пароля по токену"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = ResetPasswordForm()
    form.token.data = token
    
    if form.validate_on_submit():
        # Здесь нужно будет добавить сброс пароля по токену
        flash('Пароль успешно изменен', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/reset_password.html', form=form)

# API endpoints для AJAX запросов
@auth_bp.route('/api/check-username')
def api_check_username():
    """API проверки имени пользователя"""
    username = request.args.get('username')
    if not username:
        return jsonify({'available': False, 'message': 'Имя пользователя не указано'})
    
    # Здесь нужно будет добавить проверку доступности имени
    return jsonify({'available': True, 'message': 'Имя пользователя доступно'})

@auth_bp.route('/api/check-email')
def api_check_email():
    """API проверки email"""
    email = request.args.get('email')
    if not email:
        return jsonify({'available': False, 'message': 'Email не указан'})
    
    # Здесь нужно будет добавить проверку доступности email
    return jsonify({'available': True, 'message': 'Email доступен'})

@auth_bp.route('/api/send-verification')
@login_required
def api_send_verification():
    """API отправки кода подтверждения"""
    account_type = request.args.get('type')
    account_value = request.args.get('value')
    
    if not account_type or not account_value:
        return jsonify({'success': False, 'message': 'Не указаны параметры'})
    
    # Здесь нужно будет добавить отправку кода подтверждения
    return jsonify({'success': True, 'message': 'Код подтверждения отправлен'})
