#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для исправления синтаксических ошибок в app.py
"""

import re

def fix_syntax_errors():
    """Исправляем синтаксические ошибки в app.py"""
    
    with open('web_interface/app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Исправляем проблемы с индентацией
    lines = content.split('\n')
    fixed_lines = []
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Исправляем неправильную индентацию для if/else блоков
        if re.match(r'^\s*if.*:', line) and i + 1 < len(lines):
            next_line = lines[i + 1]
            if next_line.strip() and not next_line.startswith('    ') and not next_line.startswith('\t'):
                # Добавляем правильную индентацию
                indent = len(line) - len(line.lstrip())
                lines[i + 1] = ' ' * (indent + 4) + next_line.strip()
        
        # Исправляем неправильную индентацию для try/except блоков
        if re.match(r'^\s*try:', line) and i + 1 < len(lines):
            next_line = lines[i + 1]
            if next_line.strip() and not next_line.startswith('    ') and not next_line.startswith('\t'):
                # Добавляем правильную индентацию
                indent = len(line) - len(line.lstrip())
                lines[i + 1] = ' ' * (indent + 4) + next_line.strip()
        
        # Исправляем неправильную индентацию для return statements
        if re.match(r'^\s*return.*', line) and i > 0:
            prev_line = lines[i - 1]
            if prev_line.strip() and not prev_line.endswith(':'):
                # Проверяем, что return находится в правильном блоке
                if not line.startswith('        '):
                    # Добавляем правильную индентацию
                    indent = len(prev_line) - len(prev_line.lstrip())
                    lines[i] = ' ' * (indent + 4) + line.strip()
        
        fixed_lines.append(lines[i])
        i += 1
    
    # Записываем исправленный файл
    with open('web_interface/app.py', 'w', encoding='utf-8') as f:
        f.write('\n'.join(fixed_lines))
    
    print("✅ Синтаксические ошибки исправлены!")

if __name__ == "__main__":
    fix_syntax_errors()


