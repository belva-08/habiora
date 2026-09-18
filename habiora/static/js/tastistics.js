// static/js/statistics.js

document.addEventListener('DOMContentLoaded', function() {
    
    // ========================================
    // ANIMATION DES NOMBRES
    // ========================================
    const statNumbers = document.querySelectorAll('.stat-number');
    
    statNumbers.forEach(element => {
        const text = element.textContent.trim();
        const numberMatch = text.match(/[\d\s]+/);
        
        if (numberMatch && numberMatch[0]) {
            const finalValue = parseInt(numberMatch[0].replace(/\s/g, ''));
            const suffix = text.replace(numberMatch[0], '').trim();
            
            if (!isNaN(finalValue) && finalValue > 0) {
                animateNumber(element, finalValue, suffix, 800);
            }
        }
    });
    
    function animateNumber(element, target, suffix, duration) {
        const start = 0;
        const startTime = performance.now();
        
        function update(currentTime) {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            
            // Easing function
            const easeOut = 1 - Math.pow(1 - progress, 3);
            const current = Math.floor(start + (target - start) * easeOut);
            
            element.textContent = formatNumber(current) + suffix;
            
            if (progress < 1) {
                requestAnimationFrame(update);
            }
        }
        
        requestAnimationFrame(update);
    }
    
    function formatNumber(num) {
        return new Intl.NumberFormat('fr-FR').format(num);
    }
    
    // ========================================
    // ANIMATION DES CARTES
    // ========================================
    const cards = document.querySelectorAll('.stat-card, .chart-card, .table-section');
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, { threshold: 0.1 });
    
    cards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        card.style.transition = `opacity 0.5s ease ${index * 0.05}s, transform 0.5s ease ${index * 0.05}s`;
        observer.observe(card);
    });
    
    // ========================================
    // BOUTON IMPRIMER
    // ========================================
    const printBtn = document.querySelector('button[onclick="window.print()"]');
    if (printBtn) {
        printBtn.addEventListener('click', function(e) {
            e.preventDefault();
            window.print();
        });
    }
    
    console.log('✅ Statistiques JS chargé');
});