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
    
    # Получаем путь к корню проекта
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    
    # Запускаем основной дашборд
    print("🌐 Запуск дашборда...")
    print("📂 Корень проекта:", project_root)
    
    # Переходим в корень проекта и запускаем дашборд
    os.chdir(project_root)
    subprocess.run([sys.executable, 'run_dashboard.py'])

if __name__ == "__main__":
    main()
