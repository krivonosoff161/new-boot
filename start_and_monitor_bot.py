#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Запуск и мониторинг Grid Bot
"""
import requests
import json
import time
import os

def start_and_monitor_bot():
    """Запускаем Grid Bot и мониторим его работу"""
    
    print("🚀 ЗАПУСК И МОНИТОРИНГ GRID BOT")
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
    
    bot_id = "grid_462885677_1759333561"
    
    # 2. Запускаем Grid Bot
    print(f"\n2️⃣ Запуск Grid Bot {bot_id}...")
    response = session.post(f"http://localhost:5000/api/bots/{bot_id}/start")
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Grid Bot запущен: {result.get('message', 'OK')}")
        print(f"   🐍 Процесс ID: {result.get('process_id', 'N/A')}")
    else:
        print(f"❌ Ошибка запуска: {response.status_code}")
        print(f"Ответ: {response.text}")
        return
    
    # 3. Мониторим работу бота
    print(f"\n3️⃣ Мониторинг работы бота...")
    print("   ⏱️ Нажмите Ctrl+C для остановки мониторинга")
    
    try:
        for i in range(30):  # Мониторим 30 секунд
            print(f"\n--- Мониторинг {i+1}/30 ---")
            
            # Проверяем статус бота
            response = session.get("http://localhost:5000/api/bots/status")
            if response.status_code == 200:
                bots_data = response.json()
                bots = bots_data.get('bots', [])
                grid_bot = None
                for bot in bots:
                    if bot.get('id') == bot_id:
                        grid_bot = bot
                        break
                
                if grid_bot:
                    print(f"   🤖 Статус: {grid_bot.get('status', 'N/A')}")
                    print(f"   📅 Последнее обновление: {grid_bot.get('last_update', 'N/A')}")
                else:
                    print("   ❌ Бот не найден в списке")
            
            # Проверяем процессы
            response = session.get("http://localhost:5000/api/bots/processes")
            if response.status_code == 200:
                processes = response.json()
                if processes.get('success'):
                    bot_processes = processes.get('bot_processes', [])
                    grid_process = None
                    for proc in bot_processes:
                        if proc.get('bot_id') == bot_id:
                            grid_process = proc
                            break
                    
                    if grid_process:
                        print(f"   🐍 Процесс: PID {grid_process.get('pid', 'N/A')} - {grid_process.get('status', 'N/A')}")
                    else:
                        print("   ⚠️ Процесс не найден")
            
            # Проверяем логи
            log_file = f"logs/bots/{bot_id}.log"
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    if lines:
                        print(f"   📝 Последняя запись в логе: {lines[-1].strip()}")
                        print(f"   📊 Всего записей в логе: {len(lines)}")
            
            # Проверяем детали бота
            response = session.get(f"http://localhost:5000/api/bots/{bot_id}/details")
            if response.status_code == 200:
                details = response.json()
                if details.get('success'):
                    bot_details = details.get('bot_details', {})
                    balance_info = bot_details.get('balance_info', {})
                    print(f"   💰 Баланс: ${balance_info.get('allocated_capital', 0):.2f}")
                    print(f"   📊 Торговые пары: {len(bot_details.get('trading_pairs', []))}")
            
            time.sleep(2)  # Ждем 2 секунды
            
    except KeyboardInterrupt:
        print(f"\n\n⏹️ Мониторинг остановлен пользователем")
    
    # 4. Останавливаем бота
    print(f"\n4️⃣ Остановка Grid Bot...")
    response = session.post(f"http://localhost:5000/api/bots/{bot_id}/stop")
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Grid Bot остановлен: {result.get('message', 'OK')}")
    else:
        print(f"❌ Ошибка остановки: {response.status_code}")
    
    print("\n✅ МОНИТОРИНГ ЗАВЕРШЕН!")

if __name__ == "__main__":
    start_and_monitor_bot()



