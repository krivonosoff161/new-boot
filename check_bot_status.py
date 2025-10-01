#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Проверка статуса ботов
"""
import requests
import json

def check_bot_status():
    """Проверяем статус ботов"""
    
    print("🔍 ПРОВЕРКА СТАТУСА БОТОВ")
    print("=" * 40)
    
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
    
    # 2. Получаем список ботов
    print("\n2️⃣ Получение списка ботов...")
    response = session.get("http://localhost:5000/api/bots/status")
    if response.status_code == 200:
        bots_data = response.json()
        bots = bots_data.get('bots', [])
        print(f"✅ Найдено ботов: {len(bots)}")
        
        for bot in bots:
            print(f"\n🤖 Бот: {bot.get('name', 'N/A')}")
            print(f"   🆔 ID: {bot.get('id', 'N/A')}")
            print(f"   📊 Тип: {bot.get('type', 'N/A')}")
            print(f"   🟢 Статус: {bot.get('status', 'N/A')}")
            print(f"   📅 Создан: {bot.get('created_at', 'N/A')}")
    else:
        print(f"❌ Ошибка получения ботов: {response.status_code}")
    
    # 3. Проверяем процессы ботов
    print("\n3️⃣ Проверка процессов ботов...")
    response = session.get("http://localhost:5000/api/bots/processes")
    if response.status_code == 200:
        processes = response.json()
        print(f"✅ Процессы получены: {processes.get('success', False)}")
        if processes.get('success'):
            bot_processes = processes.get('bot_processes', [])
            print(f"   🐍 Найдено процессов: {len(bot_processes)}")
            for proc in bot_processes:
                print(f"   📊 {proc.get('bot_id', 'N/A')}: PID {proc.get('pid', 'N/A')} - {proc.get('status', 'N/A')}")
        else:
            print(f"   ❌ Ошибка: {processes.get('error', 'N/A')}")
    else:
        print(f"❌ Ошибка получения процессов: {response.status_code}")
    
    print("\n✅ ПРОВЕРКА ЗАВЕРШЕНА!")

if __name__ == "__main__":
    check_bot_status()

