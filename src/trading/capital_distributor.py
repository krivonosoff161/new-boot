# v2.0 (+правки: корректная агрегация капитала, working_capital, min_alloc)
"""
Модуль для централизованного и корректного распределения капитала между стратегиями.
v2.0: Исправлена агрегация капитала, добавлены working_capital и min_alloc.
v3.0: Интеграция с Exchange Mode Manager и улучшенная обработка ошибок.
"""
import logging
import asyncio
import ccxt.async_support as ccxt
import os
from typing import Dict, List, Optional, Union, Any
from core.log_helper import build_logger
from core.config_manager import ConfigManager
from core.exchange_mode_manager import exchange_mode_manager

class CapitalDistributor:
    def __init__(self, exchange: ccxt.Exchange = None, user_id: int = None):
        """
        Инициализация Capital Distributor
        
        Args:
            exchange: Экземпляр биржи
            user_id: ID пользователя
        """
        self.ex = exchange
        self.user_id = user_id
        self.logger = build_logger(f"capital_distributor_{user_id}" if user_id else "capital_distributor")
        self.config_manager = ConfigManager()
        self.config = self.config_manager.get_config()

    async def get_total_capital(self) -> float:
        """
        Получает общий капитал один раз из баланса USDT.
        v2.0: Исправлена ошибка дублирования баланса. Используется totalEq.
        v3.0: Улучшена обработка ошибок и валидация данных.
        
        Returns:
            float: Общий капитал в USDT
        """
        if not self.ex:
            self.logger.error("❌ Биржа не инициализирована")
            return 0.0
            
        try:
            # Получаем баланс с обработкой ошибок
            balance = self.ex.fetch_balance({'type': 'spot'})
            
            # Валидация структуры баланса
            if not isinstance(balance, dict):
                self.logger.error("❌ Некорректная структура баланса")
                return 0.0
            
            # Проверяем наличие USDT в балансе
            if 'total' not in balance:
                self.logger.error("❌ Отсутствует секция 'total' в балансе")
                return 0.0
            
            if 'USDT' not in balance['total']:
                self.logger.error("❌ Отсутствует USDT в балансе")
                return 0.0
            
            # Получаем и валидируем значение
            total_usdt_raw = balance['total']['USDT']
            
            if total_usdt_raw is None:
                self.logger.error("❌ USDT баланс равен None")
                return 0.0
            
            try:
                total_usdt = float(total_usdt_raw)
            except (ValueError, TypeError) as e:
                self.logger.error(f"❌ Ошибка конвертации USDT баланса: {e}")
                return 0.0
            
            # Валидация значения
            if total_usdt < 0:
                self.logger.warning(f"⚠️ Отрицательный баланс USDT: {total_usdt}")
                return 0.0
            
            if total_usdt == 0:
                self.logger.warning("⚠️ Нулевой баланс USDT")
                return 0.0
            
            self.logger.info(f"💰 Общий капитал (totalEq): ${total_usdt:.2f} USDT")
            return total_usdt
            
        except ccxt.NetworkError as e:
            self.logger.error(f"❌ Сетевая ошибка при получении баланса: {e}")
            return 0.0
        except ccxt.ExchangeError as e:
            self.logger.error(f"❌ Ошибка биржи при получении баланса: {e}")
            return 0.0
        except Exception as e:
            self.logger.error(f"❌ Неожиданная ошибка при получении общего капитала: {e}")
            return 0.0

    async def distribute_for_strategy(self, strategy_type: str, symbols: list) -> dict:
        """
        Распределяет капитал для конкретной стратегии.
        v2.0: Добавлены working_capital и min_alloc.
        v3.0: Улучшена обработка ошибок и логирование.
        
        Args:
            strategy_type: Тип стратегии ('grid', 'scalp')
            symbols: Список торговых пар
            
        Returns:
            dict: Словарь с распределением капитала по символам
        """
        try:
            total_capital = await self.get_total_capital()
            if total_capital <= 0:
                self.logger.warning("⚠️ Общий капитал равен нулю или отрицателен.")
                return {}

            # Получаем настройки распределения капитала
            capital_split = self.config.get('capital_split', {'grid': 0.5, 'scalp': 0.5})
            working_capital_ratio = self.config.get('working_capital_ratio', 0.5)
            
            working_capital = total_capital * working_capital_ratio
            strategy_share = capital_split.get(strategy_type, 0.5)
            allocated_for_strategy = working_capital * strategy_share

            self.logger.info(f"💰 Общий капитал: ${total_capital:.2f} USDT")
            self.logger.info(f"💰 Рабочий капитал: ${working_capital:.2f} USDT ({working_capital_ratio*100:.1f}%)")
            self.logger.info(f"📊 Доля стратегии '{strategy_type}': {strategy_share*100:.1f}% -> ${allocated_for_strategy:.2f} USDT")

            min_alloc = 50  # Принудительно устанавливаем минимум $50
            base_allocation = allocated_for_strategy / len(symbols) if symbols else 0
            
            self.logger.info(f"🔢 Расчет: общий={total_capital:.2f}, рабочий={working_capital:.2f}, для_стратегии={allocated_for_strategy:.2f}")
            self.logger.info(f"🔢 Символов={len(symbols)}, базовое_выделение={base_allocation:.2f}, минимум={min_alloc}")

            allocations = {}
            skipped_symbols = []

            for symbol in symbols:
                if base_allocation >= min_alloc:
                    allocations[symbol] = base_allocation
                else:
                    skipped_symbols.append(symbol)
                    self.logger.warning(f"⚠️ {symbol}: Пропущена из-за минимального выделения (${base_allocation:.2f} < ${min_alloc})")

            if skipped_symbols and allocations:
                remaining_to_distribute = sum([base_allocation for _ in skipped_symbols])
                bonus_per_active = remaining_to_distribute / len(allocations) if allocations else 0
                for symbol in allocations:
                    allocations[symbol] += bonus_per_active
                self.logger.info(f"🔁 Перераспределено: {len(skipped_symbols)} пар пропущено, капитал перераспределен.")
            elif not allocations:
                self.logger.warning(f"⚠️ Ни одна пара не прошла минимальный порог выделения для стратегии '{strategy_type}'.")

            self.logger.info(f"✅ Распределение для '{strategy_type}' завершено. Всего пар: {len(allocations)}, Пропущено: {len(skipped_symbols)}")
            return allocations

        except Exception as e:
            self.logger.error(f"❌ Ошибка распределения капитала для стратегии '{strategy_type}': {e}")
            return {}

    async def redistribute_capital(self, current_allocations: Dict[str, float], 
                                 performance_data: Dict[str, Dict] = None) -> Dict[str, float]:
        """
        Перераспределение капитала на основе производительности
        
        Args:
            current_allocations: Текущие распределения
            performance_data: Данные о производительности по символам
            
        Returns:
            dict: Новые распределения капитала
        """
        try:
            total_capital = await self.get_total_capital()
            if total_capital <= 0:
                self.logger.warning("⚠️ Общий капитал равен нулю или отрицателен.")
                return current_allocations

            # Если нет данных о производительности, возвращаем текущие распределения
            if not performance_data:
                self.logger.info("📊 Нет данных о производительности, оставляем текущие распределения")
                return current_allocations

            # Анализируем производительность
            performance_scores = {}
            total_score = 0

            for symbol, data in performance_data.items():
                if symbol in current_allocations:
                    # Простой расчет скóра на основе PnL и количества сделок
                    pnl = data.get('pnl', 0)
                    trades_count = data.get('trades_count', 1)
                    win_rate = data.get('win_rate', 0.5)
                    
                    # Базовый скор
                    score = 1.0
                    
                    # Бонус за положительный PnL
                    if pnl > 0:
                        score += pnl / current_allocations[symbol] * 0.1
                    
                    # Бонус за высокий винрейт
                    if win_rate > 0.6:
                        score += 0.2
                    
                    # Штраф за низкий винрейт
                    if win_rate < 0.4:
                        score -= 0.2
                    
                    # Штраф за отсутствие сделок
                    if trades_count == 0:
                        score -= 0.3
                    
                    performance_scores[symbol] = max(score, 0.1)  # Минимальный скор
                    total_score += performance_scores[symbol]

            if total_score == 0:
                self.logger.warning("⚠️ Все скоры производительности равны нулю")
                return current_allocations

            # Перераспределяем капитал
            working_capital_ratio = self.config.get('working_capital_ratio', 0.5)
            working_capital = total_capital * working_capital_ratio
            
            new_allocations = {}
            for symbol, current_allocation in current_allocations.items():
                if symbol in performance_scores:
                    # Взвешенное распределение
                    weight = performance_scores[symbol] / total_score
                    new_allocation = working_capital * weight
                    new_allocations[symbol] = new_allocation
                else:
                    # Сохраняем текущее распределение
                    new_allocations[symbol] = current_allocation

            self.logger.info(f"🔄 Перераспределение капитала завершено")
            for symbol, allocation in new_allocations.items():
                old_allocation = current_allocations.get(symbol, 0)
                change = allocation - old_allocation
                self.logger.info(f"📊 {symbol}: ${old_allocation:.2f} -> ${allocation:.2f} (изменение: {change:+.2f})")

            return new_allocations

        except Exception as e:
            self.logger.error(f"❌ Ошибка перераспределения капитала: {e}")
            return current_allocations

    async def get_symbol_analysis(self, symbols: List[str]) -> Dict[str, Dict]:
        """
        Анализ символов для умного распределения капитала
        
        Args:
            symbols: Список торговых пар
            
        Returns:
            dict: Анализ символов с рекомендациями
        """
        if not self.ex:
            self.logger.error("❌ Биржа не инициализирована")
            return {}

        try:
            analysis = {}
            
            for symbol in symbols:
                try:
                    # Получаем информацию о рынке
                    market = self.ex.market(symbol)
                    ticker = self.ex.fetch_ticker(symbol)
                    
                    # Анализируем ликвидность
                    volume_24h = ticker.get('quoteVolume', 0)
                    spread = (ticker.get('ask', 0) - ticker.get('bid', 0)) / ticker.get('last', 1)
                    
                    # Определяем приоритет символа
                    priority = 'medium'
                    if volume_24h > 1000000:  # Высокий объем
                        priority = 'high'
                    elif volume_24h < 100000:  # Низкий объем
                        priority = 'low'
                    
                    # Анализируем спред
                    liquidity = 'good'
                    if spread > 0.001:  # 0.1% спред
                        liquidity = 'poor'
                    elif spread > 0.0005:  # 0.05% спред
                        liquidity = 'medium'
                    
                    analysis[symbol] = {
                        'priority': priority,
                        'liquidity': liquidity,
                        'volume_24h': volume_24h,
                        'spread': spread,
                        'min_amount': market.get('limits', {}).get('amount', {}).get('min', 0),
                        'min_cost': market.get('limits', {}).get('cost', {}).get('min', 0),
                        'recommended_allocation': self._calculate_recommended_allocation(priority, liquidity, volume_24h)
                    }
                    
                except Exception as e:
                    self.logger.error(f"❌ Ошибка анализа символа {symbol}: {e}")
                    analysis[symbol] = {
                        'priority': 'low',
                        'liquidity': 'poor',
                        'volume_24h': 0,
                        'spread': 0.01,
                        'min_amount': 0,
                        'min_cost': 0,
                        'recommended_allocation': 0.5
                    }
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка анализа символов: {e}")
            return {}

    def _calculate_recommended_allocation(self, priority: str, liquidity: str, volume_24h: float) -> float:
        """
        Расчет рекомендуемого коэффициента распределения для символа
        
        Args:
            priority: Приоритет символа ('high', 'medium', 'low')
            liquidity: Ликвидность ('good', 'medium', 'poor')
            volume_24h: Объем торгов за 24 часа
            
        Returns:
            float: Коэффициент распределения (0.0 - 2.0)
        """
        base_allocation = 1.0
        
        # Корректировка по приоритету
        if priority == 'high':
            base_allocation *= 1.5
        elif priority == 'low':
            base_allocation *= 0.5
        
        # Корректировка по ликвидности
        if liquidity == 'good':
            base_allocation *= 1.2
        elif liquidity == 'poor':
            base_allocation *= 0.7
        
        # Корректировка по объему
        if volume_24h > 10000000:  # Очень высокий объем
            base_allocation *= 1.3
        elif volume_24h < 50000:  # Очень низкий объем
            base_allocation *= 0.6
        
        # Ограничиваем диапазон
        return max(0.1, min(2.0, base_allocation))

    async def smart_distribute_for_strategy(self, strategy_type: str, symbols: list) -> dict:
        """
        Умное распределение капитала с учетом анализа символов
        
        Args:
            strategy_type: Тип стратегии ('grid', 'scalp')
            symbols: Список торговых пар
            
        Returns:
            dict: Словарь с умным распределением капитала
        """
        try:
            # Получаем базовое распределение
            base_allocations = await self.distribute_for_strategy(strategy_type, symbols)
            if not base_allocations:
                return {}

            # Анализируем символы
            symbol_analysis = await self.get_symbol_analysis(symbols)
            
            # Применяем умные коэффициенты
            smart_allocations = {}
            total_coefficient = 0
            
            for symbol, base_allocation in base_allocations.items():
                if symbol in symbol_analysis:
                    coefficient = symbol_analysis[symbol]['recommended_allocation']
                    smart_allocations[symbol] = base_allocation * coefficient
                    total_coefficient += coefficient
                else:
                    smart_allocations[symbol] = base_allocation
                    total_coefficient += 1.0
            
            # Нормализуем распределения
            if total_coefficient > 0:
                total_base = sum(base_allocations.values())
                for symbol in smart_allocations:
                    smart_allocations[symbol] = (smart_allocations[symbol] / total_coefficient) * total_base
            
            self.logger.info(f"🧠 Умное распределение для '{strategy_type}' завершено")
            for symbol, allocation in smart_allocations.items():
                base_allocation = base_allocations.get(symbol, 0)
                change = allocation - base_allocation
                self.logger.info(f"🧠 {symbol}: ${base_allocation:.2f} -> ${allocation:.2f} (изменение: {change:+.2f})")
            
            return smart_allocations
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка умного распределения капитала: {e}")
            return await self.distribute_for_strategy(strategy_type, symbols)


