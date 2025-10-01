#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Отладка структуры данных ботов
"""
import requests
import json

def debug_bots_structure():
    """Отлаживаем структуру данных ботов"""
    
    print("🔍 ОТЛАДКА СТРУКТУРЫ ДАННЫХ БОТОВ")
    print("=" * 50)
    
    # Создаем сессию
    session = requests.Session()
    
    # 1. Логинимся
    print("1️⃣ Вход в систему...")
    login_data = {
        'username': 'дмитрий',
        'password': '123'
    }
    
    response = session.post("http://localhost:5000/login", data=login_data)
    if response.status_code == 200:
        print("✅ Вход успешен")
    else:
        print(f"❌ Ошибка входа: {response.status_code}")
        return
    
    # 2. Получаем список ботов с полной отладкой
    print("\n2️⃣ Получение списка ботов...")
    response = session.get("http://localhost:5000/api/bots/status")
    if response.status_code == 200:
        bots_data = response.json()
        print(f"✅ Ответ получен: {response.status_code}")
        print(f"📊 Полные данные ответа:")
        print(json.dumps(bots_data, indent=2, ensure_ascii=False))
        
        bots = bots_data.get('bots', [])
        print(f"\n📋 Найдено ботов: {len(bots)}")
        
        for i, bot in enumerate(bots):
            print(f"\n🤖 Бот {i+1}:")
            print(f"   Ключи: {list(bot.keys())}")
            for key, value in bot.items():
                print(f"   {key}: {value} (тип: {type(value).__name__})")
    else:
        print(f"❌ Ошибка получения ботов: {response.status_code}")
        print(f"Ответ: {response.text}")

if __name__ == "__main__":
    debug_bots_structure()
