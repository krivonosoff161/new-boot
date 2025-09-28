#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web Forms
Enhanced Trading System v3.0 Commercial
"""

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SelectField, TextAreaField, HiddenField
from wtforms.validators import DataRequired, Email, Length, EqualTo
from wtforms.widgets import TextArea
import re

class LoginForm(FlaskForm):
    """Форма входа"""
    username_or_email = StringField(
        'Имя пользователя или Email',
        validators=[DataRequired(), Length(min=3, max=100)],
        render_kw={'placeholder': 'Введите имя пользователя или email', 'class': 'form-control'}
    )
    password = PasswordField(
        'Пароль',
        validators=[DataRequired(), Length(min=6, max=100)],
        render_kw={'placeholder': 'Введите пароль', 'class': 'form-control'}
    )
    remember_me = BooleanField(
        'Запомнить меня',
        render_kw={'class': 'form-check-input'}
    )
    two_factor_code = StringField(
        'Код 2FA (если включен)',
        validators=[Length(min=6, max=6)],
        render_kw={'placeholder': 'Введите 6-значный код', 'class': 'form-control', 'maxlength': '6'}
    )

class RegisterForm(FlaskForm):
    """Форма регистрации"""
    username = StringField(
        'Имя пользователя',
        validators=[DataRequired(), Length(min=3, max=50)],
        render_kw={'placeholder': 'Введите имя пользователя', 'class': 'form-control'}
    )
    email = StringField(
        'Email',
        validators=[DataRequired(), Email(), Length(max=100)],
        render_kw={'placeholder': 'Введите email', 'class': 'form-control'}
    )
    password = PasswordField(
        'Пароль',
        validators=[
            DataRequired(), 
            Length(min=8, max=100, message='Пароль должен содержать минимум 8 символов')
        ],
        render_kw={'placeholder': 'Введите пароль', 'class': 'form-control'}
    )
    confirm_password = PasswordField(
        'Подтвердите пароль',
        validators=[DataRequired(), EqualTo('password', message='Пароли не совпадают')],
        render_kw={'placeholder': 'Подтвердите пароль', 'class': 'form-control'}
    )
    agree_terms = BooleanField(
        'Я согласен с условиями использования',
        validators=[DataRequired()],
        render_kw={'class': 'form-check-input'}
    )
    agree_privacy = BooleanField(
        'Я согласен с политикой конфиденциальности',
        validators=[DataRequired()],
        render_kw={'class': 'form-check-input'}
    )

    def validate_password(self, field):
        """Валидация пароля"""
        password = field.data
        if len(password) < 8:
            raise ValidationError('Пароль должен содержать минимум 8 символов')
        if not re.search(r'[A-Za-z]', password):
            raise ValidationError('Пароль должен содержать буквы')
        if not re.search(r'\d', password):
            raise ValidationError('Пароль должен содержать цифры')

    def validate_username(self, field):
        """Валидация имени пользователя"""
        username = field.data
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            raise ValidationError('Имя пользователя может содержать только буквы, цифры и подчеркивания')

class TwoFactorForm(FlaskForm):
    """Форма 2FA"""
    code = StringField(
        'Код аутентификации',
        validators=[DataRequired(), Length(min=6, max=6)],
        render_kw={'placeholder': 'Введите 6-значный код', 'class': 'form-control', 'maxlength': '6'}
    )
    backup_code = StringField(
        'Резервный код (если нет доступа к приложению)',
        validators=[Length(min=8, max=8)],
        render_kw={'placeholder': 'Введите 8-значный резервный код', 'class': 'form-control', 'maxlength': '8'}
    )

class LinkAccountForm(FlaskForm):
    """Форма привязки аккаунта"""
    account_type = SelectField(
        'Тип аккаунта',
        choices=[
            ('telegram', 'Telegram'),
            ('email', 'Email'),
            ('phone', 'Телефон')
        ],
        validators=[DataRequired()],
        render_kw={'class': 'form-control'}
    )
    account_value = StringField(
        'Значение аккаунта',
        validators=[DataRequired(), Length(min=3, max=100)],
        render_kw={'placeholder': 'Введите username, email или номер телефона', 'class': 'form-control'}
    )
    verification_code = StringField(
        'Код подтверждения',
        validators=[Length(min=4, max=10)],
        render_kw={'placeholder': 'Введите код подтверждения', 'class': 'form-control'}
    )

class ChangePasswordForm(FlaskForm):
    """Форма смены пароля"""
    current_password = PasswordField(
        'Текущий пароль',
        validators=[DataRequired()],
        render_kw={'placeholder': 'Введите текущий пароль', 'class': 'form-control'}
    )
    new_password = PasswordField(
        'Новый пароль',
        validators=[
            DataRequired(), 
            Length(min=8, max=100)
        ],
        render_kw={'placeholder': 'Введите новый пароль', 'class': 'form-control'}
    )
    confirm_new_password = PasswordField(
        'Подтвердите новый пароль',
        validators=[DataRequired(), EqualTo('new_password', message='Пароли не совпадают')],
        render_kw={'placeholder': 'Подтвердите новый пароль', 'class': 'form-control'}
    )

class ForgotPasswordForm(FlaskForm):
    """Форма восстановления пароля"""
    email = StringField(
        'Email',
        validators=[DataRequired(), Email()],
        render_kw={'placeholder': 'Введите email для восстановления', 'class': 'form-control'}
    )

class ResetPasswordForm(FlaskForm):
    """Форма сброса пароля"""
    token = HiddenField('Токен сброса')
    new_password = PasswordField(
        'Новый пароль',
        validators=[
            DataRequired(), 
            Length(min=8, max=100)
        ],
        render_kw={'placeholder': 'Введите новый пароль', 'class': 'form-control'}
    )
    confirm_new_password = PasswordField(
        'Подтвердите новый пароль',
        validators=[DataRequired(), EqualTo('new_password', message='Пароли не совпадают')],
        render_kw={'placeholder': 'Подтвердите новый пароль', 'class': 'form-control'}
    )

class NotificationSettingsForm(FlaskForm):
    """Форма настроек уведомлений"""
    telegram_enabled = BooleanField(
        'Telegram уведомления',
        render_kw={'class': 'form-check-input'}
    )
    email_enabled = BooleanField(
        'Email уведомления',
        render_kw={'class': 'form-check-input'}
    )
    sms_enabled = BooleanField(
        'SMS уведомления',
        render_kw={'class': 'form-check-input'}
    )
    push_enabled = BooleanField(
        'Push уведомления',
        render_kw={'class': 'form-check-input'}
    )
    
    # Настройки типов уведомлений
    trading_signals = BooleanField(
        'Торговые сигналы',
        render_kw={'class': 'form-check-input'}
    )
    price_alerts = BooleanField(
        'Ценовые алерты',
        render_kw={'class': 'form-check-input'}
    )
    system_notifications = BooleanField(
        'Системные уведомления',
        render_kw={'class': 'form-check-input'}
    )
    security_alerts = BooleanField(
        'Уведомления безопасности',
        render_kw={'class': 'form-check-input'}
    )

class APIKeyForm(FlaskForm):
    """Форма добавления API ключей"""
    exchange = SelectField(
        'Биржа',
        choices=[
            ('okx', 'OKX'),
            ('binance', 'Binance'),
            ('bybit', 'Bybit'),
            ('kraken', 'Kraken')
        ],
        validators=[DataRequired()],
        render_kw={'class': 'form-control'}
    )
    api_key = StringField(
        'API Key',
        validators=[DataRequired(), Length(min=10, max=200)],
        render_kw={'placeholder': 'Введите API ключ', 'class': 'form-control'}
    )
    secret_key = PasswordField(
        'Secret Key',
        validators=[DataRequired(), Length(min=10, max=200)],
        render_kw={'placeholder': 'Введите секретный ключ', 'class': 'form-control'}
    )
    passphrase = StringField(
        'Passphrase (если требуется)',
        validators=[Length(max=100)],
        render_kw={'placeholder': 'Введите passphrase', 'class': 'form-control'}
    )
    is_demo = BooleanField(
        'Демо-режим',
        render_kw={'class': 'form-check-input'}
    )

class ContactForm(FlaskForm):
    """Форма обратной связи"""
    name = StringField(
        'Имя',
        validators=[DataRequired(), Length(min=2, max=50)],
        render_kw={'placeholder': 'Введите ваше имя', 'class': 'form-control'}
    )
    email = StringField(
        'Email',
        validators=[DataRequired(), Email()],
        render_kw={'placeholder': 'Введите ваш email', 'class': 'form-control'}
    )
    subject = StringField(
        'Тема',
        validators=[DataRequired(), Length(min=5, max=100)],
        render_kw={'placeholder': 'Введите тему сообщения', 'class': 'form-control'}
    )
    message = TextAreaField(
        'Сообщение',
        validators=[DataRequired(), Length(min=10, max=1000)],
        render_kw={'placeholder': 'Введите ваше сообщение', 'class': 'form-control', 'rows': 5}
    )
