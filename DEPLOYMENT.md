# 🚀 Развертывание системы для нескольких пользователей

## 📋 Требования

- Python 3.8+
- Windows 10/11
- Минимум 4GB RAM
- 10GB свободного места на диске

## 🔧 Установка

### 1. Установка зависимостей
```bash
pip install waitress psutil
```

### 2. Настройка базы данных
```bash
python manage_users.py create admin admin@example.com admin123 --role admin
python manage_users.py create user1 user1@example.com password123
python manage_users.py create user2 user2@example.com password123
```

### 3. Проверка пользователей
```bash
python manage_users.py list
```

## 🚀 Запуск продакшн-сервера

### Запуск сервера
```bash
python run_production.py
```

### Доступ к системе
- **Локально**: http://localhost:5000
- **По сети**: http://YOUR_IP:5000

## 👥 Управление пользователями

### Создание пользователя
```bash
python manage_users.py create username email@example.com password
```

### Список пользователей
```bash
python manage_users.py list
```

### Деактивация пользователя
```bash
python manage_users.py deactivate username
```

### Активация пользователя
```bash
python manage_users.py activate username
```

### Изменение роли
```bash
python manage_users.py role username admin
```

## 📊 Мониторинг системы

### Разовый мониторинг
```bash
python monitor_system.py
```

### Непрерывный мониторинг
```bash
python monitor_system.py --watch --interval 30
```

### Сохранение данных мониторинга
```bash
python monitor_system.py --save
```

## 🔒 Безопасность

### 1. Измените секретный ключ
```python
# В config/production.py
SECRET_KEY = 'your-very-secure-secret-key-here'
```

### 2. Настройте файрвол
- Откройте порт 5000 для доступа к системе
- Закройте ненужные порты

### 3. Регулярные бэкапы
```bash
# Создайте скрипт для бэкапа
python backup_system.py
```

## 📈 Масштабирование

### Для 10+ пользователей
- Увеличьте `threads=16` в `run_production.py`
- Добавьте `connection_limit=200`

### Для 50+ пользователей
- Используйте Nginx как reverse proxy
- Настройте load balancing
- Используйте PostgreSQL вместо SQLite

## 🛠️ Обслуживание

### Перезапуск сервера
```bash
# Остановить все процессы
taskkill /IM python.exe /F

# Запустить заново
python run_production.py
```

### Очистка логов
```bash
# Очистить старые логи (старше 7 дней)
forfiles /p logs /s /m *.log /d -7 /c "cmd /c del @path"
```

### Обновление системы
```bash
# Остановить сервер
taskkill /IM python.exe /F

# Обновить код
git pull

# Запустить заново
python run_production.py
```

## 📞 Поддержка

При проблемах проверьте:
1. Логи в `logs/production.log`
2. Статус процессов: `python monitor_system.py`
3. Статус ботов: `python manage_users.py list`

## 🔄 Автоматический запуск

### Создание bat-файла для автозапуска
```batch
@echo off
cd /d "C:\path\to\your\system"
python run_production.py
pause
```

### Добавление в автозагрузку Windows
1. Скопируйте bat-файл в папку автозагрузки
2. Или создайте задачу в Планировщике заданий Windows








