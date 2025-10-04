#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Проверка консоли дашборда
"""

import subprocess
import time
import requests
import threading

def check_dashboard_console():
    """Проверка консоли дашборда"""
    print("🔥 SOVERYN FIELD: ПРОВЕРКА КОНСОЛИ ДАШБОРДА")
    print("=" * 50)
    
    # Запускаем дашборд
    print("\n1. ЗАПУСК ДАШБОРДА:")
    try:
        process = subprocess.Popen(['python', 'run_web.py'], 
                                 stdout=subprocess.PIPE, 
                                 stderr=subprocess.PIPE,
                                 text=True)
        
        # Ждем запуска
        time.sleep(3)
        print("   Дашборд запущен")
        
        # Тестируем вход
        print("\n2. ТЕСТ ВХОДА:")
        session = requests.Session()
        
        login_data = {
            'username': 'дмитрий',
            'password': '123'
        }
        
        response = session.post('http://localhost:5000/login', data=login_data)
        print(f"   Статус: {response.status_code}")
        
        # Ждем для вывода отладочной информации
        time.sleep(2)
        
        # Проверяем вывод
        print("\n3. ПРОВЕРКА ВЫВОДА:")
        try:
            stdout, stderr = process.communicate(timeout=1)
            if stdout:
                print("   STDOUT:")
                print(stdout)
            if stderr:
                print("   STDERR:")
                print(stderr)
        except subprocess.TimeoutExpired:
            print("   Таймаут при чтении вывода")
        
        # Останавливаем дашборд
        process.terminate()
        process.wait()
        
    except Exception as e:
        print(f"   ОШИБКА: {e}")
    
    print("\n" + "=" * 50)
    print("🔥 ПРОВЕРКА КОНСОЛИ ЗАВЕРШЕНА")

if __name__ == "__main__":
    check_dashboard_console()
