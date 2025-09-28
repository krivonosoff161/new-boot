#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Главный скрипт запуска Enhanced Trading System v3.0
"""

import os
import sys
import subprocess

def main():
    print("🚀 Enhanced Trading System v3.0")
    print("=" * 50)
    
    # Проверяем, есть ли новая структура
    if os.path.exists('enhanced_trading_system'):
        print("📁 Используем новую структуру enhanced_trading_system/")
        os.chdir('enhanced_trading_system')
        os.chdir('web_interface')
    else:
        print("📁 Используем старую структуру web_interface/")
        os.chdir('web_interface')
    
    # Запускаем веб-интерфейс
    print("🌐 Запуск веб-интерфейса...")
    subprocess.run([sys.executable, 'app.py'])

if __name__ == "__main__":
    main()


