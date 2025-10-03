#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Запуск Grid Bot через API с реальными ключами
"""
import requests
import json
import time

def start_real_bot():
    """Запускаем Grid Bot через API"""
    
    print("🚀 ЗАПУСК GRID BOT ЧЕРЕЗ API")
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
        
        grid_bot = None
        for bot in bots:
            if bot.get('type') == 'grid':
                grid_bot = bot
                break
        
        if grid_bot:
            bot_id = grid_bot.get('id')
            print(f"   🤖 Grid Bot: {bot_id}")
            
            # 3. Запускаем Grid Bot
            print(f"\n3️⃣ Запуск Grid Bot {bot_id}...")
            response = session.post(f"http://localhost:5000/api/bots/{bot_id}/start")
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Grid Bot запущен: {result.get('message', 'OK')}")
                print(f"   🐍 Процесс ID: {result.get('process_id', 'N/A')}")
                
                # 4. Мониторим работу
                print(f"\n4️⃣ Мониторинг работы бота...")
                print("   ⏱️ Нажмите Ctrl+C для остановки мониторинга")
                
                try:
                    for i in range(10):  # Мониторим 10 циклов
                        print(f"\n--- Мониторинг {i+1}/10 ---")
                        
                        # Проверяем статус
                        response = session.get("http://localhost:5000/api/bots/status")
                        if response.status_code == 200:
                            bots_data = response.json()
                            bots = bots_data.get('bots', [])
                            for bot in bots:
                                if bot.get('id') == bot_id:
                                    print(f"   🤖 Статус: {bot.get('status', 'N/A')}")
                                    print(f"   📅 Обновление: {bot.get('last_update', 'N/A')}")
                                    break
                        
                        # Проверяем логи
                        response = session.get(f"http://localhost:5000/api/bots/{bot_id}/logs")
                        if response.status_code == 200:
                            logs = response.json()
                            if logs.get('success'):
                                log_entries = logs.get('logs', [])
                                if log_entries:
                                    print(f"   📝 Последняя запись: {log_entries[-1][:100]}...")
                        
                        time.sleep(3)  # Ждем 3 секунды
                        
                except KeyboardInterrupt:
                    print(f"\n\n⏹️ Мониторинг остановлен пользователем")
                
                # 5. Останавливаем бота
                print(f"\n5️⃣ Остановка Grid Bot...")
                response = session.post(f"http://localhost:5000/api/bots/{bot_id}/stop")
                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ Grid Bot остановлен: {result.get('message', 'OK')}")
                else:
                    print(f"❌ Ошибка остановки: {response.status_code}")
            else:
                print(f"❌ Ошибка запуска: {response.status_code}")
                print(f"Ответ: {response.text[:200]}")
        else:
            print("❌ Grid Bot не найден")
    else:
        print(f"❌ Ошибка получения ботов: {response.status_code}")
    
    print("\n✅ ЗАПУСК ЗАВЕРШЕН!")

if __name__ == "__main__":
    start_real_bot()



