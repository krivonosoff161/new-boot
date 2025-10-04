#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Безопасный менеджер ботов с полным контролем
"""

import json
import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional

class SafeBotManager:
    """Безопасный менеджер ботов"""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.bots_file = 'data/bot_status.json'
        self.configs_dir = 'data/bot_configs'
        self.trading_pairs_file = 'data/trading_pairs.json'
        
        # Создаем директории если не существуют
        os.makedirs(self.configs_dir, exist_ok=True)
    
    def create_bot(self, bot_data: Dict) -> Dict:
        """Создать нового бота в безопасном режиме"""
        
        bot_id = f"{bot_data['bot_type']}_{self.user_id}_{int(datetime.now().timestamp())}"
        
        # Базовые данные бота
        new_bot = {
            'bot_id': bot_id,
            'user_id': self.user_id,
            'username': bot_data.get('username', f'user_{self.user_id}'),
            'bot_type': bot_data['bot_type'],
            'bot_name': bot_data.get('bot_name', f"{bot_data['bot_type']} {bot_id}"),
            'api_key_id': bot_data.get('api_key_id', ''),
            'mode': bot_data.get('mode', 'demo'),
            'trading_pairs': bot_data.get('trading_pairs', ['BTC/USDT']),
            'settings': bot_data.get('settings', {}),
            'status': 'created',
            'created_at': datetime.now().isoformat(),
            'last_update': datetime.now().isoformat(),
            
            # Безопасные настройки
            'safe_mode': True,
            'has_real_trading': False,
            'ready_for_trading': False,
            'trading_instance_class': None,
            'trading_config': None,
            
            # Статистика
            'performance': {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'profit_loss': 0.0,
                'win_rate': 0.0,
                'avg_profit': 0.0,
                'max_drawdown': 0.0
            },
            
            # Автоматизация
            'automation_settings': {
                'auto_rebalance': False,
                'auto_stop_loss': False,
                'auto_take_profit': False,
                'auto_pairs_selection': False,
                'risk_management': True
            }
        }
        
        # Сохраняем бота
        self._save_bot(new_bot)
        
        return {
            'success': True,
            'bot_id': bot_id,
            'message': f'Бот {bot_id} создан в безопасном режиме'
        }
    
    def get_bot_details(self, bot_id: str) -> Dict:
        """Получить детальную информацию о боте"""
        
        bot_info = self._load_bot(bot_id)
        if not bot_info:
            return {'success': False, 'error': 'Бот не найден'}
        
        # Получаем реальный баланс
        from .balance_calculator import BalanceCalculator
        balance_calc = BalanceCalculator(self.user_id)
        real_balance = balance_calc.get_real_balance()
        
        # Получаем торговые пары
        trading_pairs = self._get_available_pairs()
        
        return {
            'success': True,
            'basic_info': {
                'bot_id': bot_info['bot_id'],
                'bot_name': bot_info['bot_name'],
                'bot_type': bot_info['bot_type'],
                'status': bot_info['status'],
                'mode': bot_info['mode'],
                'api_key_id': bot_info['api_key_id'],
                'created_at': bot_info['created_at'],
                'last_update': bot_info['last_update']
            },
            'trading_settings': {
                'capital': bot_info['settings'].get('capital', 5000),
                'risk_level': 'medium',
                'max_pairs': 8,
                'grid_spacing': 0.5,
                'profit_target': 2.0,
                'stop_loss': -5.0,
                'available_balance': real_balance.get('total_usdt', 0),
                'recommended_per_pair': real_balance.get('total_usdt', 0) / 8 if real_balance.get('total_usdt', 0) > 0 else 5000
            },
            'performance': bot_info['performance'],
            'balance_info': {
                'allocated_capital': bot_info['settings'].get('capital', 5000),
                'available_capital': real_balance.get('total_usdt', 0),
                'used_capital': 0,
                'profit_loss': 0
            },
            'risk_management': {
                'max_risk_per_trade': 2.0,
                'total_risk_limit': 10.0,
                'current_risk': 0.0,
                'risk_level': 'medium'
            },
            'current_positions': [],
            'trading_pairs': bot_info['trading_pairs'],
            'available_pairs': trading_pairs,
            'automation_settings': bot_info['automation_settings'],
            'last_update': datetime.now().isoformat()
        }
    
    def update_automation(self, bot_id: str, setting: str, value: bool) -> Dict:
        """Обновить настройки автоматизации"""
        
        bot_info = self._load_bot(bot_id)
        if not bot_info:
            return {'success': False, 'error': 'Бот не найден'}
        
        if setting in bot_info['automation_settings']:
            bot_info['automation_settings'][setting] = value
            bot_info['last_update'] = datetime.now().isoformat()
            self._save_bot(bot_info)
            
            return {
                'success': True,
                'message': f'Настройка {setting} изменена на {value}',
                'automation_settings': bot_info['automation_settings']
            }
        else:
            return {'success': False, 'error': f'Неизвестная настройка: {setting}'}
    
    def get_all_bots(self) -> List[Dict]:
        """Получить список всех ботов пользователя"""
        
        if not os.path.exists(self.bots_file):
            return []
        
        try:
            with open(self.bots_file, 'r', encoding='utf-8') as f:
                all_bots = json.load(f)
            
            user_bots = []
            for bot_id, bot_info in all_bots.items():
                if bot_info.get('user_id') == self.user_id:
                    user_bots.append({
                        'bot_id': bot_id,
                        'bot_name': bot_info.get('bot_name', f'Bot {bot_id}'),
                        'bot_type': bot_info.get('bot_type', 'unknown'),
                        'status': bot_info.get('status', 'unknown'),
                        'created_at': bot_info.get('created_at', ''),
                        'last_update': bot_info.get('last_update', ''),
                        'has_real_trading': bot_info.get('has_real_trading', False),
                        'safe_mode': bot_info.get('safe_mode', True)
                    })
            
            return user_bots
            
        except Exception as e:
            print(f"Ошибка загрузки ботов: {e}")
            return []
    
    def _get_available_pairs(self) -> List[Dict]:
        """Получить доступные торговые пары"""
        
        if not os.path.exists(self.trading_pairs_file):
            return [
                {'symbol': 'BTC/USDT', 'reason': 'Базовая пара', 'score': 9.0},
                {'symbol': 'ETH/USDT', 'reason': 'Базовая пара', 'score': 8.5}
            ]
        
        try:
            with open(self.trading_pairs_file, 'r', encoding='utf-8') as f:
                pairs_data = json.load(f)
            
            return pairs_data.get('recommended', [])
            
        except Exception as e:
            print(f"Ошибка загрузки торговых пар: {e}")
            return [
                {'symbol': 'BTC/USDT', 'reason': 'Базовая пара', 'score': 9.0}
            ]
    
    def _load_bot(self, bot_id: str) -> Optional[Dict]:
        """Загрузить данные бота"""
        
        if not os.path.exists(self.bots_file):
            return None
        
        try:
            with open(self.bots_file, 'r', encoding='utf-8') as f:
                all_bots = json.load(f)
            
            return all_bots.get(bot_id)
            
        except Exception as e:
            print(f"Ошибка загрузки бота {bot_id}: {e}")
            return None
    
    def _save_bot(self, bot_info: Dict) -> None:
        """Сохранить данные бота"""
        
        # Загружаем существующие данные
        all_bots = {}
        if os.path.exists(self.bots_file):
            try:
                with open(self.bots_file, 'r', encoding='utf-8') as f:
                    all_bots = json.load(f)
            except:
                all_bots = {}
        
        # Обновляем данные
        all_bots[bot_info['bot_id']] = bot_info
        
        # Сохраняем
        with open(self.bots_file, 'w', encoding='utf-8') as f:
            json.dump(all_bots, f, ensure_ascii=False, indent=2)
        
        # Сохраняем конфигурацию
        config_file = f"{self.configs_dir}/{bot_info['bot_id']}_config.json"
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(bot_info, f, ensure_ascii=False, indent=2)
















