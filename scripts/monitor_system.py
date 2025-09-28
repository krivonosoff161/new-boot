#!/usr/bin/env python3
"""
Мониторинг системы для продакшна
"""

import psutil
import time
import json
import os
from datetime import datetime

def get_system_stats():
    """Получение статистики системы"""
    stats = {
        'timestamp': datetime.now().isoformat(),
        'cpu': {
            'usage_percent': psutil.cpu_percent(interval=1),
            'count': psutil.cpu_count()
        },
        'memory': {
            'total': psutil.virtual_memory().total,
            'available': psutil.virtual_memory().available,
            'percent': psutil.virtual_memory().percent
        },
        'disk': {
            'total': psutil.disk_usage('/').total,
            'free': psutil.disk_usage('/').free,
            'percent': psutil.disk_usage('/').percent
        },
        'network': {
            'bytes_sent': psutil.net_io_counters().bytes_sent,
            'bytes_recv': psutil.net_io_counters().bytes_recv
        }
    }
    return stats

def get_python_processes():
    """Получение информации о Python процессах"""
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'cmdline']):
        try:
            if proc.info['name'] == 'python.exe' or 'python' in proc.info['name']:
                processes.append({
                    'pid': proc.info['pid'],
                    'name': proc.info['name'],
                    'cpu_percent': proc.info['cpu_percent'],
                    'memory_percent': proc.info['memory_percent'],
                    'cmdline': ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return processes

def get_bot_status():
    """Получение статуса ботов"""
    try:
        with open('data/bot_status.json', 'r', encoding='utf-8') as f:
            bot_status = json.load(f)
        return bot_status
    except:
        return {}

def save_monitoring_data(stats, processes, bot_status):
    """Сохранение данных мониторинга"""
    data = {
        'system': stats,
        'processes': processes,
        'bots': bot_status
    }
    
    # Создаем директорию если не существует
    os.makedirs('logs/monitoring', exist_ok=True)
    
    # Сохраняем в файл
    filename = f"logs/monitoring/monitor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    return filename

def print_status():
    """Вывод статуса системы"""
    print("🔍 Мониторинг системы торговых ботов")
    print("=" * 50)
    
    # Системная статистика
    stats = get_system_stats()
    print(f"💻 CPU: {stats['cpu']['usage_percent']:.1f}% ({stats['cpu']['count']} ядер)")
    print(f"🧠 RAM: {stats['memory']['percent']:.1f}% ({stats['memory']['available'] // (1024**3):.1f}GB свободно)")
    print(f"💾 Диск: {stats['disk']['percent']:.1f}% ({stats['disk']['free'] // (1024**3):.1f}GB свободно)")
    
    # Python процессы
    processes = get_python_processes()
    print(f"\n🐍 Python процессов: {len(processes)}")
    for proc in processes:
        print(f"   PID {proc['pid']:5d}: {proc['cpu_percent']:5.1f}% CPU, {proc['memory_percent']:5.1f}% RAM - {proc['cmdline'][:60]}...")
    
    # Статус ботов
    bot_status = get_bot_status()
    running_bots = sum(1 for bot in bot_status.values() if bot.get('status') == 'running')
    total_bots = len(bot_status)
    print(f"\n🤖 Ботов: {running_bots}/{total_bots} запущено")
    
    for bot_id, bot_info in bot_status.items():
        status_icon = "🟢" if bot_info.get('status') == 'running' else "🔴"
        print(f"   {status_icon} {bot_id}: {bot_info.get('status', 'unknown')}")

def main():
    """Главная функция мониторинга"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Мониторинг системы')
    parser.add_argument('--watch', action='store_true', help='Непрерывный мониторинг')
    parser.add_argument('--interval', type=int, default=30, help='Интервал обновления в секундах')
    parser.add_argument('--save', action='store_true', help='Сохранить данные в файл')
    
    args = parser.parse_args()
    
    if args.watch:
        print(f"🔄 Непрерывный мониторинг (интервал: {args.interval}с)")
        print("Нажмите Ctrl+C для остановки")
        print()
        
        try:
            while True:
                os.system('cls' if os.name == 'nt' else 'clear')
                print_status()
                
                if args.save:
                    stats = get_system_stats()
                    processes = get_python_processes()
                    bot_status = get_bot_status()
                    filename = save_monitoring_data(stats, processes, bot_status)
                    print(f"\n💾 Данные сохранены: {filename}")
                
                time.sleep(args.interval)
                
        except KeyboardInterrupt:
            print("\n👋 Мониторинг остановлен")
    else:
        print_status()
        
        if args.save:
            stats = get_system_stats()
            processes = get_python_processes()
            bot_status = get_bot_status()
            filename = save_monitoring_data(stats, processes, bot_status)
            print(f"\n💾 Данные сохранены: {filename}")

if __name__ == '__main__':
    main()





