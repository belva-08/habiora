<?php
// account/change_password.php - Version simplifiée sans logs

session_start();

// Configuration SQLite
define('DB_PATH', __DIR__ . '/../database.sqlite');

try {
    $pdo = new PDO('sqlite:' . DB_PATH);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
} catch(PDOException $e) {
    echo json_encode(['success' => false, 'message' => 'Erreur de connexion à la base de données']);
    exit;
}

// Vérifier si l'utilisateur est connecté
if (!isset($_SESSION['user_id'])) {
    echo json_encode(['success' => false, 'message' => 'Vous devez être connecté']);
    exit;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    echo json_encode(['success' => false, 'message' => 'Méthode non autorisée']);
    exit;
}

$currentPassword = $_POST['current_password'] ?? '';
$newPassword = $_POST['new_password'] ?? '';

// Validations
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
    
    $stmt = $pdo->prepare("SELECT mot_de_passe FROM utilisateurs WHERE id = ?");
    $stmt->execute([$userId]);
    $user = $stmt->fetch();
    
    if (!$user) {
        echo json_encode(['success' => false, 'message' => 'Utilisateur non trouvé']);
        exit;
    }
    
    if (!password_verify($currentPassword, $user['mot_de_passe'])) {
        echo json_encode(['success' => false, 'message' => 'Mot de passe actuel incorrect']);
        exit;
    }
    
    $hashedPassword = password_hash($newPassword, PASSWORD_DEFAULT);
    
    $stmt = $pdo->prepare("UPDATE utilisateurs SET mot_de_passe = ? WHERE id = ?");
    $stmt->execute([$hashedPassword, $userId]);
    
    echo json_encode(['success' => true, 'message' => '✅ Mot de passe changé avec succès !']);
    
} catch(PDOException $e) {
    echo json_encode(['success' => false, 'message' => 'Erreur lors du changement de mot de passe']);
    error_log('Erreur: ' . $e->getMessage());
}

// Fichier: install.php - À exécuter une seule fois

$dbPath = __DIR__ . '/database.sqlite';

try {
    $pdo = new PDO('sqlite:' . $dbPath);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    
    echo "✅ Connexion à SQLite établie<br><br>";

    // Table des utilisateurs
    $pdo->exec("
        CREATE TABLE IF NOT EXISTS utilisateurs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom_utilisateur VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            mot_de_passe VARCHAR(255) NOT NULL,
            date_creation DATETIME DEFAULT CURRENT_TIMESTAMP,
            derniere_connexion DATETIME
        )
    ");
    echo "✅ Table 'utilisateurs' créée<br>";

    // Table des logs
    $pdo->exec("
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            action VARCHAR(255) NOT NULL,
            date_action DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES utilisateurs(id) ON DELETE CASCADE
        )
    ");
    echo "✅ Table 'logs' créée<br>";

    // Table des tokens de réinitialisation
    $pdo->exec("
        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token VARCHAR(255) NOT NULL UNIQUE,
            date_creation DATETIME DEFAULT CURRENT_TIMESTAMP,
            date_expiration DATETIME NOT NULL,
            utilise INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES utilisateurs(id) ON DELETE CASCADE
        )
    ");
    echo "✅ Table 'password_reset_tokens' créée<br><br>";

    // Créer un utilisateur de test
    $stmt = $pdo->prepare("SELECT COUNT(*) FROM utilisateurs WHERE nom_utilisateur = ?");
    $stmt->execute(['test']);
    $count = $stmt->fetchColumn();
    
    if ($count == 0) {
        $hashedPassword = password_hash('password', PASSWORD_DEFAULT);
        $stmt = $pdo->prepare("
            INSERT INTO utilisateurs (nom_utilisateur, email, mot_de_passe) 
            VALUES (?, ?, ?)
        ");
        $stmt->execute(['test', 'test@test.com', $hashedPassword]);
        echo "✅ Utilisateur de test créé (login: test, mot de passe: password)<br>";
    } else {
        echo "ℹ️ L'utilisateur test existe déjà<br>";
    }

    echo "<br><strong>🎉 Installation terminée avec succès !</strong><br>";
    echo "<a href='password_reset.html'>➡️ Aller à la page de réinitialisation</a> | ";
    echo "<a href='account/change_password.html'>➡️ Changer le mot de passe</a>";
    
} catch(PDOException $e) {
    echo "❌ Erreur: " . $e->getMessage();
}
?>