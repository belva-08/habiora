// static/js/main.js

document.addEventListener('DOMContentLoaded', function() {
    
    // ========================================
    // 1. MESSAGES AUTO-DISSOLVANTS
    // ========================================
    const messages = document.querySelectorAll('.alert');
    messages.forEach(msg => {
        setTimeout(() => {
            msg.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
            msg.style.opacity = '0';
            msg.style.transform = 'translateY(-20px)';
            setTimeout(() => msg.remove(), 500);
        }, 5000);
    });

    // ========================================
    // 2. SMOOTH SCROLL POUR LES ANCRES
    // ========================================
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;
            
            const target = document.querySelector(targetId);
            if (target) {
                e.preventDefault();
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // ========================================
    // 3. HEADER OMBRE AU SCROLL
    // ========================================
    const header = document.querySelector('.navbar');
    if (header) {
        window.addEventListener('scroll', function() {
            if (window.scrollY > 50) {
                header.style.boxShadow = '0 5px 30px rgba(0,0,0,0.5)';
            } else {
                header.style.boxShadow = 'none';
            }
        });
    }

    console.log('✅ Habiora - JavaScript chargé !');
});