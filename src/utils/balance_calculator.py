#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Калькулятор реального баланса из API ключей
"""

import json
import os
from typing import Dict, List, Tuple

class BalanceCalculator:
    """Калькулятор баланса с реальными данными"""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.api_keys_file = f'data/api_keys/user_{user_id}_keys.json'
        
    def get_real_balance(self) -> Dict:
        """Получить реальный баланс пользователя"""
        
        if not os.path.exists(self.api_keys_file):
            return {
                'total_usdt': 0.0,
                'connected_exchanges': 0,
                'currencies': {},
                'error': 'API ключи не найдены'
            }
        
        try:
            with open(self.api_keys_file, 'r', encoding='utf-8') as f:
                keys_data = json.load(f)
            
            total_usdt = 0.0
            currencies = {}
            connected_exchanges = 0
            
            for key_name, key_info in keys_data.items():
                exchange = key_info.get('exchange', 'unknown')
                mode = key_info.get('mode', 'unknown')
                balance_info = key_info.get('balance_info', {})
                
                if balance_info:
                    connected_exchanges += 1
                    total_balance = balance_info.get('total_balance', {})
                    
                    # Конвертируем все в USDT эквивалент
                    usdt_equivalent = self._calculate_usdt_equivalent(total_balance)
                    total_usdt += usdt_equivalent
                    
                    # Собираем валюты
                    for currency, amount in total_balance.items():
                        if float(amount) > 0:
                            if currency not in currencies:
                                currencies[currency] = 0.0
                            currencies[currency] += float(amount)
            
            return {
                'total_usdt': round(total_usdt, 2),
                'connected_exchanges': connected_exchanges,
                'currencies': currencies,
                'success': True
            }
            
        except Exception as e:
            return {
                'total_usdt': 0.0,
                'connected_exchanges': 0,
                'currencies': {},
                'error': f'Ошибка чтения баланса: {str(e)}'
            }
    
    def _calculate_usdt_equivalent(self, balance: Dict) -> float:
        """Конвертировать баланс в USDT эквивалент"""
        
        usdt_equivalent = 0.0
        
        # Прямые USDT эквиваленты
        usdt_currencies = ['USDT', 'TUSD', 'USDC', 'PAX', 'USDK', 'BUSD']
        for currency in usdt_currencies:
            if currency in balance:
                usdt_equivalent += float(balance[currency])
        
        # Примерные курсы для основных валют (можно заменить на реальные API)
        crypto_rates = {
            'BTC': 45000.0,  # Примерный курс BTC/USDT
            'ETH': 3000.0,   # Примерный курс ETH/USDT
            'BNB': 300.0,    # Примерный курс BNB/USDT
            'ADA': 0.5,      # Примерный курс ADA/USDT
            'SOL': 100.0,    # Примерный курс SOL/USDT
            'DOT': 6.0,      # Примерный курс DOT/USDT
            'MATIC': 0.8,    # Примерный курс MATIC/USDT
            'AVAX': 25.0,    # Примерный курс AVAX/USDT
            'LINK': 15.0,    # Примерный курс LINK/USDT
            'UNI': 8.0,      # Примерный курс UNI/USDT
            'ATOM': 12.0,    # Примерный курс ATOM/USDT
            'NEAR': 3.0,     # Примерный курс NEAR/USDT
            'FTM': 0.3,      # Примерный курс FTM/USDT
            'ALGO': 0.2,     # Примерный курс ALGO/USDT
            'VET': 0.03,     # Примерный курс VET/USDT
            'ICP': 4.0,      # Примерный курс ICP/USDT
            'FIL': 5.0,      # Примерный курс FIL/USDT
            'TRX': 0.1,      # Примерный курс TRX/USDT
            'XRP': 0.6,      # Примерный курс XRP/USDT
            'LTC': 70.0,     # Примерный курс LTC/USDT
            'DOGE': 0.08,    # Примерный курс DOGE/USDT
            'SHIB': 0.00001  # Примерный курс SHIB/USDT
        }
        
        for currency, amount in balance.items():
            if currency in crypto_rates and currency not in usdt_currencies:
                usdt_equivalent += float(amount) * crypto_rates[currency]
        
        return usdt_equivalent
    
    def get_detailed_balance(self) -> Dict:
        """Получить детальный баланс по биржам"""
        
        if not os.path.exists(self.api_keys_file):
            return {'exchanges': [], 'error': 'API ключи не найдены'}
        
        try:
            with open(self.api_keys_file, 'r', encoding='utf-8') as f:
                keys_data = json.load(f)
            
            exchanges = []
            
            for key_name, key_info in keys_data.items():
                exchange = key_info.get('exchange', 'unknown')
                mode = key_info.get('mode', 'unknown')
                balance_info = key_info.get('balance_info', {})
                
                if balance_info:
                    total_balance = balance_info.get('total_balance', {})
                    usdt_equivalent = self._calculate_usdt_equivalent(total_balance)
                    
                    # Топ-5 активов
                    sorted_assets = sorted(
                        total_balance.items(), 
                        key=lambda x: float(x[1]), 
                        reverse=True
                    )
                    
                    top_assets = []
                    for asset, amount in sorted_assets[:5]:
                        if float(amount) > 0:
                            top_assets.append({
                                'currency': asset,
                                'amount': float(amount),
                                'usdt_value': float(amount) * (1.0 if asset in ['USDT', 'TUSD', 'USDC', 'PAX', 'USDK', 'BUSD'] else 0.0)  # Упрощенный расчет
                            })
                    
                    exchanges.append({
                        'name': f"{exchange.upper()}/{mode.upper()}",
                        'key_id': key_name,
                        'usdt_equivalent': round(usdt_equivalent, 2),
                        'total_assets': len([k for k, v in total_balance.items() if float(v) > 0]),
                        'top_assets': top_assets,
                        'status': 'connected'
                    })
            
            return {
                'exchanges': exchanges,
                'total_exchanges': len(exchanges),
                'success': True
            }
            
        except Exception as e:
            return {
                'exchanges': [],
                'error': f'Ошибка чтения детального баланса: {str(e)}'
            }



