# v1.0 - Менеджер настроек торговых ботов
"""
Модуль для управления настройками торговых ботов.
Интегрируется с реальной логикой торговли.
"""

import json
import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from core.log_helper import build_logger

class BotSettingsManager:
    def __init__(self, user_id: int):
        """
        Инициализация менеджера настроек бота
        
        Args:
            user_id: ID пользователя
        """
        self.user_id = user_id
        self.logger = build_logger(f"bot_settings_manager_{user_id}")
        self.settings_dir = "data/bot_settings"
        
        # Создаем папку для настроек если не существует
        os.makedirs(self.settings_dir, exist_ok=True)
    
    def save_bot_settings(self, bot_id: str, settings: Dict[str, Any]) -> bool:
        """
        Сохранение настроек бота
        
        Args:
            bot_id: ID бота
            settings: Настройки бота
            
        Returns:
            bool: True если успешно сохранено
        """
        try:
            # Добавляем метаданные
            full_settings = {
                'bot_id': bot_id,
                'user_id': self.user_id,
                'settings': settings,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            # Сохраняем в файл
            settings_file = os.path.join(self.settings_dir, f"{bot_id}_settings.json")
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(full_settings, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"✅ Настройки бота {bot_id} сохранены")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка сохранения настроек бота {bot_id}: {e}")
            return False
    
    def load_bot_settings(self, bot_id: str) -> Optional[Dict[str, Any]]:
        """
        Загрузка настроек бота
        
        Args:
            bot_id: ID бота
            
        Returns:
            Dict с настройками или None если не найдено
        """
        try:
            settings_file = os.path.join(self.settings_dir, f"{bot_id}_settings.json")
            if not os.path.exists(settings_file):
                return None
            
            with open(settings_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return data.get('settings', {})
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка загрузки настроек бота {bot_id}: {e}")
            return None
    
    def get_trading_pairs(self, bot_id: str) -> List[str]:
        """
        Получение торговых пар бота
        
        Args:
            bot_id: ID бота
            
        Returns:
            List торговых пар
        """
        settings = self.load_bot_settings(bot_id)
        if not settings:
            return []
        
        return settings.get('trading_pairs', [])
    
    def get_bot_mode(self, bot_id: str) -> str:
        """
        Получение режима работы бота
        
        Args:
            bot_id: ID бота
            
        Returns:
            str: Режим работы (conservative, base, aggressive, auto)
        """
        settings = self.load_bot_settings(bot_id)
        if not settings:
            return 'base'
        
        return settings.get('mode', 'base')
    
    def get_total_capital(self, bot_id: str) -> float:
        """
        Получение общего капитала бота
        
        Args:
            bot_id: ID бота
            
        Returns:
            float: Общий капитал
        """
        settings = self.load_bot_settings(bot_id)
        if not settings:
            return 1000.0
        
        return float(settings.get('total_capital', 1000.0))
    
    def determine_mode_by_balance(self, balance: float) -> str:
        """
        Определение режима работы на основе баланса
        
        Args:
            balance: Текущий баланс
            
        Returns:
            str: Рекомендуемый режим
        """
        if balance < 100:
            return 'conservative'  # Малый баланс - консервативный режим
        elif balance < 1000:
            return 'base'          # Средний баланс - базовый режим
        elif balance < 10000:
            return 'aggressive'    # Большой баланс - агрессивный режим
        else:
            return 'aggressive'    # Очень большой баланс - агрессивный режим
    
    def calculate_capital_distribution(self, bot_id: str, current_balance: Optional[float] = None) -> Dict[str, Dict[str, Any]]:
        """
        Расчет распределения капитала по парам
        
        Args:
            bot_id: ID бота
            current_balance: Текущий баланс (если None, берется из настроек)
            
        Returns:
            Dict с распределением капитала по парам
        """
        settings = self.load_bot_settings(bot_id)
        if not settings:
            return {}
        
        trading_pairs = settings.get('trading_pairs', [])
        if not trading_pairs:
            return {}
        
        mode = settings.get('mode', 'base')
        total_capital = current_balance or settings.get('total_capital', 1000.0)
        
        # Если режим автоматический, определяем на основе баланса
        if mode == 'auto':
            mode = self.determine_mode_by_balance(total_capital)
        
        # Веса для разных режимов
        mode_weights = {
            'conservative': {'base': 0.6, 'high': 0.3, 'low': 0.1},
            'base': {'base': 0.5, 'high': 0.4, 'low': 0.1},
            'aggressive': {'base': 0.3, 'high': 0.6, 'low': 0.1}
        }
        
        weights = mode_weights.get(mode, mode_weights['base'])
        
        # Определяем приоритеты пар
        pair_priorities = {}
        for pair in trading_pairs:
            if 'BTC' in pair or 'ETH' in pair:
                pair_priorities[pair] = 'high'
            elif 'USDT' in pair:
                pair_priorities[pair] = 'base'
            else:
                pair_priorities[pair] = 'low'
        
        # Распределяем капитал
        distribution = {}
        for pair in trading_pairs:
            priority = pair_priorities.get(pair, 'base')
            percentage = weights[priority] * 100 / len(trading_pairs)
            amount = (total_capital * percentage) / 100
            
            distribution[pair] = {
                'percentage': percentage,
                'amount': amount,
                'status': 'active',
                'priority': priority,
                'mode': mode
            }
        
        return distribution
    
    def update_bot_balance(self, bot_id: str, new_balance: float) -> bool:
        """
        Обновление баланса бота и пересчет режима
        
        Args:
            bot_id: ID бота
            new_balance: Новый баланс
            
        Returns:
            bool: True если успешно обновлено
        """
        try:
            settings = self.load_bot_settings(bot_id)
            if not settings:
                return False
            
            # Обновляем баланс
            settings['total_capital'] = new_balance
            
            # Если режим автоматический, пересчитываем
            if settings.get('mode') == 'auto':
                new_mode = self.determine_mode_by_balance(new_balance)
                settings['mode'] = new_mode
                self.logger.info(f"🤖 Автоматически изменен режим бота {bot_id} на {new_mode} (баланс: ${new_balance})")
            
            # Сохраняем обновленные настройки
            return self.save_bot_settings(bot_id, settings)
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка обновления баланса бота {bot_id}: {e}")
            return False
    
    def get_bot_settings(self, bot_id: str) -> Optional[Dict[str, Any]]:
        """
        Получение настроек бота (алиас для load_bot_settings)
        
        Args:
            bot_id: ID бота
            
        Returns:
            Dict с настройками или None если не найдено
        """
        return self.load_bot_settings(bot_id)
    
    def get_bot_status(self, bot_id: str) -> Dict[str, Any]:
        """
        Получение полного статуса бота
        
        Args:
            bot_id: ID бота
            
        Returns:
            Dict с полным статусом бота
        """
        settings = self.load_bot_settings(bot_id)
        if not settings:
            return {}
        
        trading_pairs = settings.get('trading_pairs', [])
        mode = settings.get('mode', 'base')
        total_capital = settings.get('total_capital', 1000.0)
        
        # Если режим автоматический, определяем текущий
        if mode == 'auto':
            mode = self.determine_mode_by_balance(total_capital)
        
        # Рассчитываем распределение
        distribution = self.calculate_capital_distribution(bot_id, total_capital)
        
        return {
            'bot_id': bot_id,
            'mode': mode,
            'total_capital': total_capital,
            'trading_pairs': trading_pairs,
            'distribution': distribution,
            'pairs_count': len(trading_pairs),
            'active_pairs': len([p for p in distribution.values() if p.get('status') == 'active']),
            'last_updated': settings.get('updated_at', 'Н/Д')
        }


