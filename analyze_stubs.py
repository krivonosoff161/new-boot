#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Анализ заглушек и закомментированных мест в проекте
"""
import os
import re

def count_stubs_in_file(filepath):
    """Подсчет заглушек в файле"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        stubs = {
            'todo': len(re.findall(r'TODO|FIXME', content, re.IGNORECASE)),
            'stub': len(re.findall(r'заглушка|stub|placeholder|mock|dummy|fake', content, re.IGNORECASE)),
            'not_implemented': len(re.findall(r'NotImplementedError|NotImplemented|raise NotImplementedError', content, re.IGNORECASE)),
            'empty_returns': len(re.findall(r'return None|return 0|return \{\}|return \[\]|return ""|return \'\'', content)),
            'pass_statements': len(re.findall(r'^\s*pass\s*$', content, re.MULTILINE)),
            'commented_blocks': len(re.findall(r'^\s*#.*[a-zA-Z]', content, re.MULTILINE))
        }
        return stubs
    except Exception as e:
        print(f"Ошибка чтения файла {filepath}: {e}")
        return {'todo': 0, 'stub': 0, 'not_implemented': 0, 'empty_returns': 0, 'pass_statements': 0, 'commented_blocks': 0}

def scan_directory(directory):
    """Сканирование директории на предмет заглушек"""
    total_stubs = {'todo': 0, 'stub': 0, 'not_implemented': 0, 'empty_returns': 0, 'pass_statements': 0, 'commented_blocks': 0}
    files_with_stubs = 0
    file_details = []
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(('.py', '.html', '.js', '.css')):
                filepath = os.path.join(root, file)
                stubs = count_stubs_in_file(filepath)
                
                if any(stubs.values()):
                    files_with_stubs += 1
                    file_details.append({
                        'file': filepath,
                        'stubs': stubs
                    })
                    
                    for key in total_stubs:
                        total_stubs[key] += stubs[key]
    
    return total_stubs, files_with_stubs, file_details

def main():
    """Основная функция"""
    print("🔍 АНАЛИЗ ЗАГЛУШЕК И ЗАКОММЕНТИРОВАННЫХ МЕСТ")
    print("=" * 60)
    
    # Сканируем src директорию
    stubs, files, details = scan_directory('src')
    
    print(f"📁 Файлов с заглушками: {files}")
    print(f"📝 TODO/FIXME: {stubs['todo']}")
    print(f"🔧 Заглушки (stub/placeholder/mock): {stubs['stub']}")
    print(f"❌ NotImplementedError: {stubs['not_implemented']}")
    print(f"🔄 Пустые return: {stubs['empty_returns']}")
    print(f"⏸️  pass statements: {stubs['pass_statements']}")
    print(f"💬 Закомментированные строки: {stubs['commented_blocks']}")
    print(f"📊 ВСЕГО ЗАГЛУШЕК: {sum(stubs.values())}")
    
    print("\n" + "=" * 60)
    print("📋 ТОП-10 ФАЙЛОВ С НАИБОЛЬШИМ КОЛИЧЕСТВОМ ЗАГЛУШЕК:")
    print("=" * 60)
    
    # Сортируем файлы по количеству заглушек
    sorted_files = sorted(details, key=lambda x: sum(x['stubs'].values()), reverse=True)
    
    for i, file_info in enumerate(sorted_files[:10]):
        total = sum(file_info['stubs'].values())
        print(f"{i+1:2d}. {file_info['file']}")
        print(f"    Всего заглушек: {total}")
        print(f"    TODO: {file_info['stubs']['todo']}, Заглушки: {file_info['stubs']['stub']}, "
              f"NotImplemented: {file_info['stubs']['not_implemented']}, "
              f"Пустые return: {file_info['stubs']['empty_returns']}, "
              f"pass: {file_info['stubs']['pass_statements']}, "
              f"Комментарии: {file_info['stubs']['commented_blocks']}")
        print()
    
    print("=" * 60)
    print("🎯 РЕКОМЕНДАЦИИ:")
    print("=" * 60)
    
    if stubs['todo'] > 0:
        print(f"⚠️  Найдено {stubs['todo']} TODO/FIXME - нужно доработать функционал")
    
    if stubs['not_implemented'] > 0:
        print(f"❌ Найдено {stubs['not_implemented']} NotImplementedError - критические заглушки")
    
    if stubs['empty_returns'] > 20:
        print(f"🔄 Много пустых return ({stubs['empty_returns']}) - возможно, недоделанный функционал")
    
    if stubs['commented_blocks'] > 100:
        print(f"💬 Много закомментированного кода ({stubs['commented_blocks']}) - нужно почистить")
    
    print(f"\n📊 Общий уровень готовности: {max(0, 100 - (sum(stubs.values()) / 10)):.1f}%")

if __name__ == "__main__":
    main()

