<?php
session_start();

// Configuration SQLite
define('DB_PATH', __DIR__ . '/../database.sqlite'); // Le fichier sera à la racine du projet

try {
    // Connexion à SQLite
    $pdo = new PDO('sqlite:' . DB_PATH);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    $pdo->setAttribute(PDO::ATTR_DEFAULT_FETCH_MODE, PDO::FETCH_ASSOC);
} catch(PDOException $e) {
    echo json_encode(['success' => false, 'message' => 'Erreur de connexion à la base de données']);
    exit;
}

// Vérifier si l'utilisateur est connecté
if (!isset($_SESSION['user_id'])) {
    echo json_encode(['success' => false, 'message' => 'Vous devez être connecté pour changer votre mot de passe']);
    exit;
}

// Vérifier la méthode de requête
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    echo json_encode(['success' => false, 'message' => 'Méthode non autorisée']);
    exit;
}

// Récupérer les données
$currentPassword = $_POST['current_password'] ?? '';
$newPassword = $_POST['new_password'] ?? '';

// Validation
if (empty($currentPassword) || empty($newPassword)) {
    echo json_encode(['success' => false, 'message' => 'Tous les champs sont requis']);
    exit;
}

if (strlen($newPassword) < 8) {
    echo json_encode(['success' => false, 'message' => 'Le mot de passe doit contenir au moins 8 caractères']);
    exit;
}

try {
    $userId = $_SESSION['user_id'];
    
    // Récupérer le mot de passe actuel de l'utilisateur
    $stmt = $pdo->prepare("SELECT mot_de_passe FROM utilisateurs WHERE id = ?");
    $stmt->execute([$userId]);
    $user = $stmt->fetch();
    
    if (!$user) {
        echo json_encode(['success' => false, 'message' => 'Utilisateur non trouvé']);
        exit;
    }
    
    // Vérifier si le mot de passe actuel est correct
    if (!password_verify($currentPassword, $user['mot_de_passe'])) {
        echo json_encode(['success' => false, 'message' => 'Mot de passe actuel incorrect']);
        exit;
    }
    
    // Hasher le nouveau mot de passe
    $hashedPassword = password_hash($newPassword, PASSWORD_DEFAULT);
    
    // Mettre à jour le mot de passe dans la base de données
    $stmt = $pdo->prepare("UPDATE utilisateurs SET mot_de_passe = ? WHERE id = ?");
    $stmt->execute([$hashedPassword, $userId]);
    
    // Enregistrer l'action dans les logs (optionnel)
    $logStmt = $pdo->prepare("INSERT INTO logs (user_id, action, date_action) VALUES (?, ?, datetime('now'))");
    $logStmt->execute([$userId, 'Changement de mot de passe']);
    
    echo json_encode(['success' => true, 'message' => '✅ Mot de passe changé avec succès !']);
    
} catch(PDOException $e) {
    echo json_encode(['success' => false, 'message' => 'Erreur lors du changement de mot de passe']);
    error_log('Erreur changement mot de passe: ' . $e->getMessage());
}
?>