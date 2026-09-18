// static/js/dashboard.js

document.addEventListener('DOMContentLoaded', function() {
    
    // ========================================
    // MESSAGES AUTO-DISSOLVANTS
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
    // ANIMATION DES CARTES
    // ========================================
    const cards = document.querySelectorAll('.stat-card, .content-card');
    
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
        card.style.transform = 'translateY(20px)';
        card.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
        observer.observe(card);
    });

    // ========================================
    // CONFIRMATION DE SUPPRESSION
    // ========================================
    const deleteButtons = document.querySelectorAll('.btn-sm-danger');
    deleteButtons.forEach(btn => {
        btn.addEventListener('click', function(e) {
            if (!confirm('Êtes-vous sûr de vouloir supprimer cet élément ?')) {
                e.preventDefault();
            }
        });
    });

    // ========================================
    // ACTIVER/DÉSACTIVER UNE ANNONCE
    // ========================================
    const toggleButtons = document.querySelectorAll('.btn-sm-warning');
    toggleButtons.forEach(btn => {
        btn.addEventListener('click', function(e) {
            const action = this.dataset.action || 'activer';
            if (!confirm(`Voulez-vous ${action} cette annonce ?`)) {
                e.preventDefault();
            }
        });
    });

    console.log('✅ Dashboard JS chargé');
});