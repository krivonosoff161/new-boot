#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Notification Controller - упрощенный Telegram бот для уведомлений
Enhanced Trading System v3.0
"""

import asyncio
import logging
import os
import sys
import time
import json
import random
import string
from datetime import datetime
from typing import Dict, List, Optional, Any

# Telegram imports
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.constants import ParseMode

# Добавляем пути для импортов
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Импорты существующих модулей
from core.config_manager import ConfigManager
from core.security_system_v3 import SecuritySystemV3

class NotificationController:
    """
    Упрощенный контроллер уведомлений v3.0
    
    Функции:
    - Восстановление пароля через Telegram
    - Двухфакторная аутентификация
    - Общие уведомления для пользователей
    - Доступ только для супер-админов
    """
    
    def __init__(self):
        """Инициализация контроллера уведомлений"""
        self.logger = logging.getLogger(__name__)
        
        # Конфигурация
        self.config_manager = ConfigManager()
        self.config = self.config_manager.get_config()
        
        # Система безопасности
        self.security_system = SecuritySystemV3()
        
        # Telegram бот - только для уведомлений
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN') or os.getenv('TELEGRAM_TOKEN')
        if not self.telegram_token:
            self.logger.warning("⚠️ TELEGRAM_BOT_TOKEN не найден - Telegram уведомления недоступны")
            self.application = None
        else:
            self.application = Application.builder().token(self.telegram_token).build()
        
        # Коды восстановления (временное хранение)
        self.reset_codes = {}  # {user_id: {'code': str, 'expires': datetime}}
        
        # Статистика
        self.notifications_sent = 0
        self.password_resets = 0
        self.two_factor_auths = 0
        
        # Настройка обработчиков
        if self.application:
            self._setup_handlers()
        
        self.logger.info("🔔 Notification Controller v3.0 инициализирован")
    
    def _setup_handlers(self):
        """Настройка обработчиков команд"""
        if not self.application:
            return
        
        # Основные команды
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        
        # Команды для супер-админов
        self.application.add_handler(CommandHandler("send_notification", self.send_notification_command))
        self.application.add_handler(CommandHandler("stats", self.stats_command))
        
        # Обработчики кнопок
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start"""
        user_id = update.effective_user.id
        
        # Проверяем, является ли пользователь супер-админом
        if not self._is_super_admin(user_id):
            await update.message.reply_text("❌ У вас нет доступа к этому боту")
            return
        
        welcome_message = """
🔔 <b>Notification Controller v3.0</b>

Добро пожаловать в систему уведомлений!

<b>Доступные команды:</b>
/help - Справка по командам
/status - Статус системы
/send_notification - Отправить уведомление
/stats - Статистика уведомлений

<b>Функции:</b>
• Восстановление паролей через Telegram
• Двухфакторная аутентификация
• Общие уведомления пользователям
        """
        
        await update.message.reply_text(welcome_message, parse_mode=ParseMode.HTML)
        self.notifications_sent += 1
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /help"""
        user_id = update.effective_user.id
        
        if not self._is_super_admin(user_id):
            await update.message.reply_text("❌ У вас нет доступа к этому боту")
            return
        
        help_message = """
📚 <b>Notification Controller v3.0 - Справка</b>

<b>ОСНОВНЫЕ КОМАНДЫ:</b>
/start - Запуск бота
/help - Эта справка
/status - Статус системы уведомлений
/stats - Статистика уведомлений

<b>АДМИНИСТРАТОРСКИЕ КОМАНДЫ:</b>
/send_notification - Отправить уведомление пользователю

<b>ФУНКЦИИ СИСТЕМЫ:</b>
• Восстановление паролей через Telegram
• Двухфакторная аутентификация
• Уведомления о важных событиях
• Мониторинг системы безопасности

<b>ДОСТУП:</b>
Только для супер-админов системы
        """
        
        await update.message.reply_text(help_message, parse_mode=ParseMode.HTML)
        self.notifications_sent += 1
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /status"""
        user_id = update.effective_user.id
        
        if not self._is_super_admin(user_id):
            await update.message.reply_text("❌ У вас нет доступа к этому боту")
            return
        
        # Получаем статистику
        total_users = len(self.security_system.get_all_users())
        active_codes = len(self.reset_codes)
        
        status_message = f"""
🔔 <b>Notification Controller v3.0 - Статус</b>

<b>СИСТЕМА УВЕДОМЛЕНИЙ:</b>
• Статус: {'🟢 Активна' if self.application else '🔴 Недоступна'}
• Telegram Bot: {'✅ Подключен' if self.telegram_token else '❌ Не настроен'}

<b>СТАТИСТИКА:</b>
• Всего пользователей: {total_users}
• Активных кодов восстановления: {active_codes}
• Отправлено уведомлений: {self.notifications_sent}
• Восстановлений паролей: {self.password_resets}
• 2FA аутентификаций: {self.two_factor_auths}

<b>ФУНКЦИИ:</b>
• Восстановление паролей: ✅
• Двухфакторная аутентификация: ✅
• Общие уведомления: ✅
• Email уведомления: ⏳ В разработке
        """
        
        await update.message.reply_text(status_message, parse_mode=ParseMode.HTML)
        self.notifications_sent += 1
    
    async def send_notification_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /send_notification"""
        user_id = update.effective_user.id
        
        if not self._is_super_admin(user_id):
            await update.message.reply_text("❌ У вас нет доступа к этому боту")
            return
        
        # Создаем клавиатуру для выбора типа уведомления
        keyboard = [
            [InlineKeyboardButton("📧 Восстановление пароля", callback_data="send_password_reset")],
            [InlineKeyboardButton("🔐 2FA код", callback_data="send_2fa_code")],
            [InlineKeyboardButton("📢 Общее уведомление", callback_data="send_general_notification")],
            [InlineKeyboardButton("❌ Отмена", callback_data="cancel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🔔 <b>Отправка уведомления</b>\n\nВыберите тип уведомления:",
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
        self.notifications_sent += 1
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /stats"""
        user_id = update.effective_user.id
        
        if not self._is_super_admin(user_id):
            await update.message.reply_text("❌ У вас нет доступа к этому боту")
            return
        
        # Получаем детальную статистику
        total_users = len(self.security_system.get_all_users())
        active_codes = len(self.reset_codes)
        
        # Очищаем истекшие коды
        self._cleanup_expired_codes()
        
        stats_message = f"""
📊 <b>Статистика уведомлений</b>

<b>ОБЩАЯ СТАТИСТИКА:</b>
• Всего пользователей: {total_users}
• Активных кодов: {active_codes}
• Отправлено уведомлений: {self.notifications_sent}

<b>ПО ТИПАМ:</b>
• Восстановления паролей: {self.password_resets}
• 2FA аутентификации: {self.two_factor_auths}
• Общие уведомления: {self.notifications_sent - self.password_resets - self.two_factor_auths}

<b>СИСТЕМА:</b>
• Telegram Bot: {'✅ Активен' if self.application else '❌ Недоступен'}
• Время работы: {datetime.now().strftime('%H:%M:%S')}
        """
        
        await update.message.reply_text(stats_message, parse_mode=ParseMode.HTML)
        self.notifications_sent += 1
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик нажатий кнопок"""
        query = update.callback_query
        user_id = query.from_user.id
        
        if not self._is_super_admin(user_id):
            await query.answer("❌ У вас нет доступа к этому боту")
            return
        
        await query.answer()
        
        if query.data == "send_password_reset":
            await self._handle_password_reset_request(query)
        elif query.data == "send_2fa_code":
            await self._handle_2fa_request(query)
        elif query.data == "send_general_notification":
            await self._handle_general_notification_request(query)
        elif query.data == "cancel":
            await query.edit_message_text("❌ Отправка уведомления отменена")
    
    async def _handle_password_reset_request(self, query):
        """Обработка запроса восстановления пароля"""
        await query.edit_message_text(
            "🔐 <b>Восстановление пароля</b>\n\n"
            "Эта функция автоматически вызывается из веб-интерфейса.\n"
            "Пользователи могут запросить восстановление пароля на странице входа.",
            parse_mode=ParseMode.HTML
        )
    
    async def _handle_2fa_request(self, query):
        """Обработка запроса 2FA"""
        await query.edit_message_text(
            "🔐 <b>Двухфакторная аутентификация</b>\n\n"
            "Эта функция автоматически вызывается при входе в систему.\n"
            "Пользователи получают код подтверждения в Telegram.",
            parse_mode=ParseMode.HTML
        )
    
    async def _handle_general_notification_request(self, query):
        """Обработка запроса общего уведомления"""
        await query.edit_message_text(
            "📢 <b>Общее уведомление</b>\n\n"
            "Эта функция будет доступна в следующих версиях.\n"
            "Планируется отправка уведомлений всем пользователям.",
            parse_mode=ParseMode.HTML
        )
    
    def _is_super_admin(self, user_id: int) -> bool:
        """Проверка, является ли пользователь супер-админом"""
        try:
            users = self.security_system.get_all_users()
            for user in users:
                if user.user_id == user_id and user.role == 'super_admin':
                    return True
            return False
        except Exception as e:
            self.logger.error(f"Ошибка проверки прав доступа: {e}")
            return False
    
    def _cleanup_expired_codes(self):
        """Очистка истекших кодов восстановления"""
        current_time = datetime.now()
        expired_codes = []
        
        for user_id, code_data in self.reset_codes.items():
            if current_time > code_data['expires']:
                expired_codes.append(user_id)
        
        for user_id in expired_codes:
            del self.reset_codes[user_id]
    
    async def send_password_reset_code(self, telegram_user_id: int, reset_code: str) -> bool:
        """Отправка кода восстановления пароля"""
        try:
            if not self.application:
                self.logger.error("Telegram бот не инициализирован")
                return False
            
            # Сохраняем код на 10 минут
            self.reset_codes[telegram_user_id] = {
                'code': reset_code,
                'expires': datetime.now().timestamp() + 600  # 10 минут
            }
            
            # Отправляем сообщение
            message = f"""
🔐 <b>Восстановление пароля</b>

Ваш код восстановления: <code>{reset_code}</code>

⏰ Код действителен 10 минут
🔒 Не передавайте код третьим лицам

Если вы не запрашивали восстановление пароля, проигнорируйте это сообщение.
            """
            
            bot = self.application.bot
            await bot.send_message(
                chat_id=telegram_user_id,
                text=message,
                parse_mode=ParseMode.HTML
            )
            
            self.password_resets += 1
            self.logger.info(f"Код восстановления отправлен пользователю {telegram_user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка отправки кода восстановления: {e}")
            return False
    
    async def send_2fa_code(self, telegram_user_id: int, code: str) -> bool:
        """Отправка кода двухфакторной аутентификации"""
        try:
            if not self.application:
                self.logger.error("Telegram бот не инициализирован")
                return False
            
            message = f"""
🔐 <b>Двухфакторная аутентификация</b>

Ваш код подтверждения: <code>{code}</code>

⏰ Код действителен 5 минут
🔒 Введите код в веб-интерфейсе для завершения входа
            """
            
            bot = self.application.bot
            await bot.send_message(
                chat_id=telegram_user_id,
                text=message,
                parse_mode=ParseMode.HTML
            )
            
            self.two_factor_auths += 1
            self.logger.info(f"2FA код отправлен пользователю {telegram_user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка отправки 2FA кода: {e}")
            return False
    
    async def start_bot(self):
        """Запуск бота"""
        if not self.application:
            self.logger.error("Telegram бот не может быть запущен - токен не найден")
            return False
        
        try:
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            
            self.logger.info("🔔 Notification Controller запущен")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка запуска бота: {e}")
            return False
    
    async def stop_bot(self):
        """Остановка бота"""
        if not self.application:
            return
        
        try:
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
            
            self.logger.info("🔔 Notification Controller остановлен")
            
        except Exception as e:
            self.logger.error(f"Ошибка остановки бота: {e}")

# Глобальный экземпляр контроллера
notification_controller = None

def get_notification_controller():
    """Получение экземпляра контроллера уведомлений"""
    global notification_controller
    if notification_controller is None:
        notification_controller = NotificationController()
    return notification_controller

async def main():
    """Основная функция для запуска бота"""
    controller = get_notification_controller()
    await controller.start_bot()

if __name__ == "__main__":
    asyncio.run(main())
