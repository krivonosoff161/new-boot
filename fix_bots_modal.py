#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для исправления модального окна деталей бота
"""
import re

def fix_bots_modal():
    """Исправляем модальное окно деталей бота"""
    
    print("🔧 ИСПРАВЛЕНИЕ МОДАЛЬНОГО ОКНА ДЕТАЛЕЙ БОТА")
    print("=" * 50)
    
    # Читаем файл
    with open('src/web/templates/bots.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("📁 Файл прочитан")
    
    # 1. Удаляем дублирующую функцию renderBotDetailsOld
    print("1️⃣ Удаляем дублирующую функцию renderBotDetailsOld...")
    
    # Находим начало функции
    start_pattern = r'function renderBotDetailsOld\(botDetails\) \{\s*console\.log\('
    start_match = re.search(start_pattern, content)
    
    if start_match:
        start_pos = start_match.start()
        print(f"   ✅ Найдено начало функции на позиции {start_pos}")
        
        # Находим конец функции (ищем закрывающую скобку на том же уровне)
        brace_count = 0
        in_function = False
        end_pos = start_pos
        
        for i, char in enumerate(content[start_pos:], start_pos):
            if char == '{':
                brace_count += 1
                in_function = True
            elif char == '}':
                brace_count -= 1
                if in_function and brace_count == 0:
                    end_pos = i + 1
                    break
        
        if end_pos > start_pos:
            # Удаляем функцию
            content = content[:start_pos] + content[end_pos:]
            print(f"   ✅ Функция удалена (позиции {start_pos}-{end_pos})")
        else:
            print("   ❌ Не удалось найти конец функции")
    else:
        print("   ❌ Функция renderBotDetailsOld не найдена")
    
    # 2. Исправляем функцию showBotDetails
    print("\n2️⃣ Исправляем функцию showBotDetails...")
    
    # Ищем функцию showBotDetails
    show_pattern = r'function showBotDetails\(botId\) \{[^}]*\}'
    show_match = re.search(show_pattern, content, re.DOTALL)
    
    if show_match:
        print("   ✅ Функция showBotDetails найдена")
        
        # Заменяем на исправленную версию
        new_show_function = '''function showBotDetails(botId) {
    console.log('DEBUG: showBotDetails called with botId:', botId);
    currentBotId = botId;  // Устанавливаем currentBotId для консоли
    
    // Показываем модальное окно
    const modal = new bootstrap.Modal(document.getElementById('botDetailsModal'));
    modal.show();
    
    // Обновляем заголовок
    document.getElementById('botDetailsModalTitle').textContent = `Детали бота ${botId}`;
    
    // Загружаем детальную информацию
    loadBotDetails(botId);
}'''
        
        content = content.replace(show_match.group(0), new_show_function)
        print("   ✅ Функция showBotDetails исправлена")
    else:
        print("   ❌ Функция showBotDetails не найдена")
    
    # 3. Исправляем функцию loadBotDetails
    print("\n3️⃣ Исправляем функцию loadBotDetails...")
    
    # Ищем функцию loadBotDetails
    load_pattern = r'function loadBotDetails\(botId\) \{[^}]*\}'
    load_match = re.search(load_pattern, content, re.DOTALL)
    
    if load_match:
        print("   ✅ Функция loadBotDetails найдена")
        
        # Заменяем на исправленную версию
        new_load_function = '''function loadBotDetails(botId) {
    console.log('DEBUG: loadBotDetails called with botId:', botId);
    
    // Показываем спиннер загрузки
    document.getElementById('botDetailsContent').innerHTML = `
        <div class="text-center py-4">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Загрузка...</span>
            </div>
            <p class="mt-2 text-muted">Загружаем детальную информацию...</p>
        </div>
    `;
    
    console.log('DEBUG: Making API request to /api/bots/' + botId + '/details');
    fetch(`/api/bots/${botId}/details`)
        .then(response => response.json())
        .then(data => {
            console.log('Функция renderBotDetails вызвана с данными:', data);
            if (data.success) {
                // Используем новую функцию с правильными параметрами
                renderBotDetails(data.bot || data.bot_details, data.charts, data.system_metrics, data.logs);
                // Загружаем рекомендованные пары
                loadRecommendedPairs();
            } else {
                document.getElementById('botDetailsContent').innerHTML = `
                    <div class="alert alert-danger">
                        <h5>Ошибка загрузки</h5>
                        <p>${data.error}</p>
                    </div>
                `;
            }
        })
        .catch(error => {
            console.error('Ошибка:', error);
            document.getElementById('botDetailsContent').innerHTML = `
                <div class="alert alert-danger">
                    <h5>Ошибка загрузки</h5>
                    <p>Произошла ошибка при загрузке детальной информации о боте.</p>
                </div>
            `;
        });
}'''
        
        content = content.replace(load_match.group(0), new_load_function)
        print("   ✅ Функция loadBotDetails исправлена")
    else:
        print("   ❌ Функция loadBotDetails не найдена")
    
    # 4. Добавляем кнопку закрытия модального окна
    print("\n4️⃣ Добавляем кнопку закрытия модального окна...")
    
    # Ищем модальное окно
    modal_pattern = r'<div class="modal-footer">\s*<button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Закрыть</button>'
    modal_match = re.search(modal_pattern, content)
    
    if modal_match:
        print("   ✅ Модальное окно найдено")
        
        # Заменяем на исправленную версию с кнопкой консоли
        new_modal_footer = '''<div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Закрыть</button>
                <button type="button" class="btn btn-info" onclick="showConsoleOutput()">
                    <i class="fas fa-terminal"></i> Консоль
                </button>
                <button type="button" class="btn btn-primary" onclick="refreshBotDetails()">
                    <i class="fas fa-sync"></i> Обновить
                </button>
            </div>'''
        
        content = content.replace(modal_match.group(0), new_modal_footer)
        print("   ✅ Кнопка консоли добавлена")
    else:
        print("   ❌ Модальное окно не найдено")
    
    # 5. Сохраняем исправленный файл
    print("\n5️⃣ Сохраняем исправленный файл...")
    
    with open('src/web/templates/bots.html', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("   ✅ Файл сохранен")
    
    print("\n✅ ИСПРАВЛЕНИЯ ЗАВЕРШЕНЫ!")
    print("\n🌐 Теперь откройте браузер и протестируйте модальное окно деталей бота")

if __name__ == "__main__":
    fix_bots_modal()



