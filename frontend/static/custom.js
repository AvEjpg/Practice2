// Дополнительные JavaScript функции для системы

// Инициализация всех tooltips
document.addEventListener('DOMContentLoaded', function() {
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    })
    
    // Автоматическое скрытие алертов
    setTimeout(function() {
        var alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
        alerts.forEach(function(alert) {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);
    
    // Подсветка обязательных полей
    var requiredFields = document.querySelectorAll('[required]');
    requiredFields.forEach(function(field) {
        field.addEventListener('invalid', function(e) {
            e.preventDefault();
            this.classList.add('is-invalid');
            var feedback = document.createElement('div');
            feedback.className = 'invalid-feedback';
            feedback.textContent = 'Это поле обязательно для заполнения';
            this.parentNode.appendChild(feedback);
        });
        
        field.addEventListener('input', function() {
            this.classList.remove('is-invalid');
            var feedback = this.parentNode.querySelector('.invalid-feedback');
            if (feedback) {
                feedback.remove();
            }
        });
    });
    
    // Форматирование телефона
    var phoneFields = document.querySelectorAll('input[type="tel"]');
    phoneFields.forEach(function(field) {
        field.addEventListener('input', function(e) {
            var x = e.target.value.replace(/\D/g, '').match(/(\d{0,1})(\d{0,3})(\d{0,3})(\d{0,2})(\d{0,2})/);
            e.target.value = !x[2] ? x[1] : '+' + x[1] + ' (' + x[2] + ') ' + x[3] + (x[4] ? '-' + x[4] : '') + (x[5] ? '-' + x[5] : '');
        });
    });
});