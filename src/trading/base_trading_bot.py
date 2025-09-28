# v3.0 (+адаптивная система торговли, режимы работы, динамические параметры)
"""
Базовый класс для торговых ботов.
v3.0: Добавлена адаптивная система с тремя режимами торговли (консервативный, базовый, агрессивный).
"""
import ccxt.async_support as ccxt
import asyncio
import time
import logging
import signal
import os
import sys
import json
import math
import collections
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

# Импорты из текущего проекта
from core.log_helper import build_logger
from core.config_manager import ConfigManager
from core.exchange_mode_manager import exchange_mode_manager

# Загрузка переменных окружения
from dotenv import load_dotenv
load_dotenv()

@dataclass
class TradeEvent:
    """Событие сделки"""
    ts: float
    symbol: str
    side: str  # buy/sell
    price: float
    qty: float
    pnl: float = 0.0

class BaseTradingBot:
    """
    Базовый класс для торговых ботов.
    v3.0: Добавлена адаптивная система торговли с режимами.
    """

    def __init__(self, bot_type: str, user_id: int, config: Dict[str, any] = None):
        """
        Базовый класс для торговых ботов.
        :param bot_type: Тип бота ('grid' или 'scalp')
        :param user_id: ID пользователя
        :param config: Конфигурация бота
        """
        self.bot_type = bot_type
        self.user_id = user_id
        
        # Настройка логирования
        self.logger = build_logger(f"{bot_type}_bot_{user_id}")
        
        # Загрузка конфигурации
        self.config_manager = ConfigManager()
        self.config = config or self.config_manager.get_config()
        
        # v3.0: Адаптивная система
        self.current_mode = "base"
        self.mode_switch_count = 0
        self.last_mode_switch = 0
        self.market_analysis_history = []
        
        # Состояние бота
        self.running = True
        self.last_notification = 0
        
        # Капитал
        self.total_capital = 0
        self.working_capital = 0
        self.reserve_capital = 0
        self.allocated_capital = {}  # {symbol: float}
        self.last_redistribution = 0
        self.redistribution_interval = self.config.get('redistribution_interval', 1800)  # 30 минут
        
        # Буфер для сделок за 24 часа
        self.trades_24h: List[TradeEvent] = []
        
        # Кэширование баланса
        self._balance_cache = {'data': None, 'time': 0}
        
        # Дедупликация логов
        self._last_log_msg = ""
        
        # Инициализация биржи (будет настроена через exchange_mode_manager)
        self.ex = None
        
        # Настройки из конфига
        self.symbols = self.config.get('symbols', ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT', 'ADA/USDT', 'DOT/USDT'])
        
        # Установка обработчиков сигналов
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

    def setup_exchange(self, exchange_name: str, api_key: str, secret: str, passphrase: str = None, mode: str = "demo"):
        """
        Настройка биржи через Exchange Mode Manager
        """
        try:
            self.ex = exchange_mode_manager.create_exchange_instance(
                exchange_name=exchange_name,
                api_key=api_key,
                secret=secret,
                passphrase=passphrase,
                mode=mode
            )
            self.logger.info(f"✅ Биржа {exchange_name} настроена в режиме {mode}")
            return True
        except Exception as e:
            self.logger.error(f"❌ Ошибка настройки биржи {exchange_name}: {e}")
            return False

    async def send_notification(self, msg: str, chat_ids: List[int] = None):
        """Отправка уведомления (заглушка для будущей интеграции с Telegram)"""
        now = time.time()
        if now - self.last_notification < 2:
            await asyncio.sleep(2 - (now - self.last_notification))
        self.last_notification = now
        
        # Логируем уведомление
        self.logger.info(f"📢 NOTIFICATION: {msg}")
        
        # TODO: Интеграция с системой уведомлений

    async def get_balances(self) -> Dict[str, Dict]:
        """
        Получение балансов для всех символов с кэшированием.
        """
        cache_ttl = self.config.get('balance_cache_sec', 60)
        current_time = time.time()
        
        if (self._balance_cache['data'] is not None and
            current_time - self._balance_cache['time'] < cache_ttl):
            self.logger.debug("📊 Использован кэш баланса")
            return self._balance_cache['data']
        
        if not self.ex:
            self.logger.error("❌ Биржа не инициализирована")
            return {}
        
        try:
            bal = self.ex.fetch_balance()
            balances = {}
            for symbol in self.symbols:
                base_currency = symbol.split('/')[0]
                quote_currency = symbol.split('/')[1]
                base_free = bal['free'].get(base_currency, 0)
                base_total = bal['total'].get(base_currency, 0)
                quote_free = bal['free'].get(quote_currency, 0)
                quote_total = bal['total'].get(quote_currency, 0)
                balances[symbol] = {
                    'base': base_total,
                    'quote': quote_total,
                    'free_base': base_free,
                    'free_quote': quote_free
                }
            
            # Обновляем кэш
            self._balance_cache['data'] = balances
            self._balance_cache['time'] = current_time
            return balances
        except Exception as e:
            self.logger.error(f"Ошибка получения балансов: {e}")
            return self._balance_cache['data'] if self._balance_cache['data'] else {}

    async def update_capital(self):
        """Обновление информации о капитале"""
        if not self.ex:
            self.logger.error("❌ Биржа не инициализирована")
            return
            
        try:
            balance = await self.ex.fetch_balance()
            
            # Получаем USDT баланс
            usdt_balance_raw = balance.get('total', {}).get('USDT', 0)
            usdt_balance = float(usdt_balance_raw) if usdt_balance_raw else 0.0
            
            if usdt_balance < 0:
                self.logger.warning(f"⚠️ Отрицательный баланс: {usdt_balance}")
                usdt_balance = 0.0
            
            self.total_capital = usdt_balance
            
            # Логируем детали по символам
            balances = await self.get_balances()
            for symbol in self.symbols:
                symbol_balance = balances.get(symbol, {'base': 0, 'quote': 0})
                try:
                    ticker = await self.ex.fetch_ticker(symbol)
                    price = ticker['last']
                    base_equity = symbol_balance['base'] * price
                    quote_equity = symbol_balance['quote']
                    equity = base_equity + quote_equity
                    self.logger.debug(f"💰 {symbol}: {symbol_balance['base']:.6f} {symbol.split('/')[0]} + {symbol_balance['quote']:.2f} {symbol.split('/')[1]} ≈ {equity:.2f} USDT")
                except Exception as e:
                    self.logger.warning(f"Не удалось получить цену для {symbol}: {e}")
            
            self.logger.info(f"💰 Обновлен капитал: Всего=${self.total_capital:.2f} USDT")
        except Exception as e:
            self.logger.error(f"❌ Ошибка обновления капитала: {e}")

    async def check_min_lot(self, symbol: str, amount: float, price: float) -> bool:
        """
        Проверка соответствия минимальным требованиям биржи
        """
        if not self.ex:
            return False
            
        try:
            market_info = self.ex.market(symbol)
            
            if not market_info:
                self.logger.warning(f"⚠️ {symbol}: Не удалось получить информацию о рынке")
                return False
            
            min_amount = market_info.get('limits', {}).get('amount', {}).get('min', 0)
            min_cost = market_info.get('limits', {}).get('cost', {}).get('min', 0)
            
            if amount < min_amount:
                self.logger.info(f"⚠️ {symbol}: Объем {amount} < минимального {min_amount}")
                return False
                
            cost = amount * price
            if cost < min_cost:
                self.logger.info(f"⚠️ {symbol}: Стоимость {cost:.4f} < минимальной {min_cost}")
                return False
                
            return True
        except Exception as e:
            self.logger.error(f"Ошибка проверки минимального лота для {symbol}: {e}")
            return False

    async def log_trade(self, event: TradeEvent):
        """Логирование сделки"""
        msg = (f"{event.symbol} {'ОТКРЫТИЕ' if event.pnl == 0 else 'ЗАКРЫТИЕ'}\n"
               f"💰 Цена: {event.price:.4f}\n"
               f"📦 Объём: {event.qty:.4f}")
        if event.pnl != 0:
            msg += f"\n📊 PnL: {event.pnl:.2f} $"
            
        # Дедупликация логов
        if msg == self._last_log_msg:
            return
        self._last_log_msg = msg
            
        self.logger.info(msg)
        await self.send_notification(msg)
        
        # Сохраняем сделку в буфер
        self.trades_24h.append(event)

    async def distribute_capital(self):
        """
        Распределение капитала между символами
        """
        self.logger.info(f"🔄 Начало перераспределения капитала для {self.bot_type}...")
        
        total_allocated = 0
        base_capital_per_symbol = self.working_capital / len(self.symbols)
        
        for symbol in self.symbols:
            allocated_capital = base_capital_per_symbol
            # Проверяем лимит экспозиции
            exposure_limit = self.config.get(self.bot_type, {}).get('exposure_limit', 1.0)
            max_allowed_for_symbol = self.total_capital * exposure_limit
            if allocated_capital > max_allowed_for_symbol:
                allocated_capital = max_allowed_for_symbol
                self.logger.info(f"⚠️ {symbol}: Превышен лимит экспозиции, скорректировано до ${allocated_capital:.2f}")
                
            self.allocated_capital[symbol] = allocated_capital
            total_allocated += allocated_capital
            self.logger.info(f"💰 {symbol}: выделено ${allocated_capital:.2f}")
            
        # Обновляем резервный капитал
        self.reserve_capital = self.total_capital - total_allocated
        max_allowed_reserve = self.total_capital * 0.5
        if self.reserve_capital > max_allowed_reserve:
            self.reserve_capital = max_allowed_reserve
        self.logger.info(f"💰 Обновлен резерв: ${self.reserve_capital:.2f} (макс. {max_allowed_reserve:.2f})")
        self.logger.info(f"✅ Перераспределение капитала для {self.bot_type} завершено.")

    async def analyze_market_conditions(self, symbols: List[str]) -> Dict:
        """Анализ рыночных условий для выбора режима торговли"""
        if not self.ex:
            return {'symbols_analysis': {}, 'overall_mode': 'base', 'timestamp': datetime.now().isoformat()}
            
        try:
            analysis_results = {}
            
            for symbol in symbols:
                try:
                    # Получаем данные OHLCV
                    ohlcv = await self.ex.fetch_ohlcv(symbol, '1h', limit=100)
                    if len(ohlcv) < 50:
                        self.logger.warning(f"⚠️ {symbol}: Недостаточно данных OHLCV ({len(ohlcv)} < 50)")
                        continue
                    
                    # Конвертируем в numpy array
                    ohlcv_array = np.array(ohlcv)
                    
                    # Анализируем символ
                    symbol_analysis = await self._analyze_symbol(symbol, ohlcv_array)
                    analysis_results[symbol] = symbol_analysis
                    
                except Exception as e:
                    self.logger.error(f"Ошибка анализа {symbol}: {e}")
                    continue
            
            # Определяем общий режим рынка
            overall_mode = self._determine_overall_mode(analysis_results)
            
            return {
                'symbols_analysis': analysis_results,
                'overall_mode': overall_mode,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка анализа рыночных условий: {e}")
            return {'symbols_analysis': {}, 'overall_mode': 'base', 'timestamp': datetime.now().isoformat()}

    async def _analyze_symbol(self, symbol: str, ohlcv: np.ndarray) -> Dict:
        """Анализ отдельного символа"""
        try:
            closes = ohlcv[:, 4]
            highs = ohlcv[:, 2]
            lows = ohlcv[:, 3]
            volumes = ohlcv[:, 5]
            
            # Простой анализ волатильности
            volatility = self._calculate_volatility(closes, highs, lows)
            volatility_level = self._classify_volatility(volatility)
            
            # Простой анализ тренда
            trend_strength = self._calculate_trend_strength(closes, highs, lows)
            trend_direction = self._determine_trend_direction(closes)
            
            # Анализ объема
            volume_analysis = self._analyze_volume(volumes)
            
            # Определение режима для символа
            symbol_mode = self._determine_symbol_mode(
                volatility_level, trend_strength, volume_analysis
            )
            
            return {
                'symbol': symbol,
                'volatility': volatility,
                'volatility_level': volatility_level,
                'trend_strength': trend_strength,
                'trend_direction': trend_direction,
                'volume_analysis': volume_analysis,
                'recommended_mode': symbol_mode,
                'confidence': self._calculate_confidence(volatility, trend_strength, volume_analysis)
            }
        except Exception as e:
            self.logger.error(f"❌ Ошибка анализа символа {symbol}: {e}")
            return {
                'symbol': symbol,
                'volatility': 0.01,
                'volatility_level': 'medium',
                'trend_strength': 0,
                'trend_direction': 'sideways',
                'volume_analysis': {'level': 'normal', 'trend': 'stable'},
                'recommended_mode': 'base',
                'confidence': 50
            }

    def _calculate_volatility(self, closes: np.ndarray, highs: np.ndarray, lows: np.ndarray) -> float:
        """Расчет волатильности"""
        if len(closes) < 20:
            return 0.01
        
        # Простая волатильность на основе стандартного отклонения
        returns = np.diff(closes) / closes[:-1]
        volatility = np.std(returns)
        
        return volatility

    def _classify_volatility(self, volatility: float) -> str:
        """Классификация уровня волатильности"""
        if volatility < 0.01:
            return 'low'
        elif volatility < 0.03:
            return 'medium'
        else:
            return 'high'

    def _calculate_trend_strength(self, closes: np.ndarray, highs: np.ndarray, lows: np.ndarray) -> float:
        """Расчет силы тренда"""
        if len(closes) < 20:
            return 0
        
        # Простая сила тренда на основе наклона линии тренда
        x = np.arange(len(closes[-20:]))
        y = closes[-20:]
        slope = np.polyfit(x, y, 1)[0]
        
        return abs(slope) / closes[-1] * 100  # Нормализованная сила тренда

    def _determine_trend_direction(self, closes: np.ndarray) -> str:
        """Определение направления тренда"""
        if len(closes) < 20:
            return 'sideways'
        
        # Простое определение тренда
        short_avg = np.mean(closes[-5:])
        long_avg = np.mean(closes[-20:])
        
        if short_avg > long_avg * 1.02:
            return 'uptrend'
        elif short_avg < long_avg * 0.98:
            return 'downtrend'
        else:
            return 'sideways'

    def _analyze_volume(self, volumes: np.ndarray) -> Dict:
        """Анализ объемов торгов"""
        if len(volumes) < 20:
            return {'level': 'normal', 'trend': 'stable'}
        
        avg_volume = np.mean(volumes[-20:])
        current_volume = volumes[-1]
        
        if current_volume > avg_volume * 1.5:
            volume_level = 'high'
        elif current_volume < avg_volume * 0.5:
            volume_level = 'low'
        else:
            volume_level = 'normal'
        
        volume_trend = 'increasing' if current_volume > volumes[-5] else 'decreasing'
        
        return {
            'level': volume_level,
            'trend': volume_trend,
            'current_volume': current_volume,
            'avg_volume': avg_volume
        }

    def _determine_symbol_mode(self, volatility_level: str, trend_strength: float, volume_analysis: Dict) -> str:
        """Определение режима для символа"""
        # Простые правила выбора режима
        if volatility_level == 'high' and volume_analysis['level'] == 'high':
            return 'aggressive'
        elif volatility_level == 'low' and volume_analysis['level'] == 'low':
            return 'conservative'
        else:
            return 'base'

    def _calculate_confidence(self, volatility: float, trend_strength: float, volume_analysis: Dict) -> float:
        """Расчет уверенности в анализе"""
        confidence = 50  # Базовая уверенность
        
        if volatility > 0.01:
            confidence += 20
        
        if trend_strength > 1.0:
            confidence += 20
        
        if volume_analysis['level'] == 'high':
            confidence += 10
        
        return min(confidence, 100)

    def _determine_overall_mode(self, symbols_analysis: Dict) -> str:
        """Определение общего режима на основе анализа всех символов"""
        if not symbols_analysis:
            return 'base'
        
        # Подсчет режимов
        mode_counts = {'conservative': 0, 'base': 0, 'aggressive': 0}
        total_confidence = 0
        
        for symbol, analysis in symbols_analysis.items():
            mode = analysis['recommended_mode']
            confidence = analysis['confidence']
            
            mode_counts[mode] += confidence
            total_confidence += confidence
        
        # Нормализация
        if total_confidence > 0:
            for mode in mode_counts:
                mode_counts[mode] = mode_counts[mode] / total_confidence
        
        # Выбираем режим с наибольшим весом
        overall_mode = max(mode_counts, key=mode_counts.get)
        
        # Сохраняем историю
        self.market_analysis_history.append({
            'mode': overall_mode,
            'timestamp': datetime.now(),
            'mode_counts': mode_counts
        })
        
        # Ограничиваем историю
        if len(self.market_analysis_history) > 100:
            self.market_analysis_history = self.market_analysis_history[-100:]
        
        return overall_mode

    async def analyze_and_select_mode(self, symbols: List[str]) -> str:
        """Анализ рынка и выбор оптимального режима"""
        try:
            market_analysis = await self.analyze_market_conditions(symbols)
            recommended_mode = market_analysis['overall_mode']
            
            # Обновляем режим
            self._update_mode(recommended_mode)
            
            return self.current_mode
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка анализа режима: {e}")
            return self.current_mode

    def _update_mode(self, new_mode: str):
        """Обновление текущего режима"""
        if self._should_switch_mode(new_mode):
            self.logger.info(f"🔄 Переключение режима: {self.current_mode} -> {new_mode}")
            self.current_mode = new_mode
            self.mode_switch_count += 1
            self.last_mode_switch = time.time()
        else:
            self.logger.debug(f"Режим остался: {self.current_mode} (новый: {new_mode})")

    def _should_switch_mode(self, new_mode: str) -> bool:
        """Проверка, нужно ли переключать режим"""
        if new_mode == self.current_mode:
            return False
        
        current_time = time.time()
        
        # Минимальный интервал между переключениями (5 минут)
        min_interval = 300
        if current_time - self.last_mode_switch < min_interval:
            return False
        
        return True

    def get_mode_parameters(self, bot_type: str) -> Dict:
        """Получение параметров для текущего режима"""
        try:
            if bot_type not in self.config or 'modes' not in self.config[bot_type]:
                return {}
            
            modes = self.config[bot_type]['modes']
            if self.current_mode not in modes:
                return modes.get('base', {})
            
            return modes[self.current_mode]
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения параметров режима: {e}")
            return {}

    async def execute_strategy(self):
        """
        Абстрактный метод для выполнения торговой стратегии.
        Должен быть реализован в дочерних классах.
        """
        raise NotImplementedError("Метод 'execute_strategy' должен быть реализован в дочернем классе")

    async def close_all_positions(self):
        """
        Абстрактный метод для закрытия всех позиций.
        Должен быть реализован в дочерних классах.
        """
        raise NotImplementedError("Метод 'close_all_positions' должен быть реализован в дочернем классе")

    async def run(self):
        """Основной цикл работы бота"""
        if not self.ex:
            self.logger.error("❌ Биржа не инициализирована")
            return
            
        try:
            await self.ex.load_markets()
            await self.update_capital()
            
            # Инициализация капитала
            self.working_capital = self.total_capital * 0.5
            self.reserve_capital = self.total_capital * 0.5
            self.logger.info(f"💰 Инициализация капитала: Всего=${self.total_capital:.2f}, "
                            f"Рабочий=${self.working_capital:.2f}, "
                            f"Резерв=${self.reserve_capital:.2f}")
            
            # Начальное распределение капитала
            await self.distribute_capital()
            
            self.logger.info(f"🟢 {self.bot_type.capitalize()} Bot запущен. Начальный капитал: {self.total_capital:.2f} USDT")
            await self.send_notification(f"🟢 {self.bot_type.capitalize()} Bot запущен. Капитал: {self.total_capital:.2f} USDT")
            
            # Основной цикл
            while self.running:
                try:
                    await self.update_capital()
                    
                    # Периодическое перераспределение капитала
                    current_time = time.time()
                    if current_time - self.last_redistribution > self.redistribution_interval:
                        await self.distribute_capital()
                        self.last_redistribution = current_time
                    
                    # Анализ режима
                    await self.analyze_and_select_mode(self.symbols)
                    
                    # Специфичная логика бота
                    await self.execute_strategy()
                    
                    # Пауза
                    sleep_interval = self.config.get(self.bot_type, {}).get('sleep_interval', 15)
                    await asyncio.sleep(sleep_interval)
                    
                except Exception as e:
                    self.logger.error(f"❌ Ошибка в основном цикле {self.bot_type}: {e}")
                    await asyncio.sleep(30)  # Увеличенная пауза при ошибке
                    
        except Exception as e:
            self.logger.error(f"❌ Критическая ошибка: {e}")
        finally:
            await self._shutdown()

    async def _shutdown(self):
        """Graceful shutdown"""
        self.logger.info(f"🛑 {self.bot_type.capitalize()} graceful shutdown...")
        try:
            await self.close_all_positions()
        except Exception as e:
            self.logger.error(f"Ошибка при закрытии позиций: {e}")
        
        # Закрываем соединения с биржей
        try:
            if hasattr(self, 'ex') and self.ex:
                await self.ex.close()
                self.logger.info("✅ Соединение с биржей закрыто")
        except Exception as e:
            self.logger.error(f"Ошибка закрытия соединения с биржей: {e}")
        
        self.running = False

    def exit_gracefully(self, signum, frame):
        """Обработчик сигналов для graceful shutdown"""
        self.logger.info(f"🛑 {self.bot_type.capitalize()} graceful shutdown (сигнал {signum})")
        self.running = False


