#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для создания патчей в Enhanced Trading System v3.0
Следует правилам разработки и создает структурированные патчи
"""

import os
import shutil
import json
from datetime import datetime
from pathlib import Path

class PatchCreator:
    def __init__(self):
        self.patches_dir = "patches"
        self.project_root = os.getcwd()
        
    def create_patch(self, patch_type, description, files_to_change=None):
        """
        Создает новый патч
        
        Args:
            patch_type: 'feature', 'bugfix', 'hotfix', 'refactor'
            description: Описание изменений
            files_to_change: Список файлов для изменения
        """
        
        # Создаем имя папки патча
        timestamp = datetime.now().strftime("%Y-%m-%d")
        safe_description = description.lower().replace(" ", "_").replace("-", "_")
        patch_name = f"{timestamp}_{safe_description}"
        patch_path = os.path.join(self.patches_dir, patch_name)
        
        # Создаем структуру патча
        self._create_patch_structure(patch_path, patch_type, description)
        
        # Если указаны файлы для изменения, копируем их
        if files_to_change:
            self._copy_files_to_patch(patch_path, files_to_change)
        
        print(f"✅ Патч создан: {patch_path}")
        print(f"📝 Тип: {patch_type}")
        print(f"📄 Описание: {description}")
        
        return patch_path
    
    def _create_patch_structure(self, patch_path, patch_type, description):
        """Создает структуру папки патча"""
        
        # Создаем основную папку
        os.makedirs(patch_path, exist_ok=True)
        
        # Создаем подпапки
        subdirs = ["files", "tests", "rollback", "docs"]
        for subdir in subdirs:
            os.makedirs(os.path.join(patch_path, subdir), exist_ok=True)
        
        # Создаем README.md для патча
        readme_content = f"""# Патч: {description}

**Тип:** {patch_type}  
**Дата создания:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**Автор:** [Ваше имя]

## 📋 Описание изменений

[Опишите что именно изменяется и зачем]

## 🎯 Цели

- [ ] Цель 1
- [ ] Цель 2
- [ ] Цель 3

## 📁 Изменяемые файлы

- `files/` - Копии файлов для изменения
- `tests/` - Тесты для патча
- `rollback/` - Скрипты отката
- `docs/` - Дополнительная документация

## 🧪 Тестирование

### Перед применением:
- [ ] Создать резервную копию
- [ ] Запустить тесты
- [ ] Проверить в staging

### После применения:
- [ ] Проверить работоспособность
- [ ] Мониторить логи
- [ ] Проверить производительность

## 🔄 Откат

Если что-то пойдет не так:
1. Остановить систему
2. Восстановить из резервной копии
3. Запустить скрипт отката из `rollback/`
4. Проверить работоспособность

## 📊 Влияние на систему

**Модули:** [Список затронутых модулей]  
**API:** [Изменения в API]  
**База данных:** [Изменения в БД]  
**Конфигурация:** [Изменения в конфиге]

## ✅ Чек-лист

- [ ] Код написан
- [ ] Тесты написаны
- [ ] Документация обновлена
- [ ] Безопасность проверена
- [ ] Производительность приемлема
- [ ] План отката готов
- [ ] Одобрение получено
"""
        
        with open(os.path.join(patch_path, "README.md"), "w", encoding="utf-8") as f:
            f.write(readme_content)
        
        # Создаем файл метаданных
        metadata = {
            "patch_name": patch_name,
            "type": patch_type,
            "description": description,
            "created_at": datetime.now().isoformat(),
            "status": "draft",
            "files_changed": [],
            "tests": [],
            "rollback_scripts": []
        }
        
        with open(os.path.join(patch_path, "metadata.json"), "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    def _copy_files_to_patch(self, patch_path, files_to_change):
        """Копирует файлы для изменения в патч"""
        
        files_dir = os.path.join(patch_path, "files")
        
        for file_path in files_to_change:
            if os.path.exists(file_path):
                # Создаем структуру папок в патче
                dest_path = os.path.join(files_dir, file_path)
                dest_dir = os.path.dirname(dest_path)
                os.makedirs(dest_dir, exist_ok=True)
                
                # Копируем файл
                shutil.copy2(file_path, dest_path)
                print(f"📄 Скопирован файл: {file_path}")
            else:
                print(f"⚠️ Файл не найден: {file_path}")
    
    def create_hotfix(self, description, critical_files):
        """Создает срочный патч"""
        return self.create_patch("hotfix", description, critical_files)
    
    def create_feature(self, description, feature_files):
        """Создает патч с новой функцией"""
        return self.create_patch("feature", description, feature_files)
    
    def create_bugfix(self, description, bug_files):
        """Создает патч исправления бага"""
        return self.create_patch("bugfix", description, bug_files)
    
    def list_patches(self):
        """Показывает список всех патчей"""
        if not os.path.exists(self.patches_dir):
            print("📁 Папка patches не найдена")
            return
        
        patches = []
        for item in os.listdir(self.patches_dir):
            patch_path = os.path.join(self.patches_dir, item)
            if os.path.isdir(patch_path):
                metadata_file = os.path.join(patch_path, "metadata.json")
                if os.path.exists(metadata_file):
                    with open(metadata_file, "r", encoding="utf-8") as f:
                        metadata = json.load(f)
                    patches.append(metadata)
        
        if not patches:
            print("📁 Патчи не найдены")
            return
        
        print("📋 Список патчей:")
        print("=" * 80)
        
        for patch in sorted(patches, key=lambda x: x["created_at"], reverse=True):
            status_emoji = {
                "draft": "📝",
                "testing": "🧪", 
                "ready": "✅",
                "applied": "🚀",
                "rolled_back": "🔄"
            }.get(patch["status"], "❓")
            
            print(f"{status_emoji} {patch['patch_name']}")
            print(f"   Тип: {patch['type']}")
            print(f"   Описание: {patch['description']}")
            print(f"   Статус: {patch['status']}")
            print(f"   Создан: {patch['created_at']}")
            print()

def main():
    """Интерактивное создание патча"""
    creator = PatchCreator()
    
    print("🔧 Создание патча для Enhanced Trading System v3.0")
    print("=" * 60)
    
    # Выбираем тип патча
    print("Выберите тип патча:")
    print("1. feature - Новая функция")
    print("2. bugfix - Исправление бага")
    print("3. hotfix - Срочное исправление")
    print("4. refactor - Рефакторинг")
    print("5. list - Показать существующие патчи")
    
    choice = input("\nВведите номер (1-5): ").strip()
    
    if choice == "5":
        creator.list_patches()
        return
    
    patch_types = {
        "1": "feature",
        "2": "bugfix", 
        "3": "hotfix",
        "4": "refactor"
    }
    
    if choice not in patch_types:
        print("❌ Неверный выбор")
        return
    
    patch_type = patch_types[choice]
    
    # Получаем описание
    description = input(f"\nВведите описание {patch_type}: ").strip()
    if not description:
        print("❌ Описание обязательно")
        return
    
    # Получаем файлы для изменения
    print("\nВведите пути к файлам для изменения (через запятую, или Enter для пропуска):")
    files_input = input("Файлы: ").strip()
    
    files_to_change = []
    if files_input:
        files_to_change = [f.strip() for f in files_input.split(",") if f.strip()]
    
    # Создаем патч
    patch_path = creator.create_patch(patch_type, description, files_to_change)
    
    print(f"\n✅ Патч создан: {patch_path}")
    print("\n📋 Следующие шаги:")
    print("1. Отредактируйте файлы в папке files/")
    print("2. Напишите тесты в папке tests/")
    print("3. Создайте скрипт отката в папке rollback/")
    print("4. Обновите README.md патча")
    print("5. Протестируйте изменения")
    print("6. Примените патч")

if __name__ == "__main__":
    main()








