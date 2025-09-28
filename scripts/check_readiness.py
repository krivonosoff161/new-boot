#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт проверки готовности к реорганизации проекта
Enhanced Trading System v3.0
"""

import os
import json
from datetime import datetime
from pathlib import Path

class ReadinessChecker:
    def __init__(self):
        self.project_root = os.getcwd()
        self.issues = []
        self.warnings = []
        self.recommendations = []
        
    def check_backup_availability(self):
        """Проверяет доступность места для резервной копии"""
        print("🔍 Проверка места для резервной копии...")
        
        # Проверяем свободное место (упрощенно)
        try:
            # Создаем тестовый файл для проверки записи
            test_file = "test_write_permission.tmp"
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
            print("✅ Запись в текущую директорию возможна")
        except Exception as e:
            self.issues.append(f"Нет прав записи в директорию: {e}")
            return False
        
        return True
    
    def check_file_dependencies(self):
        """Проверяет зависимости между файлами"""
        print("🔍 Анализ зависимостей файлов...")
        
        # Список файлов для анализа
        files_to_check = [
            "web_interface/app.py",
            "enhanced/security_system_v3.py",
            "enhanced/enhanced_controller.py",
            "enhanced/enhanced_grid_bot.py",
            "enhanced/enhanced_scalp_bot.py"
        ]
        
        missing_files = []
        for file_path in files_to_check:
            if not os.path.exists(file_path):
                missing_files.append(file_path)
        
        if missing_files:
            self.warnings.append(f"Отсутствуют файлы: {', '.join(missing_files)}")
        else:
            print("✅ Все ключевые файлы найдены")
        
        return len(missing_files) == 0
    
    def check_database_integrity(self):
        """Проверяет целостность базы данных"""
        print("🔍 Проверка базы данных...")
        
        db_files = [
            "web_interface/secure_users.db",
            "web_interface/users.db"
        ]
        
        for db_file in db_files:
            if os.path.exists(db_file):
                try:
                    # Простая проверка - файл не пустой
                    if os.path.getsize(db_file) > 0:
                        print(f"✅ База данных {db_file} найдена и не пустая")
                    else:
                        self.warnings.append(f"База данных {db_file} пустая")
                except Exception as e:
                    self.issues.append(f"Ошибка проверки {db_file}: {e}")
            else:
                self.warnings.append(f"База данных {db_file} не найдена")
    
    def check_configuration_files(self):
        """Проверяет конфигурационные файлы"""
        print("🔍 Проверка конфигурации...")
        
        config_files = [
            "config/bot_config.json"
        ]
        
        for config_file in config_files:
            if os.path.exists(config_file):
                try:
                    with open(config_file, "r", encoding="utf-8") as f:
                        json.load(f)
                    print(f"✅ Конфигурация {config_file} валидна")
                except Exception as e:
                    self.issues.append(f"Ошибка в конфигурации {config_file}: {e}")
            else:
                self.warnings.append(f"Конфигурация {config_file} не найдена")
    
    def check_duplicate_files(self):
        """Проверяет дублирующиеся файлы"""
        print("🔍 Поиск дублирующихся файлов...")
        
        # Файлы, которые могут дублироваться
        potential_duplicates = {
            "app.py": ["web_interface/app.py", "web_interface/app_backup.py", "web_interface/app_simple.py"],
            "users.db": ["web_interface/secure_users.db", "web_interface/users.db"],
            "start.py": ["start.py", "start_system.py"]
        }
        
        duplicates_found = []
        for base_name, candidates in potential_duplicates.items():
            existing_files = [f for f in candidates if os.path.exists(f)]
            if len(existing_files) > 1:
                duplicates_found.append(f"{base_name}: {', '.join(existing_files)}")
        
        if duplicates_found:
            self.warnings.append(f"Найдены дублирующиеся файлы: {'; '.join(duplicates_found)}")
        else:
            print("✅ Дублирующихся файлов не найдено")
    
    def check_directory_structure(self):
        """Проверяет текущую структуру директорий"""
        print("🔍 Анализ структуры директорий...")
        
        expected_dirs = [
            "web_interface",
            "enhanced", 
            "config",
            "logs",
            "user_data"
        ]
        
        missing_dirs = []
        for dir_name in expected_dirs:
            if not os.path.exists(dir_name):
                missing_dirs.append(dir_name)
        
        if missing_dirs:
            self.warnings.append(f"Отсутствуют директории: {', '.join(missing_dirs)}")
        else:
            print("✅ Основные директории найдены")
    
    def check_python_environment(self):
        """Проверяет Python окружение"""
        print("🔍 Проверка Python окружения...")
        
        try:
            import sys
            python_version = sys.version_info
            if python_version.major >= 3 and python_version.minor >= 8:
                print(f"✅ Python версия {python_version.major}.{python_version.minor} подходит")
            else:
                self.issues.append(f"Python версия {python_version.major}.{python_version.minor} слишком старая. Нужна 3.8+")
        except Exception as e:
            self.issues.append(f"Ошибка проверки Python: {e}")
    
    def check_required_packages(self):
        """Проверяет наличие необходимых пакетов"""
        print("🔍 Проверка необходимых пакетов...")
        
        required_packages = [
            "flask",
            "ccxt", 
            "numpy",
            "cryptography",
            "python-telegram-bot"
        ]
        
        missing_packages = []
        for package in required_packages:
            try:
                __import__(package)
            except ImportError:
                missing_packages.append(package)
        
        if missing_packages:
            self.warnings.append(f"Отсутствуют пакеты: {', '.join(missing_packages)}")
        else:
            print("✅ Все необходимые пакеты установлены")
    
    def generate_report(self):
        """Генерирует отчет о готовности"""
        print("\n" + "="*60)
        print("📊 ОТЧЕТ О ГОТОВНОСТИ К РЕОРГАНИЗАЦИИ")
        print("="*60)
        
        # Критические проблемы
        if self.issues:
            print("\n❌ КРИТИЧЕСКИЕ ПРОБЛЕМЫ:")
            for i, issue in enumerate(self.issues, 1):
                print(f"  {i}. {issue}")
        
        # Предупреждения
        if self.warnings:
            print("\n⚠️ ПРЕДУПРЕЖДЕНИЯ:")
            for i, warning in enumerate(self.warnings, 1):
                print(f"  {i}. {warning}")
        
        # Рекомендации
        if self.recommendations:
            print("\n💡 РЕКОМЕНДАЦИИ:")
            for i, rec in enumerate(self.recommendations, 1):
                print(f"  {i}. {rec}")
        
        # Общий статус
        print(f"\n📈 СТАТУС ГОТОВНОСТИ:")
        if not self.issues:
            print("✅ ГОТОВ К РЕОРГАНИЗАЦИИ")
            print("   Можно запускать: python reorganize_project.py")
        else:
            print("❌ НЕ ГОТОВ К РЕОРГАНИЗАЦИИ")
            print("   Сначала исправьте критические проблемы")
        
        # Сохраняем отчет в файл
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "issues": self.issues,
            "warnings": self.warnings,
            "recommendations": self.recommendations,
            "ready": len(self.issues) == 0
        }
        
        with open("readiness_report.json", "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 Отчет сохранен в: readiness_report.json")
    
    def run_checks(self):
        """Запускает все проверки"""
        print("🚀 ПРОВЕРКА ГОТОВНОСТИ К РЕОРГАНИЗАЦИИ")
        print("="*60)
        
        # Выполняем все проверки
        self.check_backup_availability()
        self.check_file_dependencies()
        self.check_database_integrity()
        self.check_configuration_files()
        self.check_duplicate_files()
        self.check_directory_structure()
        self.check_python_environment()
        self.check_required_packages()
        
        # Генерируем отчет
        self.generate_report()

def main():
    """Главная функция"""
    checker = ReadinessChecker()
    checker.run_checks()

if __name__ == "__main__":
    main()








