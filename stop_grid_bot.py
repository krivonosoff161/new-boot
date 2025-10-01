#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Остановка Grid Bot
"""
import requests
import json

def stop_grid_bot():
    """Останавливаем Grid Bot"""
    
    print("🛑 ОСТАНОВКА GRID BOT")
    print("=" * 30)
    
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
    
    # 2. Останавливаем Grid Bot
    print("\n2️⃣ Остановка Grid Bot...")
    bot_id = "grid_462885677_1759333561"
    response = session.post(f"http://localhost:5000/api/bots/{bot_id}/stop")
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Grid Bot остановлен: {result.get('message', 'OK')}")
    else:
        print(f"❌ Ошибка остановки: {response.status_code}")
        print(f"Ответ: {response.text}")
    
    print("\n✅ ОСТАНОВКА ЗАВЕРШЕНА!")

if __name__ == "__main__":
    stop_grid_bot()

