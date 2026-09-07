// static/js/accueil.js

document.addEventListener('DOMContentLoaded', function() {
    
    // ========================================
    // ANIMATION DES CARTES AU SCROLL
    // ========================================
    const cards = document.querySelectorAll(
        '.presentation-card, .property-card, .security-grid > div, .step'
    );
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, { threshold: 0.1 });
    
    cards.forEach(card => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(30px)';
        card.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        observer.observe(card);
    });

    // ========================================
    // ANIMATION DES CARTES FLOTTANTES
    // ========================================
    const floatCards = document.querySelectorAll('.floating-info, .image-tag');
    floatCards.forEach((card, index) => {
        card.style.animationDelay = `${index * 1}s`;
    });

    console.log('✅ Accueil - Animations chargées !');
});