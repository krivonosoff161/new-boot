// Enhanced Trading System - Main JavaScript

document.addEventListener('DOMContentLoaded', function() {
    console.log('Enhanced Trading System loaded');
    
    // Инициализация
    init();
});

function init() {
    // Инициализация всех компонентов
    initNavigation();
    initForms();
    initStats();
}

function initNavigation() {
    // Обработка навигации
    const navLinks = document.querySelectorAll('.nav a');
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            // Добавляем активный класс
            navLinks.forEach(l => l.classList.remove('active'));
            this.classList.add('active');
        });
    });
}

function initForms() {
    // Обработка форм
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            // Валидация формы
            if (!validateForm(this)) {
                e.preventDefault();
                return false;
            }
        });
    });
}

function validateForm(form) {
    const inputs = form.querySelectorAll('input[required]');
    let isValid = true;
    
    inputs.forEach(input => {
        if (!input.value.trim()) {
            showError(input, 'Это поле обязательно для заполнения');
            isValid = false;
        } else {
            clearError(input);
        }
    });
    
    return isValid;
}

function showError(input, message) {
    clearError(input);
    
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.textContent = message;
    errorDiv.style.color = '#dc3545';
    errorDiv.style.fontSize = '14px';
    errorDiv.style.marginTop = '5px';
    
    input.parentNode.appendChild(errorDiv);
    input.style.borderColor = '#dc3545';
}

function clearError(input) {
    const errorDiv = input.parentNode.querySelector('.error-message');
    if (errorDiv) {
        errorDiv.remove();
    }
    input.style.borderColor = '#ddd';
}

function initStats() {
    // Обновление статистики
    if (document.querySelector('.stats-grid')) {
        updateStats();
        setInterval(updateStats, 30000); // Обновляем каждые 30 секунд
    }
}

function updateStats() {
    // AJAX запрос для обновления статистики
    fetch('/api/user/stats')
        .then(response => response.json())
        .then(data => {
            updateStatsDisplay(data);
        })
        .catch(error => {
            console.error('Ошибка обновления статистики:', error);
        });
}

function updateStatsDisplay(data) {
    // Обновляем отображение статистики
    const totalBalance = document.querySelector('#total-balance');
    if (totalBalance) {
        totalBalance.textContent = `$${data.total_balance.toFixed(2)}`;
    }
    
    const freeBalance = document.querySelector('#free-balance');
    if (freeBalance) {
        freeBalance.textContent = `$${data.free_balance.toFixed(2)}`;
    }
    
    const usedBalance = document.querySelector('#used-balance');
    if (usedBalance) {
        usedBalance.textContent = `$${data.used_balance.toFixed(2)}`;
    }
}

// Функции для управления ботами
function startBot(botType) {
    fetch(`/api/bots/start/${botType}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('success', `Бот ${botType} успешно запущен`);
            updateBotsStatus();
        } else {
            showAlert('danger', `Ошибка запуска бота: ${data.error}`);
        }
    })
    .catch(error => {
        showAlert('danger', `Ошибка: ${error.message}`);
    });
}

function stopBot(botType) {
    fetch(`/api/bots/stop/${botType}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('success', `Бот ${botType} успешно остановлен`);
            updateBotsStatus();
        } else {
            showAlert('danger', `Ошибка остановки бота: ${data.error}`);
        }
    })
    .catch(error => {
        showAlert('danger', `Ошибка: ${error.message}`);
    });
}

function restartBot(botType) {
    fetch(`/api/bots/restart/${botType}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('success', `Бот ${botType} успешно перезапущен`);
            updateBotsStatus();
        } else {
            showAlert('danger', `Ошибка перезапуска бота: ${data.error}`);
        }
    })
    .catch(error => {
        showAlert('danger', `Ошибка: ${error.message}`);
    });
}

function updateBotsStatus() {
    fetch('/api/bots/status')
        .then(response => response.json())
        .then(data => {
            updateBotsDisplay(data);
        })
        .catch(error => {
            console.error('Ошибка получения статуса ботов:', error);
        });
}

function updateBotsDisplay(data) {
    // Обновляем отображение статуса ботов
    Object.keys(data).forEach(botType => {
        if (botType !== 'summary') {
            const statusElement = document.querySelector(`#${botType}-status`);
            if (statusElement) {
                statusElement.textContent = data[botType].status;
                statusElement.className = `status ${data[botType].status}`;
            }
        }
    });
}

function showAlert(type, message) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type}`;
    alertDiv.textContent = message;
    
    const container = document.querySelector('.main-content') || document.body;
    container.insertBefore(alertDiv, container.firstChild);
    
    // Автоматически скрываем через 5 секунд
    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

// Глобальные функции
window.startBot = startBot;
window.stopBot = stopBot;
window.restartBot = restartBot;
window.updateStats = updateStats;


