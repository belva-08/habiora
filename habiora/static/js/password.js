// Attendre que le DOM soit chargé
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('passwordForm');
    const messageDiv = document.getElementById('message');
    const currentPassword = document.getElementById('currentPassword');
    const newPassword = document.getElementById('newPassword');
    const confirmPassword = document.getElementById('confirmPassword');
    const strengthDiv = document.getElementById('passwordStrength');

    // Vérifier la force du mot de passe
    newPassword.addEventListener('input', function() {
        const password = this.value;
        const strength = checkPasswordStrength(password);
        
        strengthDiv.className = 'password-strength';
        if (password.length > 0) {
            if (strength === 'weak') {
                strengthDiv.classList.add('weak');
            } else if (strength === 'medium') {
                strengthDiv.classList.add('medium');
            } else if (strength === 'strong') {
                strengthDiv.classList.add('strong');
            }
        }
    });

    // Soumission du formulaire
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Récupérer les valeurs
        const currentPwd = currentPassword.value.trim();
        const newPwd = newPassword.value.trim();
        const confirmPwd = confirmPassword.value.trim();

        // Validation côté client
        if (!currentPwd || !newPwd || !confirmPwd) {
            showMessage('Veuillez remplir tous les champs.', 'error');
            return;
        }

        if (newPwd.length < 8) {
            showMessage('Le nouveau mot de passe doit contenir au moins 8 caractères.', 'error');
            return;
        }

        if (newPwd !== confirmPwd) {
            showMessage('Les mots de passe ne correspondent pas.', 'error');
            return;
        }

        if (currentPwd === newPwd) {
            showMessage('Le nouveau mot de passe doit être différent de l\'ancien.', 'error');
            return;
        }

        // Envoyer la requête au serveur
        changePassword(currentPwd, newPwd);
    });
});

// Fonction pour afficher les messages
function showMessage(text, type) {
    const messageDiv = document.getElementById('message');
    messageDiv.textContent = text;
    messageDiv.className = 'message ' + type;
    messageDiv.classList.remove('hidden');
    
    // Masquer automatiquement après 5 secondes
    clearTimeout(window.messageTimeout);
    window.messageTimeout = setTimeout(() => {
        messageDiv.classList.add('hidden');
    }, 5000);
}

// Fonction pour vérifier la force du mot de passe
function checkPasswordStrength(password) {
    let strength = 0;
    
    if (password.length >= 8) strength++;
    if (password.match(/[a-z]+/)) strength++;
    if (password.match(/[A-Z]+/)) strength++;
    if (password.match(/[0-9]+/)) strength++;
    if (password.match(/[$@#&!]+/)) strength++;
    
    if (strength <= 2) return 'weak';
    if (strength <= 4) return 'medium';
    return 'strong';
}

// Fonction pour afficher/masquer le mot de passe
function togglePassword(inputId) {
    const input = document.getElementById(inputId);
    // Récupérer l'élément span cliqué
    const toggle = event.target;
    
    if (input.type === 'password') {
        input.type = 'text';
        toggle.textContent = '🙈';
    } else {
        input.type = 'password';
        toggle.textContent = '👁️';
    }
}

// Fonction pour changer le mot de passe (requête AJAX)
function changePassword(currentPassword, newPassword) {
    const submitBtn = document.querySelector('.btn-primary');
    submitBtn.disabled = true;
    submitBtn.textContent = 'Changement en cours...';

    // Créer les données à envoyer
    const formData = new FormData();
    formData.append('current_password', currentPassword);
    formData.append('new_password', newPassword);

    // Envoyer la requête
    fetch('change_password.php', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showMessage(data.message, 'success');
            // Réinitialiser le formulaire
            document.getElementById('passwordForm').reset();
            document.getElementById('passwordStrength').className = 'password-strength';
        } else {
            showMessage(data.message, 'error');
        }
    })
    .catch(error => {
        showMessage('Erreur de connexion au serveur.', 'error');
        console.error('Erreur:', error);
    })
    .finally(() => {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Changer le mot de passe';
    });
}