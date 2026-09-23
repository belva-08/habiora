from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    """Profil utilisateur étendu"""
    ROLE_CHOICES = [
        ('client', 'Client'),
        ('proprietaire', 'Propriétaire'),
        ('admin', 'Administrateur'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='client')
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    bio = models.TextField(max_length=500, blank=True)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, default='Yaoundé')
    profile_picture = models.ImageField(upload_to='user_avatars/', null=True, blank=True)

    is_verified = models.BooleanField(default=False)
    verification_status = models.CharField(
        max_length=20,
        choices=[
            ('not_submitted', 'Non soumis'),
            ('pending', 'En attente'),
            ('approved', 'Approuvé'),
            ('rejected', 'Rejeté'),
        ],
        default='not_submitted'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_activity = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profil de {self.user.username} ({self.get_role_display()})"

    def is_proprietaire(self):
        return self.role == 'proprietaire'

    def is_client(self):
        return self.role == 'client'

    def is_admin(self):
        return self.role == 'admin' or self.user.is_superuser


class OwnerVerification(models.Model):
    """Vérification des propriétaires"""
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('approved', 'Approuvé'),
        ('rejected', 'Rejeté'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='owner_verification')
    identity_document = models.FileField(upload_to='owner_documents/identity/', null=True, blank=True)
    proof_of_ownership = models.FileField(upload_to='owner_documents/proof/', null=True, blank=True)
    tax_identification = models.FileField(upload_to='owner_documents/tax/', null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_notes = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Vérification de {self.user.username} - {self.get_status_display()}"


class AdminActionLog(models.Model):
    """Journal des actions de l'administrateur"""
    ACTION_TYPES = [
        ('user_activate', 'Activation utilisateur'),
        ('user_deactivate', 'Désactivation utilisateur'),
        ('user_delete', 'Suppression utilisateur'),
        ('user_verify', 'Vérification utilisateur'),
        ('user_reject', 'Rejet utilisateur'),
        ('property_approve', 'Approbation annonce'),
        ('property_reject', 'Rejet annonce'),
        ('property_delete', 'Suppression annonce'),
        ('incident_resolve', 'Résolution signalement'),
    ]

    admin = models.ForeignKey(User, on_delete=models.CASCADE, related_name='accounts_admin_actions')
    action_type = models.CharField(max_length=30, choices=ACTION_TYPES)
    description = models.TextField()
    target_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='accounts_targeted_actions')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
