#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Мониторинг логов ботов
"""

import os
import time
import glob
from datetime import datetime

def monitor_bot_logs():
    """Мониторинг логов ботов в реальном времени"""
    
    print("🔍 МОНИТОРИНГ ЛОГОВ БОТОВ")
    print("=" * 50)
    
    # Находим все лог файлы ботов
    log_files = glob.glob('logs/bots/bot_*.log')
    
    if not log_files:
        print("❌ Лог файлы ботов не найдены")
        print("💡 Запустите бота, чтобы создать лог файл")
        return
    
    print(f"📁 Найдено лог файлов: {len(log_files)}")
    for log_file in log_files:
        print(f"   - {log_file}")
    
    print("\n🔄 Мониторинг в реальном времени...")
    print("⏹️ Нажмите Ctrl+C для остановки")
    print("-" * 50)
    
    # Отслеживаем изменения в файлах
    file_positions = {}
    for log_file in log_files:
        file_positions[log_file] = 0
    
    try:
        while True:
            for log_file in log_files:
                if os.path.exists(log_file):
                    try:
                        with open(log_file, 'r', encoding='utf-8') as f:
                            f.seek(file_positions[log_file])
                            new_lines = f.readlines()
                            
                            if new_lines:
                                file_positions[log_file] = f.tell()
                                
                                for line in new_lines:
                                    line = line.strip()
                                    if line:
                                        # Определяем тип сообщения по цвету
                                        if 'ERROR' in line or '❌' in line:
                                            print(f"🔴 {line}")
                                        elif 'WARNING' in line or '⚠️' in line:
                                            print(f"🟡 {line}")
                                        elif 'INFO' in line or '✅' in line or '🚀' in line:
                                            print(f"🟢 {line}")
                                        else:
                                            print(f"⚪ {line}")
                    except Exception as e:
                        print(f"❌ Ошибка чтения {log_file}: {e}")
            
            time.sleep(1)  # Проверяем каждую секунду
            
    except KeyboardInterrupt:
        print("\n⏹️ Мониторинг остановлен")

def show_latest_logs(log_file=None, lines=50):
    """Показать последние записи из лога"""
    
    if log_file is None:
        # Находим самый новый лог файл
        log_files = glob.glob('logs/bots/bot_*.log')
        if not log_files:
            print("❌ Лог файлы ботов не найдены")
            return
        log_file = max(log_files, key=os.path.getmtime)
    
    print(f"📄 Последние {lines} строк из {log_file}:")
    print("-" * 50)
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            last_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
            
            for line in last_lines:
                line = line.strip()
                if line:
                    # Определяем тип сообщения по цвету
                    if 'ERROR' in line or '❌' in line:
                        print(f"🔴 {line}")
                    elif 'WARNING' in line or '⚠️' in line:
                        print(f"🟡 {line}")
                    elif 'INFO' in line or '✅' in line or '🚀' in line:
                        print(f"🟢 {line}")
                    else:
                        print(f"⚪ {line}")
                        
    except Exception as e:
        print(f"❌ Ошибка чтения {log_file}: {e}")

def main():
    """Главная функция"""
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == '--latest':
            lines = int(sys.argv[2]) if len(sys.argv) > 2 else 50
            show_latest_logs(lines=lines)
        elif sys.argv[1] == '--monitor':
            monitor_bot_logs()
        else:
            print("Использование:")
            print("  python monitor_bot_logs.py --latest [количество_строк]")
            print("  python monitor_bot_logs.py --monitor")
    else:
        show_latest_logs()

if __name__ == "__main__":
    main()

