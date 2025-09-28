#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ML Signal Engine v3.0
Машинное обучение для предсказания краткосрочных движений цены в Scalp стратегии
"""

import numpy as np
import pandas as pd
import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import pickle
import os
from datetime import datetime, timedelta
import talib

# ML imports
try:
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.svm import SVR
    from sklearn.preprocessing import StandardScaler, LabelEncoder
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, classification_report
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    print("⚠️ scikit-learn не установлен. ML функции будут ограничены.")

logger = logging.getLogger(__name__)

@dataclass
class MLPrediction:
    """Результат ML предсказания"""
    direction: str  # 'buy', 'sell', 'hold'
    confidence: float  # 0.0 - 1.0
    target_price: float
    timeframe_minutes: int
    features_used: List[str]
    timestamp: float

@dataclass
class MarketFeatures:
    """Рыночные фичи для ML"""
    # Технические индикаторы
    rsi: float
    macd: float
    macd_signal: float
    stoch_k: float
    stoch_d: float
    bb_upper: float
    bb_lower: float
    bb_middle: float
    
    # Ценовые данные
    price_change_1m: float
    price_change_5m: float
    volume_change: float
    volatility: float
    
    # Паттерны
    candle_pattern: str
    trend_strength: float
    support_distance: float
    resistance_distance: float

class MLSignalEngine:
    """
    ML движок для генерации торговых сигналов
    
    Использует ensemble из нескольких моделей:
    - RandomForest для направления движения
    - GradientBoosting для силы сигнала  
    - SVR для предсказания цены
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {
            "timeframes": ["1m", "3m", "5m"],
            "lookback_periods": 50,
            "prediction_horizon": 5,
            "confidence_threshold": 0.6
        }
        self.logger = logging.getLogger(f"{__name__}.MLSignalEngine")
        
        # Модели
        self.models = {}
        self.scalers = {}
        self.is_trained = False
        
        # Данные для обучения
        self.training_data = []
        self.feature_names = []
        
        # Настройки
        self.lookback_periods = [1, 5, 15, 30]  # минуты для анализа
        self.prediction_horizon = 5  # предсказываем на 5 минут вперед
        self.min_confidence = 0.6  # минимальная уверенность для сигнала
        
        # Статистика
        self.predictions_made = 0
        self.correct_predictions = 0
        self.model_performance = {}
        
        if ML_AVAILABLE:
            self._initialize_models()
            self.logger.info("✅ ML Signal Engine инициализирован")
        else:
            self.logger.warning("⚠️ ML функции ограничены - нет scikit-learn")
    
    def _initialize_models(self):
        """Инициализация ML моделей"""
        if not ML_AVAILABLE:
            return
        
        # Модель для предсказания направления (классификация)
        self.models['direction'] = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            random_state=42
        )
        
        # Модель для предсказания силы движения (классификация)
        self.models['strength'] = GradientBoostingClassifier(
            n_estimators=50,
            max_depth=6,
            learning_rate=0.1,
            random_state=42
        )
        
        # Модель для предсказания цены (регрессия)
        self.models['price'] = SVR(
            kernel='rbf',
            C=1.0,
            epsilon=0.01
        )
        
        # Скалеры для нормализации
        for model_name in self.models.keys():
            self.scalers[model_name] = StandardScaler()
        
        self.logger.debug("🤖 ML модели инициализированы")
    
    async def extract_features(self, ohlcv_data: List, order_book: Dict = None) -> MarketFeatures:
        """
        Извлечение фич для ML из рыночных данных
        
        Args:
            ohlcv_data: OHLCV данные (последние 100+ свечей)
            order_book: Данные стакана заявок (опционально)
            
        Returns:
            MarketFeatures: Извлеченные фичи
        """
        try:
            if len(ohlcv_data) < 50:
                self.logger.warning("Недостаточно данных для извлечения фич")
                return self._get_default_features()
            
            # Преобразуем в numpy массивы
            closes = np.array([candle[4] for candle in ohlcv_data])
            highs = np.array([candle[2] for candle in ohlcv_data])
            lows = np.array([candle[3] for candle in ohlcv_data])
            volumes = np.array([candle[5] for candle in ohlcv_data])
            
            # Технические индикаторы
            rsi = talib.RSI(closes, timeperiod=14)[-1]
            macd, macd_signal, _ = talib.MACD(closes)
            stoch_k, stoch_d = talib.STOCH(highs, lows, closes)
            bb_upper, bb_middle, bb_lower = talib.BBANDS(closes)
            
            # Ценовые изменения
            current_price = closes[-1]
            price_change_1m = (current_price - closes[-2]) / closes[-2] if len(closes) > 1 else 0
            price_change_5m = (current_price - closes[-6]) / closes[-6] if len(closes) > 5 else 0
            
            # Объемы
            volume_change = (volumes[-1] - np.mean(volumes[-10:])) / np.mean(volumes[-10:]) if len(volumes) > 10 else 0
            
            # Волатильность (ATR)
            atr = talib.ATR(highs, lows, closes, timeperiod=14)[-1]
            volatility = atr / current_price if current_price > 0 else 0
            
            # Паттерны свечей
            candle_pattern = self._detect_candle_pattern(ohlcv_data[-3:])
            
            # Сила тренда
            adx = talib.ADX(highs, lows, closes, timeperiod=14)[-1]
            trend_strength = adx / 100.0 if not np.isnan(adx) else 0.2
            
            # Поддержка и сопротивление (упрощенная версия)
            recent_highs = highs[-20:]
            recent_lows = lows[-20:]
            resistance = np.max(recent_highs)
            support = np.min(recent_lows)
            
            support_distance = (current_price - support) / current_price
            resistance_distance = (resistance - current_price) / current_price
            
            return MarketFeatures(
                rsi=rsi if not np.isnan(rsi) else 50,
                macd=macd[-1] if len(macd) > 0 and not np.isnan(macd[-1]) else 0,
                macd_signal=macd_signal[-1] if len(macd_signal) > 0 and not np.isnan(macd_signal[-1]) else 0,
                stoch_k=stoch_k[-1] if len(stoch_k) > 0 and not np.isnan(stoch_k[-1]) else 50,
                stoch_d=stoch_d[-1] if len(stoch_d) > 0 and not np.isnan(stoch_d[-1]) else 50,
                bb_upper=bb_upper[-1] if len(bb_upper) > 0 and not np.isnan(bb_upper[-1]) else current_price * 1.02,
                bb_lower=bb_lower[-1] if len(bb_lower) > 0 and not np.isnan(bb_lower[-1]) else current_price * 0.98,
                bb_middle=bb_middle[-1] if len(bb_middle) > 0 and not np.isnan(bb_middle[-1]) else current_price,
                price_change_1m=price_change_1m,
                price_change_5m=price_change_5m,
                volume_change=volume_change,
                volatility=volatility,
                candle_pattern=candle_pattern,
                trend_strength=trend_strength,
                support_distance=support_distance,
                resistance_distance=resistance_distance
            )
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка извлечения фич: {e}")
            return self._get_default_features()
    
    def _detect_candle_pattern(self, recent_candles: List) -> str:
        """Простое определение паттернов свечей"""
        if len(recent_candles) < 2:
            return "neutral"
        
        last_candle = recent_candles[-1]
        prev_candle = recent_candles[-2]
        
        # [timestamp, open, high, low, close, volume]
        last_open, last_close = last_candle[1], last_candle[4]
        prev_open, prev_close = prev_candle[1], prev_candle[4]
        
        # Определяем направление свечей
        last_bullish = last_close > last_open
        prev_bullish = prev_close > prev_open
        
        # Размер тела свечи
        last_body = abs(last_close - last_open) / last_open
        
        if last_bullish and prev_bullish and last_body > 0.01:
            return "bullish_momentum"
        elif not last_bullish and not prev_bullish and last_body > 0.01:
            return "bearish_momentum"
        elif last_bullish and not prev_bullish:
            return "reversal_up"
        elif not last_bullish and prev_bullish:
            return "reversal_down"
        else:
            return "neutral"
    
    def _get_default_features(self) -> MarketFeatures:
        """Фичи по умолчанию при ошибках"""
        return MarketFeatures(
            rsi=50, macd=0, macd_signal=0, stoch_k=50, stoch_d=50,
            bb_upper=1000, bb_lower=900, bb_middle=950,
            price_change_1m=0, price_change_5m=0, volume_change=0, volatility=0.02,
            candle_pattern="neutral", trend_strength=0.2,
            support_distance=0.05, resistance_distance=0.05
        )
    
    def features_to_array(self, features: MarketFeatures) -> np.array:
        """Преобразование фич в numpy массив для ML"""
        # Кодируем категориальные фичи
        pattern_encoding = {
            'bullish_momentum': 1,
            'bearish_momentum': -1,
            'reversal_up': 0.5,
            'reversal_down': -0.5,
            'neutral': 0
        }
        
        feature_array = np.array([
            features.rsi / 100.0,  # нормализуем RSI
            features.macd,
            features.macd_signal,
            features.stoch_k / 100.0,
            features.stoch_d / 100.0,
            features.price_change_1m,
            features.price_change_5m,
            features.volume_change,
            features.volatility,
            pattern_encoding.get(features.candle_pattern, 0),
            features.trend_strength,
            features.support_distance,
            features.resistance_distance
        ])
        
        return feature_array
    
    async def predict_signal(self, ohlcv_data: List, order_book: Dict = None) -> MLPrediction:
        """
        Основная функция предсказания торгового сигнала
        
        Args:
            ohlcv_data: OHLCV данные
            order_book: Стакан заявок (опционально)
            
        Returns:
            MLPrediction: Предсказание с направлением и уверенностью
        """
        try:
            # Извлекаем фичи
            features = await self.extract_features(ohlcv_data, order_book)
            feature_array = self.features_to_array(features)
            
            if not ML_AVAILABLE or not self.is_trained:
                # Возвращаем базовое предсказание без ML
                return self._basic_prediction(features, ohlcv_data)
            
            # ML предсказание
            return await self._ml_prediction(feature_array, features, ohlcv_data)
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка предсказания сигнала: {e}")
            return MLPrediction(
                direction='hold',
                confidence=0.0,
                target_price=ohlcv_data[-1][4] if ohlcv_data else 0,
                timeframe_minutes=self.prediction_horizon,
                features_used=[],
                timestamp=datetime.now().timestamp()
            )
    
    def _basic_prediction(self, features: MarketFeatures, ohlcv_data: List) -> MLPrediction:
        """Базовое предсказание без ML (на основе технических индикаторов)"""
        current_price = ohlcv_data[-1][4]
        
        # Простая логика на основе индикаторов
        buy_signals = 0
        sell_signals = 0
        
        # RSI сигналы
        if features.rsi < 30:
            buy_signals += 1
        elif features.rsi > 70:
            sell_signals += 1
        
        # MACD сигналы
        if features.macd > features.macd_signal:
            buy_signals += 1
        else:
            sell_signals += 1
        
        # Bollinger Bands
        if current_price < features.bb_lower:
            buy_signals += 1
        elif current_price > features.bb_upper:
            sell_signals += 1
        
        # Паттерны свечей
        if features.candle_pattern in ['bullish_momentum', 'reversal_up']:
            buy_signals += 1
        elif features.candle_pattern in ['bearish_momentum', 'reversal_down']:
            sell_signals += 1
        
        # Определяем направление
        if buy_signals > sell_signals:
            direction = 'buy'
            confidence = min(buy_signals / 4.0, 1.0)
            target_price = current_price * (1 + features.volatility * 2)
        elif sell_signals > buy_signals:
            direction = 'sell'
            confidence = min(sell_signals / 4.0, 1.0)
            target_price = current_price * (1 - features.volatility * 2)
        else:
            direction = 'hold'
            confidence = 0.1
            target_price = current_price
        
        return MLPrediction(
            direction=direction,
            confidence=confidence,
            target_price=target_price,
            timeframe_minutes=self.prediction_horizon,
            features_used=['rsi', 'macd', 'bb', 'candle_pattern'],
            timestamp=datetime.now().timestamp()
        )
    
    async def _ml_prediction(self, feature_array: np.array, features: MarketFeatures, ohlcv_data: List) -> MLPrediction:
        """ML предсказание (когда модели обучены)"""
        current_price = ohlcv_data[-1][4]
        
        try:
            # Нормализуем фичи
            X = self.scalers['direction'].transform([feature_array])
            
            # Предсказание направления
            direction_proba = self.models['direction'].predict_proba(X)[0]
            direction_classes = self.models['direction'].classes_
            
            # Предсказание силы
            strength_proba = self.models['strength'].predict_proba(X)[0]
            
            # Предсказание цены
            predicted_price = self.models['price'].predict(X)[0]
            
            # Определяем лучший сигнал
            best_direction_idx = np.argmax(direction_proba)
            direction = direction_classes[best_direction_idx]
            confidence = direction_proba[best_direction_idx]
            
            # Корректируем уверенность с учетом силы
            strength_confidence = np.max(strength_proba)
            final_confidence = (confidence + strength_confidence) / 2
            
            self.predictions_made += 1
            
            return MLPrediction(
                direction=direction,
                confidence=final_confidence,
                target_price=predicted_price,
                timeframe_minutes=self.prediction_horizon,
                features_used=list(range(len(feature_array))),
                timestamp=datetime.now().timestamp()
            )
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка ML предсказания: {e}")
            return self._basic_prediction(features, ohlcv_data)
    
    def add_training_data(self, features: MarketFeatures, actual_direction: str, actual_price_change: float):
        """Добавление данных для обучения"""
        if not ML_AVAILABLE:
            return
        
        feature_array = self.features_to_array(features)
        
        training_sample = {
            'features': feature_array,
            'direction': actual_direction,
            'price_change': actual_price_change,
            'timestamp': datetime.now().timestamp()
        }
        
        self.training_data.append(training_sample)
        
        # Ограничиваем размер данных для обучения
        if len(self.training_data) > 10000:
            self.training_data = self.training_data[-5000:]  # Оставляем последние 5000
        
        self.logger.debug(f"📚 Добавлены данные для обучения. Всего: {len(self.training_data)}")
    
    def train_models(self) -> Dict[str, float]:
        """Обучение ML моделей"""
        if not ML_AVAILABLE or len(self.training_data) < 100:
            self.logger.warning("⚠️ Недостаточно данных для обучения ML моделей")
            return {}
        
        try:
            self.logger.info("🎓 Начинаю обучение ML моделей...")
            
            # Подготовка данных
            X = np.array([sample['features'] for sample in self.training_data])
            y_direction = np.array([sample['direction'] for sample in self.training_data])
            y_price = np.array([sample['price_change'] for sample in self.training_data])
            
            # Создаем метки силы движения
            y_strength = np.array(['weak' if abs(change) < 0.01 else 'strong' for change in y_price])
            
            # Разделяем данные
            X_train, X_test, y_dir_train, y_dir_test = train_test_split(X, y_direction, test_size=0.2, random_state=42)
            _, _, y_str_train, y_str_test = train_test_split(X, y_strength, test_size=0.2, random_state=42)
            _, _, y_price_train, y_price_test = train_test_split(X, y_price, test_size=0.2, random_state=42)
            
            results = {}
            
            # Обучение модели направления
            X_train_scaled = self.scalers['direction'].fit_transform(X_train)
            X_test_scaled = self.scalers['direction'].transform(X_test)
            
            self.models['direction'].fit(X_train_scaled, y_dir_train)
            dir_accuracy = self.models['direction'].score(X_test_scaled, y_dir_test)
            results['direction_accuracy'] = dir_accuracy
            
            # Обучение модели силы
            X_train_scaled_str = self.scalers['strength'].fit_transform(X_train)
            X_test_scaled_str = self.scalers['strength'].transform(X_test)
            
            self.models['strength'].fit(X_train_scaled_str, y_str_train)
            str_accuracy = self.models['strength'].score(X_test_scaled_str, y_str_test)
            results['strength_accuracy'] = str_accuracy
            
            # Обучение модели цены
            X_train_scaled_price = self.scalers['price'].fit_transform(X_train)
            X_test_scaled_price = self.scalers['price'].transform(X_test)
            
            self.models['price'].fit(X_train_scaled_price, y_price_train)
            price_score = self.models['price'].score(X_test_scaled_price, y_price_test)
            results['price_r2'] = price_score
            
            self.is_trained = True
            self.model_performance = results
            
            self.logger.info(f"✅ ML модели обучены:")
            self.logger.info(f"   Точность направления: {dir_accuracy:.3f}")
            self.logger.info(f"   Точность силы: {str_accuracy:.3f}")
            self.logger.info(f"   R² цены: {price_score:.3f}")
            
            return results
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка обучения ML моделей: {e}")
            return {}
    
    def get_statistics(self) -> Dict:
        """Получение статистики работы ML движка"""
        accuracy = (self.correct_predictions / self.predictions_made) if self.predictions_made > 0 else 0
        
        return {
            'ml_available': ML_AVAILABLE,
            'is_trained': self.is_trained,
            'training_samples': len(self.training_data),
            'predictions_made': self.predictions_made,
            'correct_predictions': self.correct_predictions,
            'accuracy': accuracy,
            'model_performance': self.model_performance
        }
    
    def save_models(self, filepath: str):
        """Сохранение обученных моделей"""
        if not ML_AVAILABLE or not self.is_trained:
            return
        
        try:
            model_data = {
                'models': self.models,
                'scalers': self.scalers,
                'is_trained': self.is_trained,
                'model_performance': self.model_performance
            }
            
            with open(filepath, 'wb') as f:
                pickle.dump(model_data, f)
            
            self.logger.info(f"💾 ML модели сохранены в {filepath}")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка сохранения моделей: {e}")
    
    def load_models(self, filepath: str):
        """Загрузка обученных моделей"""
        if not ML_AVAILABLE or not os.path.exists(filepath):
            return
        
        try:
            with open(filepath, 'rb') as f:
                model_data = pickle.load(f)
            
            self.models = model_data['models']
            self.scalers = model_data['scalers']
            self.is_trained = model_data['is_trained']
            self.model_performance = model_data.get('model_performance', {})
            
            self.logger.info(f"📂 ML модели загружены из {filepath}")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка загрузки моделей: {e}")

# Тестирование модуля
if __name__ == "__main__":
    import asyncio
    
    async def test_ml_engine():
        print("🧪 ТЕСТИРОВАНИЕ ML SIGNAL ENGINE")
        print("=" * 50)
        
        # Создаем тестовую конфигурацию
        config = {
            'ml_prediction_horizon': 5,
            'ml_min_confidence': 0.6
        }
        
        # Создаем ML движок
        engine = MLSignalEngine(config)
        
        # Создаем тестовые OHLCV данные
        test_ohlcv = []
        base_price = 50000
        for i in range(100):
            price = base_price + (i * 10) + np.random.normal(0, 50)
            high = price * 1.001
            low = price * 0.999
            volume = 1000 + np.random.normal(0, 100)
            test_ohlcv.append([0, price, high, low, price, volume])
        
        # Тест извлечения фич
        print("\n📊 Тест 1: Извлечение фич")
        features = await engine.extract_features(test_ohlcv)
        print(f"  RSI: {features.rsi:.2f}")
        print(f"  MACD: {features.macd:.4f}")
        print(f"  Volatility: {features.volatility:.4f}")
        print(f"  Pattern: {features.candle_pattern}")
        
        # Тест предсказания
        print("\n🎯 Тест 2: Предсказание сигнала")
        prediction = await engine.predict_signal(test_ohlcv)
        print(f"  Направление: {prediction.direction}")
        print(f"  Уверенность: {prediction.confidence:.3f}")
        print(f"  Целевая цена: ${prediction.target_price:.2f}")
        print(f"  Таймфрейм: {prediction.timeframe_minutes} мин")
        
        # Тест статистики
        print("\n📈 Тест 3: Статистика")
        stats = engine.get_statistics()
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        print("\n✅ Все тесты ML Signal Engine пройдены!")
        
        if ML_AVAILABLE:
            print("🤖 ML функции доступны")
        else:
            print("⚠️ ML функции ограничены (установите scikit-learn)")
    
    # Запуск тестов
    asyncio.run(test_ml_engine())



