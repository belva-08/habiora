<?php
// password_reset_request.php

session_start();

// Configuration SQLite
define('DB_PATH', __DIR__ . '/database.sqlite');

try {
    $pdo = new PDO('sqlite:' . DB_PATH);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
} catch(PDOException $e) {
    echo json_encode(['success' => false, 'message' => 'Erreur de connexion à la base de données']);
    exit;
}

// Vérifier la méthode
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    echo json_encode(['success' => false, 'message' => 'Méthode non autorisée']);
    exit;
}

// Récupérer l'email
$email = $_POST['email'] ?? '';

if (empty($email) || !filter_var($email, FILTER_VALIDATE_EMAIL)) {
    echo json_encode(['success' => false, 'message' => 'Email invalide']);
    exit;
}

try {
    // Vérifier si l'utilisateur existe
    $stmt = $pdo->prepare("SELECT id, nom_utilisateur FROM utilisateurs WHERE email = ?");
    $stmt->execute([$email]);
    $user = $stmt->fetch();

    if (!$user) {
        // Pour des raisons de sécurité, ne pas indiquer si l'email existe ou non
        echo json_encode(['success' => true, 'message' => '📧 Si cet email existe, un lien de réinitialisation vous a été envoyé.']);
        exit;
    }

    // Générer un token unique
    $token = bin2hex(random_bytes(32));
    $expiration = date('Y-m-d H:i:s', strtotime('+1 hour'));

    // Supprimer les anciens tokens pour cet utilisateur
    $stmt = $pdo->prepare("DELETE FROM password_reset_tokens WHERE user_id = ? AND utilise = 0");
    $stmt->execute([$user['id']]);

    // Enregistrer le nouveau token
    $stmt = $pdo->prepare("
        INSERT INTO password_reset_tokens (user_id, token, date_expiration) 
        VALUES (?, ?, ?)
    ");
    $stmt->execute([$user['id'], $token, $expiration]);

    // Ici, vous devriez envoyer un email avec le lien
    // Pour les tests, on va afficher le lien dans la réponse
    $resetLink = "http://" . $_SERVER['HTTP_HOST'] . dirname($_SERVER['PHP_SELF']) . "/reset_password.php?token=" . $token;
    
    // En production, envoyez un email
    // mail($email, "Réinitialisation de mot de passe", "Cliquez sur ce lien: " . $resetLink);
    
    // Log
    $stmt = $pdo->prepare("INSERT INTO logs (user_id, action, date_action) VALUES (?, ?, datetime('now'))");
    $stmt->execute([$user['id'], 'Demande de réinitialisation de mot de passe']);

    // Pour les tests, on renvoie le lien dans la réponse
    // En production, NE RENVOYEZ PAS le lien dans la réponse JSON
    echo json_encode([
        'success' => true, 
        'message' => '📧 Si cet email existe, un lien de réinitialisation vous a été envoyé.',
        // Supprimez cette ligne en production
        'test_link' => $resetLink 
    ]);

} catch(PDOException $e) {
    echo json_encode(['success' => false, 'message' => 'Erreur lors du traitement']);
    error_log('Erreur reset password: ' . $e->getMessage());
}
?>