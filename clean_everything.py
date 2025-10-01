#!/usr/bin/env python3
"""
Полная очистка системы - удаление всех пользователей, ключей и данных
"""

import os
import sqlite3
import shutil
import json

def clean_everything():
    print("🧹 НАЧИНАЕМ ПОЛНУЮ ОЧИСТКУ СИСТЕМЫ")
    print("=" * 50)
    
    # 1. Удаляем базу данных пользователей
    if os.path.exists('secure_users.db'):
        os.remove('secure_users.db')
        print("✅ Удалена база данных secure_users.db")
    else:
        print("ℹ️ База данных secure_users.db не найдена")
    
    # 2. Удаляем папку с API ключами
    if os.path.exists('data/api_keys'):
        shutil.rmtree('data/api_keys')
        print("✅ Удалена папка data/api_keys")
    else:
        print("ℹ️ Папка data/api_keys не найдена")
    
    # 3. Удаляем файлы статуса ботов
    bot_files = [
        'data/bot_status.json',
        'data/bot_configs',
        'data/bot_stats.json'
    ]
    
    for file_path in bot_files:
        if os.path.exists(file_path):
            if os.path.isdir(file_path):
                shutil.rmtree(file_path)
                print(f"✅ Удалена папка {file_path}")
            else:
                os.remove(file_path)
                print(f"✅ Удален файл {file_path}")
        else:
            print(f"ℹ️ {file_path} не найден")
    
    # 4. Удаляем временные файлы
    temp_files = [
        'check_keys.py',
        'clean_everything.py'
    ]
    
    for file_path in temp_files:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"✅ Удален временный файл {file_path}")
    
    # 5. Создаем пустую структуру папок
    os.makedirs('data', exist_ok=True)
    os.makedirs('data/api_keys', exist_ok=True)
    os.makedirs('data/bot_configs', exist_ok=True)
    
    # Создаем пустые файлы
    with open('data/bot_status.json', 'w') as f:
        json.dump({}, f)
    
    with open('data/bot_stats.json', 'w') as f:
        json.dump({}, f)
    
    print("✅ Создана новая структура папок")
    
    print("\n🎉 ОЧИСТКА ЗАВЕРШЕНА!")
    print("Теперь можно заново пройти регистрацию с правильным шифрованием ключей")
    print("=" * 50)

if __name__ == "__main__":
    clean_everything()




