<?php
// reset_password.php - Cette page reçoit le token dans l'URL

session_start();

// Configuration SQLite
define('DB_PATH', __DIR__ . '/database.sqlite');

try {
    $pdo = new PDO('sqlite:' . DB_PATH);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
} catch(PDOException $e) {
    die("Erreur de connexion à la base de données");
}

// Récupérer le token
$token = $_GET['token'] ?? '';

if (empty($token)) {
    die("Token manquant");
}

// Vérifier le token
try {
    $stmt = $pdo->prepare("
        SELECT t.*, u.id as user_id, u.nom_utilisateur, u.email 
        FROM password_reset_tokens t
        JOIN utilisateurs u ON t.user_id = u.id
        WHERE t.token = ? AND t.utilise = 0 AND t.date_expiration > datetime('now')
    ");
    $stmt->execute([$token]);
    $resetData = $stmt->fetch();

    if (!$resetData) {
        die("❌ Lien de réinitialisation invalide ou expiré. <a href='password_reset.html'>Faire une nouvelle demande</a>");
    }

    $userId = $resetData['user_id'];
    $tokenId = $resetData['id'];

} catch(PDOException $e) {
    die("Erreur lors de la vérification du token");
}
?>

<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nouveau mot de passe</title>
    <link rel="stylesheet" href="account/css/style.css">
    <style>
        .reset-box {
            background: white;
            padding: 40px;
            border-radius: 15px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            animation: slideUp 0.5s ease-out;
            max-width: 450px;
            width: 100%;
        }

        .user-info {
            background: #f8f9fa;
            padding: 12px;
            border-radius: 8px;
            text-align: center;
            margin-bottom: 20px;
            color: #555;
            font-size: 14px;
        }

        .user-info strong {
            color: #333;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="reset-box">
            <h2>🔐 Nouveau mot de passe</h2>
            
            <div class="user-info">
                👤 Compte : <strong><?php echo htmlspecialchars($resetData['nom_utilisateur']); ?></strong><br>
                📧 Email : <strong><?php echo htmlspecialchars($resetData['email']); ?></strong>
            </div>

            <div id="message" class="message hidden"></div>

            <form id="resetForm">
                <input type="hidden" name="token" value="<?php echo htmlspecialchars($token); ?>">
                <input type="hidden" name="token_id" value="<?php echo $tokenId; ?>">
                <input type="hidden" name="user_id" value="<?php echo $userId; ?>">

                <div class="form-group">
                    <label for="newPassword">Nouveau mot de passe</label>
                    <div class="password-input-wrapper">
                        <input type="password" id="newPassword" 
                               placeholder="Entrez votre nouveau mot de passe" required>
                        <span class="toggle-password" onclick="togglePassword('newPassword')">👁️</span>
                    </div>
                    <div class="password-strength" id="passwordStrength"></div>
                </div>

                <div class="form-group">
                    <label for="confirmPassword">Confirmer le mot de passe</label>
                    <div class="password-input-wrapper">
                        <input type="password" id="confirmPassword" 
                               placeholder="Confirmez votre nouveau mot de passe" required>
                        <span class="toggle-password" onclick="togglePassword('confirmPassword')">👁️</span>
                    </div>
                </div>

                <button type="submit" class="btn-primary">Réinitialiser le mot de passe</button>
                <a href="login.html" class="btn-secondary">← Retour à la connexion</a>
            </form>
        </div>
    </div>

    <script>
        document.addEventListener('DOMContentLoaded', function() {
            const form = document.getElementById('resetForm');
            const messageDiv = document.getElementById('message');
            const newPassword = document.getElementById('newPassword');
            const confirmPassword = document.getElementById('confirmPassword');
            const strengthDiv = document.getElementById('passwordStrength');

            // Vérification de la force du mot de passe
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

            function showMessage(text, type) {
                messageDiv.textContent = text;
                messageDiv.className = 'message ' + type;
                messageDiv.classList.remove('hidden');
                
                clearTimeout(window.messageTimeout);
                window.messageTimeout = setTimeout(() => {
                    messageDiv.classList.add('hidden');
                }, 6000);
            }

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

            function togglePassword(inputId) {
                const input = document.getElementById(inputId);
                const toggle = event.target;
                if (input.type === 'password') {
                    input.type = 'text';
                    toggle.textContent = '🙈';
                } else {
                    input.type = 'password';
                    toggle.textContent = '👁️';
                }
            }

            form.addEventListener('submit', function(e) {
                e.preventDefault();
                
                const newPwd = newPassword.value.trim();
                const confirmPwd = confirmPassword.value.trim();

                if (!newPwd || !confirmPwd) {
                    showMessage('Veuillez remplir tous les champs.', 'error');
                    return;
                }

                if (newPwd.length < 8) {
                    showMessage('Le mot de passe doit contenir au moins 8 caractères.', 'error');
                    return;
                }

                if (newPwd !== confirmPwd) {
                    showMessage('Les mots de passe ne correspondent pas.', 'error');
                    return;
                }

                // Envoyer la requête
                const submitBtn = form.querySelector('.btn-primary');
                submitBtn.disabled = true;
                submitBtn.textContent = 'Réinitialisation en cours...';

                const formData = new FormData();
                formData.append('token', document.querySelector('input[name="token"]').value);
                formData.append('token_id', document.querySelector('input[name="token_id"]').value);
                formData.append('user_id', document.querySelector('input[name="user_id"]').value);
                formData.append('new_password', newPwd);

                fetch('password_reset_confirm.php', {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        showMessage(data.message, 'success');
                        // Rediriger après 3 secondes
                        setTimeout(() => {
                            window.location.href = 'login.html';
                        }, 3000);
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
                    submitBtn.textContent = 'Réinitialiser le mot de passe';
                });
            });
        });
    </script>
</body>
</html>