// Enhanced Authentication JavaScript

class AuthManager {
    constructor() {
        this.init();
    }

    init() {
        this.bindEvents();
        this.initPasswordStrength();
        this.initFormValidation();
    }

    bindEvents() {
        // Обработка отправки форм
        document.querySelectorAll('form').forEach(form => {
            form.addEventListener('submit', (e) => this.handleFormSubmit(e));
        });

        // Обработка изменения полей
        document.querySelectorAll('input, select, textarea').forEach(field => {
            field.addEventListener('change', (e) => this.handleFieldChange(e));
            field.addEventListener('input', (e) => this.handleFieldInput(e));
        });

        // Обработка кнопок
        document.querySelectorAll('.btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.handleButtonClick(e));
        });
    }

    handleFormSubmit(e) {
        const form = e.target;
        const submitBtn = form.querySelector('button[type="submit"]');
        
        if (submitBtn) {
            this.setButtonLoading(submitBtn, true);
        }

        // Валидация формы
        if (!this.validateForm(form)) {
            e.preventDefault();
            if (submitBtn) {
                this.setButtonLoading(submitBtn, false);
            }
            return;
        }
    }

    handleFieldChange(e) {
        const field = e.target;
        this.validateField(field);
    }

    handleFieldInput(e) {
        const field = e.target;
        
        // Специальная обработка для пароля
        if (field.type === 'password' && field.name === 'password') {
            this.updatePasswordStrength(field.value);
        }
        
        // Специальная обработка для подтверждения пароля
        if (field.type === 'password' && field.name === 'confirm_password') {
            this.validatePasswordConfirmation(field);
        }
    }

    handleButtonClick(e) {
        const btn = e.target;
        
        // Обработка кнопок с data-action
        const action = btn.getAttribute('data-action');
        if (action) {
            e.preventDefault();
            this.handleAction(action, btn);
        }
    }

    validateForm(form) {
        let isValid = true;
        const fields = form.querySelectorAll('input[required], select[required], textarea[required]');
        
        fields.forEach(field => {
            if (!this.validateField(field)) {
                isValid = false;
            }
        });
        
        return isValid;
    }

    validateField(field) {
        const value = field.value.trim();
        const fieldName = field.name;
        let isValid = true;
        let errorMessage = '';

        // Удаляем предыдущие ошибки
        this.clearFieldError(field);

        // Проверка обязательности
        if (field.hasAttribute('required') && !value) {
            errorMessage = 'Это поле обязательно для заполнения';
            isValid = false;
        }

        // Специфичные валидации
        if (value && isValid) {
            switch (fieldName) {
                case 'username':
                    if (!/^[a-zA-Z0-9_]+$/.test(value)) {
                        errorMessage = 'Имя пользователя может содержать только буквы, цифры и подчеркивания';
                        isValid = false;
                    } else if (value.length < 3) {
                        errorMessage = 'Имя пользователя должно содержать минимум 3 символа';
                        isValid = false;
                    }
                    break;

                case 'email':
                    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
                        errorMessage = 'Введите корректный email адрес';
                        isValid = false;
                    }
                    break;

                case 'password':
                    if (value.length < 8) {
                        errorMessage = 'Пароль должен содержать минимум 8 символов';
                        isValid = false;
                    } else if (!/(?=.*[a-zA-Z])(?=.*\d)/.test(value)) {
                        errorMessage = 'Пароль должен содержать буквы и цифры';
                        isValid = false;
                    }
                    break;

                case 'confirm_password':
                    const passwordField = form.querySelector('input[name="password"]');
                    if (passwordField && value !== passwordField.value) {
                        errorMessage = 'Пароли не совпадают';
                        isValid = false;
                    }
                    break;

                case 'two_factor_code':
                    if (!/^\d{6}$/.test(value)) {
                        errorMessage = 'Код должен содержать 6 цифр';
                        isValid = false;
                    }
                    break;
            }
        }

        // Показываем ошибку если есть
        if (!isValid) {
            this.showFieldError(field, errorMessage);
        } else {
            this.showFieldSuccess(field);
        }

        return isValid;
    }

    validatePasswordConfirmation(field) {
        const passwordField = field.form.querySelector('input[name="password"]');
        if (passwordField && field.value !== passwordField.value) {
            this.showFieldError(field, 'Пароли не совпадают');
            return false;
        } else {
            this.showFieldSuccess(field);
            return true;
        }
    }

    showFieldError(field, message) {
        field.classList.add('is-invalid');
        field.classList.remove('is-valid');
        
        let feedback = field.parentNode.querySelector('.invalid-feedback');
        if (!feedback) {
            feedback = document.createElement('div');
            feedback.className = 'invalid-feedback';
            field.parentNode.appendChild(feedback);
        }
        feedback.textContent = message;
    }

    showFieldSuccess(field) {
        field.classList.add('is-valid');
        field.classList.remove('is-invalid');
        
        const feedback = field.parentNode.querySelector('.invalid-feedback');
        if (feedback) {
            feedback.remove();
        }
    }

    clearFieldError(field) {
        field.classList.remove('is-invalid', 'is-valid');
        const feedback = field.parentNode.querySelector('.invalid-feedback');
        if (feedback) {
            feedback.remove();
        }
    }

    initPasswordStrength() {
        const passwordField = document.querySelector('input[name="password"]');
        if (passwordField) {
            // Создаем индикатор силы пароля
            const strengthContainer = document.createElement('div');
            strengthContainer.className = 'password-strength';
            strengthContainer.innerHTML = `
                <div class="password-strength-bar">
                    <div class="password-strength-fill"></div>
                </div>
                <div class="password-strength-text">Введите пароль</div>
            `;
            passwordField.parentNode.appendChild(strengthContainer);
        }
    }

    updatePasswordStrength(password) {
        const strengthContainer = document.querySelector('.password-strength');
        if (!strengthContainer) return;

        const strengthBar = strengthContainer.querySelector('.password-strength-fill');
        const strengthText = strengthContainer.querySelector('.password-strength-text');
        
        if (!password) {
            strengthContainer.className = 'password-strength';
            strengthText.textContent = 'Введите пароль';
            return;
        }

        let strength = 0;
        let strengthClass = '';
        let strengthMessage = '';

        // Проверяем длину
        if (password.length >= 8) strength += 1;
        if (password.length >= 12) strength += 1;

        // Проверяем наличие букв
        if (/[a-z]/.test(password)) strength += 1;
        if (/[A-Z]/.test(password)) strength += 1;

        // Проверяем наличие цифр
        if (/\d/.test(password)) strength += 1;

        // Проверяем наличие спецсимволов
        if (/[!@#$%^&*(),.?":{}|<>]/.test(password)) strength += 1;

        // Определяем класс и сообщение
        if (strength < 2) {
            strengthClass = 'password-strength-weak';
            strengthMessage = 'Слабый пароль';
        } else if (strength < 4) {
            strengthClass = 'password-strength-medium';
            strengthMessage = 'Средний пароль';
        } else if (strength < 6) {
            strengthClass = 'password-strength-strong';
            strengthMessage = 'Хороший пароль';
        } else {
            strengthClass = 'password-strength-very-strong';
            strengthMessage = 'Отличный пароль';
        }

        strengthContainer.className = `password-strength ${strengthClass}`;
        strengthText.textContent = strengthMessage;
    }

    initFormValidation() {
        // Валидация в реальном времени
        document.querySelectorAll('input, select, textarea').forEach(field => {
            field.addEventListener('blur', (e) => this.validateField(e.target));
        });
    }

    setButtonLoading(button, loading) {
        if (loading) {
            button.disabled = true;
            button.classList.add('loading');
            button.setAttribute('data-original-text', button.textContent);
            button.textContent = 'Загрузка...';
        } else {
            button.disabled = false;
            button.classList.remove('loading');
            button.textContent = button.getAttribute('data-original-text') || button.textContent;
        }
    }

    handleAction(action, button) {
        switch (action) {
            case 'check-username':
                this.checkUsername(button);
                break;
            case 'check-email':
                this.checkEmail(button);
                break;
            case 'send-verification':
                this.sendVerification(button);
                break;
            case 'toggle-password':
                this.togglePasswordVisibility(button);
                break;
        }
    }

    checkUsername(button) {
        const usernameField = document.querySelector('input[name="username"]');
        if (!usernameField) return;

        const username = usernameField.value.trim();
        if (!username) return;

        this.setButtonLoading(button, true);

        fetch(`/auth/api/check-username?username=${encodeURIComponent(username)}`)
            .then(response => response.json())
            .then(data => {
                if (data.available) {
                    this.showFieldSuccess(usernameField);
                } else {
                    this.showFieldError(usernameField, data.message);
                }
            })
            .catch(error => {
                console.error('Ошибка проверки имени пользователя:', error);
            })
            .finally(() => {
                this.setButtonLoading(button, false);
            });
    }

    checkEmail(button) {
        const emailField = document.querySelector('input[name="email"]');
        if (!emailField) return;

        const email = emailField.value.trim();
        if (!email) return;

        this.setButtonLoading(button, true);

        fetch(`/auth/api/check-email?email=${encodeURIComponent(email)}`)
            .then(response => response.json())
            .then(data => {
                if (data.available) {
                    this.showFieldSuccess(emailField);
                } else {
                    this.showFieldError(emailField, data.message);
                }
            })
            .catch(error => {
                console.error('Ошибка проверки email:', error);
            })
            .finally(() => {
                this.setButtonLoading(button, false);
            });
    }

    sendVerification(button) {
        const accountType = document.querySelector('select[name="account_type"]').value;
        const accountValue = document.querySelector('input[name="account_value"]').value.trim();
        
        if (!accountType || !accountValue) return;

        this.setButtonLoading(button, true);

        fetch('/auth/api/send-verification', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                type: accountType,
                value: accountValue
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.showNotification(data.message, 'success');
            } else {
                this.showNotification(data.message, 'error');
            }
        })
        .catch(error => {
            console.error('Ошибка отправки кода:', error);
            this.showNotification('Ошибка отправки кода', 'error');
        })
        .finally(() => {
            this.setButtonLoading(button, false);
        });
    }

    togglePasswordVisibility(button) {
        const passwordField = button.parentNode.querySelector('input[type="password"], input[type="text"]');
        if (!passwordField) return;

        if (passwordField.type === 'password') {
            passwordField.type = 'text';
            button.innerHTML = '<i class="fas fa-eye-slash"></i>';
        } else {
            passwordField.type = 'password';
            button.innerHTML = '<i class="fas fa-eye"></i>';
        }
    }

    showNotification(message, type = 'info') {
        const alertClass = `alert-${type}`;
        const alertHtml = `
            <div class="alert ${alertClass} alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        
        const container = document.querySelector('.auth-body');
        if (container) {
            container.insertAdjacentHTML('afterbegin', alertHtml);
            
            // Автоматически скрываем через 5 секунд
            setTimeout(() => {
                const alert = container.querySelector('.alert');
                if (alert) {
                    alert.remove();
                }
            }, 5000);
        }
    }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    new AuthManager();
});

// Дополнительные утилиты
class AuthUtils {
    static formatCurrency(amount) {
        return new Intl.NumberFormat('ru-RU', {
            style: 'currency',
            currency: 'USD'
        }).format(amount);
    }

    static formatDate(date) {
        return new Intl.DateTimeFormat('ru-RU', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        }).format(new Date(date));
    }

    static copyToClipboard(text) {
        navigator.clipboard.writeText(text).then(() => {
            // Показываем уведомление об успешном копировании
            const notification = document.createElement('div');
            notification.className = 'alert alert-success alert-dismissible fade show position-fixed';
            notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999;';
            notification.innerHTML = `
                Скопировано в буфер обмена
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
            document.body.appendChild(notification);
            
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.remove();
                }
            }, 3000);
        });
    }
}

// Экспорт для использования в других модулях
window.AuthManager = AuthManager;
window.AuthUtils = AuthUtils;


















