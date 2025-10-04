#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple Web Interface Launcher
Enhanced Trading System v3.0 Commercial
"""

import os
import sys

# Добавляем путь к src
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Импортируем и запускаем приложение
from src.web.app import app

if __name__ == '__main__':
    print("Starting web interface...")
    print("Open browser: http://localhost:5000")
    print("Press Ctrl+C to stop")
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        use_reloader=False
    )


















