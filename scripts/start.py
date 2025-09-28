#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Trading System v3.0 - Главный скрипт запуска
"""

import os
import sys
import subprocess

def main():
    print("🚀 Enhanced Trading System v3.0")
    print("=" * 50)
    
    # Переходим в папку веб-интерфейса
    os.chdir('web_interface')
    
    # Запускаем веб-интерфейс
    print("🌐 Запуск веб-интерфейса...")
    subprocess.run([sys.executable, 'app.py'])

if __name__ == "__main__":
    main()
