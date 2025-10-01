// Enhanced Dashboard JavaScript

class DashboardManager {
    constructor() {
        this.charts = {};
        this.updateInterval = null;
        this.init();
    }

    init() {
        this.initCharts();
        this.loadBots();
        this.startAutoUpdate();
        this.bindEvents();
    }

    // Инициализация графиков
    initCharts() {
        const ctx = document.getElementById('tradingChart');
        if (!ctx) return;

        this.charts.trading = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Баланс',
                    data: [],
                    borderColor: '#20c997',
                    backgroundColor: 'rgba(32, 201, 151, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }, {
                    label: 'P&L',
                    data: [],
                    borderColor: '#e83e8c',
                    backgroundColor: 'rgba(232, 62, 140, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: {
                            color: '#ffffff'
                        }
                    }
                },
                scales: {
                    x: {
                        ticks: {
                            color: '#ffffff'
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    },
                    y: {
                        ticks: {
                            color: '#ffffff',
                            callback: function(value) {
                                return '$' + value.toFixed(2);
                            }
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                }
            }
        });
    }

    // Загрузка ботов
    async loadBots() {
        try {
            const response = await fetch('/dashboard/api/bots');
            const data = await response.json();
            
            if (data.success) {
                this.renderBots(data.data.available_bots, data.data.active_bots);
            }
        } catch (error) {
            console.error('Ошибка загрузки ботов:', error);
        }
    }

    // Отображение ботов
    renderBots(availableBots, activeBots) {
        const availableContainer = document.getElementById('availableBots');
        const activeContainer = document.getElementById('activeBots');

        // Доступные боты
        availableContainer.innerHTML = '';
        availableBots.forEach(bot => {
            const botElement = this.createBotElement(bot, false);
            availableContainer.appendChild(botElement);
        });

        // Активные боты
        activeContainer.innerHTML = '';
        activeBots.forEach(bot => {
            const botElement = this.createBotElement(bot, true);
            activeContainer.appendChild(botElement);
        });
    }

    // Создание элемента бота
    createBotElement(bot, isActive) {
        const div = document.createElement('div');
        div.className = `bot-item ${isActive ? 'active' : ''}`;
        div.innerHTML = `
            <div class="d-flex justify-content-between align-items-center">
                <div>
                    <h6 class="mb-1">${bot.name || bot}</h6>
                    <small class="text-muted">${bot.description || 'Торговый бот'}</small>
                </div>
                <div class="d-flex align-items-center">
                    <span class="status-indicator ${isActive ? 'active' : 'inactive'}"></span>
                    ${isActive ? 
                        `<button class="btn btn-sm btn-outline-danger" onclick="dashboard.stopBot('${bot.id}')">
                            <i class="fas fa-stop"></i>
                        </button>` :
                        `<button class="btn btn-sm btn-outline-success" onclick="dashboard.startBot('${bot}')">
                            <i class="fas fa-play"></i>
                        </button>`
                    }
                </div>
            </div>
        `;
        return div;
    }

    // Запуск бота
    async startBot(botType) {
        try {
            const response = await fetch('/dashboard/api/bots/start', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    bot_type: botType,
                    config: {}
                })
            });

            const data = await response.json();
            
            if (data.success) {
                this.showAlert('success', data.message);
                this.loadBots(); // Перезагружаем список ботов
            } else {
                this.showAlert('danger', data.error);
            }
        } catch (error) {
            console.error('Ошибка запуска бота:', error);
            this.showAlert('danger', 'Ошибка запуска бота');
        }
    }

    // Остановка бота
    async stopBot(botId) {
        try {
            const response = await fetch('/dashboard/api/bots/stop', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    bot_id: botId
                })
            });

            const data = await response.json();
            
            if (data.success) {
                this.showAlert('success', data.message);
                this.loadBots(); // Перезагружаем список ботов
            } else {
                this.showAlert('danger', data.error);
            }
        } catch (error) {
            console.error('Ошибка остановки бота:', error);
            this.showAlert('danger', 'Ошибка остановки бота');
        }
    }

    // Автообновление данных
    startAutoUpdate() {
        this.updateInterval = setInterval(() => {
            this.updateStats();
        }, 30000); // Обновляем каждые 30 секунд
    }

    // Обновление статистики
    async updateStats() {
        try {
            const response = await fetch('/dashboard/api/stats');
            const data = await response.json();
            
            if (data.success) {
                this.updateCharts(data.data);
                this.updateStatsCards(data.data);
            }
        } catch (error) {
            console.error('Ошибка обновления статистики:', error);
        }
    }

    // Обновление графиков
    updateCharts(data) {
        if (!this.charts.trading) return;

        const now = new Date();
        const timeLabel = now.toLocaleTimeString();
        
        // Добавляем новые данные
        this.charts.trading.data.labels.push(timeLabel);
        this.charts.trading.data.datasets[0].data.push(data.trading_data.balance);
        this.charts.trading.data.datasets[1].data.push(data.trading_data.profit_loss);

        // Ограничиваем количество точек на графике
        const maxPoints = 20;
        if (this.charts.trading.data.labels.length > maxPoints) {
            this.charts.trading.data.labels.shift();
            this.charts.trading.data.datasets[0].data.shift();
            this.charts.trading.data.datasets[1].data.shift();
        }

        this.charts.trading.update('none');
    }

    // Обновление карточек статистики
    updateStatsCards(data) {
        // Обновляем баланс
        const balanceElement = document.querySelector('.card.bg-success h3');
        if (balanceElement) {
            balanceElement.textContent = `$${data.trading_data.balance.toFixed(2)}`;
        }

        // Обновляем активные боты
        const botsElement = document.querySelector('.card.bg-info h3');
        if (botsElement) {
            botsElement.textContent = data.trading_data.active_bots;
        }

        // Обновляем P&L
        const pnlElement = document.querySelector('.card.bg-success h3, .card.bg-danger h3');
        if (pnlElement) {
            pnlElement.textContent = `$${data.trading_data.profit_loss.toFixed(2)}`;
        }

        // Обновляем винрейт
        const winRateElement = document.querySelector('.card.bg-warning h3');
        if (winRateElement) {
            winRateElement.textContent = `${data.trading_data.win_rate.toFixed(1)}%`;
        }
    }

    // Привязка событий
    bindEvents() {
        // Обработка кликов по карточкам
        document.querySelectorAll('.card').forEach(card => {
            card.addEventListener('click', (e) => {
                if (e.target.closest('.btn')) return; // Игнорируем клики по кнопкам
                
                card.classList.add('shadow-glow');
                setTimeout(() => {
                    card.classList.remove('shadow-glow');
                }, 2000);
            });
        });

        // Обработка наведения на элементы
        document.querySelectorAll('.bot-item').forEach(item => {
            item.addEventListener('mouseenter', (e) => {
                e.target.style.transform = 'translateX(5px)';
            });
            
            item.addEventListener('mouseleave', (e) => {
                e.target.style.transform = 'translateX(0)';
            });
        });
    }

    // Показ уведомлений
    showAlert(type, message) {
        const alertContainer = document.createElement('div');
        alertContainer.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        alertContainer.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        alertContainer.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        document.body.appendChild(alertContainer);

        // Автоматически скрываем через 5 секунд
        setTimeout(() => {
            if (alertContainer.parentNode) {
                alertContainer.remove();
            }
        }, 5000);
    }

    // Очистка ресурсов
    destroy() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
        }
        
        Object.values(this.charts).forEach(chart => {
            if (chart && typeof chart.destroy === 'function') {
                chart.destroy();
            }
        });
    }
}

// Инициализация дашборда
let dashboard;

document.addEventListener('DOMContentLoaded', () => {
    dashboard = new DashboardManager();
});

// Очистка при выгрузке страницы
window.addEventListener('beforeunload', () => {
    if (dashboard) {
        dashboard.destroy();
    }
});

// Дополнительные утилиты
class DashboardUtils {
    static formatCurrency(amount) {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD'
        }).format(amount);
    }

    static formatPercentage(value) {
        return `${value.toFixed(1)}%`;
    }

    static formatNumber(value) {
        return new Intl.NumberFormat('en-US').format(value);
    }

    static getStatusColor(status) {
        const colors = {
            'active': 'success',
            'inactive': 'danger',
            'pending': 'warning',
            'error': 'danger'
        };
        return colors[status] || 'secondary';
    }

    static animateValue(element, start, end, duration) {
        const startTimestamp = performance.now();
        const step = (timestamp) => {
            const progress = Math.min((timestamp - startTimestamp) / duration, 1);
            const current = start + (end - start) * progress;
            element.textContent = current.toFixed(2);
            if (progress < 1) {
                requestAnimationFrame(step);
            }
        };
        requestAnimationFrame(step);
    }
}

// Экспорт для использования в других модулях
window.DashboardManager = DashboardManager;
window.DashboardUtils = DashboardUtils;











