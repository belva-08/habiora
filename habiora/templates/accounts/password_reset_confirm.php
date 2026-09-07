<?php
// password_reset_confirm.php - Backend pour la confirmation

session_start();

// Configuration SQLite
define('DB_PATH', __DIR__ . '/database.sqlite');

// Headers pour JSON
header('Content-Type: application/json');

try {
    $pdo = new PDO('sqlite:' . DB_PATH);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    $pdo->setAttribute(PDO::ATTR_DEFAULT_FETCH_MODE, PDO::FETCH_ASSOC);
} catch(PDOException $e) {
    echo json_encode(['success' => false, 'message' => 'Erreur de connexion à la base de données']);
    exit;
}

// Vérifier la méthode
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    echo json_encode(['success' => false, 'message' => 'Méthode non autorisée']);
    exit;
}

// Récupérer l'action
$action = $_POST['action'] ?? '';

if ($action === 'verify') {
    // VÉRIFICATION DU TOKEN
    verifyToken($pdo);
} elseif ($action === 'confirm') {
    // CONFIRMATION DE LA RÉINITIALISATION
    confirmReset($pdo);
} else {
    echo json_encode(['success' => false, 'message' => 'Action non reconnue']);
}

// Fonction de vérification du token
function verifyToken($pdo) {
    $token = $_POST['token'] ?? '';

    if (empty($token)) {
        echo json_encode(['success' => false, 'message' => 'Token manquant']);
        return;
    }

    try {
        // Vérifier le token
        $stmt = $pdo->prepare("
            SELECT t.id as token_id, t.user_id, t.date_creation, t.date_expiration, 
                   u.nom_utilisateur, u.email
            FROM password_reset_tokens t
            JOIN utilisateurs u ON t.user_id = u.id
            WHERE t.token = ? AND t.utilise = 0 AND t.date_expiration > datetime('now')
        ");
        $stmt->execute([$token]);
        $result = $stmt->fetch();

        if (!$result) {
            echo json_encode([
                'success' => false, 
                'message' => 'Ce lien de réinitialisation est invalide ou a expiré. Veuillez faire une nouvelle demande.'
            ]);
            return;
        }

        // Token valide
        echo json_encode([
            'success' => true,
            'user_id' => $result['user_id'],
            'token_id' => $result['token_id'],
            'user_name' => $result['nom_utilisateur'],
            'email' => $result['email'],
            'date' => date('d/m/Y à H:i', strtotime($result['date_creation'])),
            'expires' => date('d/m/Y à H:i', strtotime($result['date_expiration']))
        ]);

    } catch(PDOException $e) {
        echo json_encode(['success' => false, 'message' => 'Erreur lors de la vérification']);
        error_log('Erreur verify token: ' . $e->getMessage());
    }
}

// Fonction de confirmation de la réinitialisation
function confirmReset($pdo) {
    $token = $_POST['token'] ?? '';
    $userId = $_POST['user_id'] ?? '';
    $tokenId = $_POST['token_id'] ?? '';

    if (empty($token) || empty($userId) || empty($tokenId)) {
        echo json_encode(['success' => false, 'message' => 'Données manquantes']);
        return;
    }

    try {
        // Vérifier que le token existe toujours
        $stmt = $pdo->prepare("
            SELECT * FROM password_reset_tokens 
            WHERE id = ? AND user_id = ? AND token = ? AND utilise = 0 
            AND date_expiration > datetime('now')
        ");
        $stmt->execute([$tokenId, $userId, $token]);
        $result = $stmt->fetch();

        if (!$result) {
            echo json_encode([
                'success' => false, 
                'message' => 'Ce lien a déjà été utilisé ou a expiré.'
            ]);
            return;
        }

        // Marquer le token comme utilisé
        $stmt = $pdo->prepare("UPDATE password_reset_tokens SET utilise = 1 WHERE id = ?");
        $stmt->execute([$tokenId]);

        // Log
        $stmt = $pdo->prepare("
            INSERT INTO logs (user_id, action, date_action) 
            VALUES (?, ?, datetime('now'))
        ");
        $stmt->execute([$userId, 'Réinitialisation de mot de passe confirmée']);

        echo json_encode([
            'success' => true,
            'message' => '✅ Réinitialisation confirmée ! Vous allez être redirigé.'
        ]);

    } catch(PDOException $e) {
        echo json_encode(['success' => false, 'message' => 'Erreur lors de la confirmation']);
        error_log('Erreur confirm reset: ' . $e->getMessage());
    }
}
?>