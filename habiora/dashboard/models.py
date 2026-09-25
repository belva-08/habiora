from django.db import models
from django.contrib.auth.models import User
from properties.models import Property
import uuid
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class AdminActionLog(models.Model):
    """
    Journal des actions de l'administrateur
    """
    ACTION_TYPES = [
        ('user_activate', 'Activation utilisateur'),
        ('user_deactivate', 'Désactivation utilisateur'),
        ('property_approve', 'Approbation annonce'),
        ('property_reject', 'Rejet annonce'),
        ('property_delete', 'Suppression annonce'),
        ('owner_verify', 'Vérification propriétaire'),
        ('incident_resolve', 'Résolution signalement'),
    ]
    
    admin = models.ForeignKey(User, on_delete=models.CASCADE, related_name='dashboard_admin_actions')
    action_type = models.CharField(max_length=30, choices=ACTION_TYPES)
    description = models.TextField()
    target_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='dashboard_targeted_actions')
    target_property = models.ForeignKey(Property, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.admin.username} - {self.get_action_type_display()} - {self.created_at}"
    
    class Meta:
        ordering = ['-created_at']

class VerificationRequest(models.Model):
    """Demande de vérification d'identité ou de document"""
    
    TYPE_CHOICES = [
        ('identity', _('Pièce d\'identité')),
        ('address', _('Justificatif de domicile')),
        ('diploma', _('Diplôme')),
        ('business', _('Compte professionnel')),
        ('other', _('Autre')),
    ]
    
    STATUS_CHOICES = [
        ('pending', _('En attente')),
        ('in_review', _('En cours d\'examen')),
        ('approved', _('Approuvée')),
        ('rejected', _('Rejetée')),
        ('cancelled', _('Annulée')),
    ]
    
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='verification_requests'
    )
    
    request_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    
    # Contenu soumis
    document = models.FileField(upload_to='verifications/%Y/%m/', blank=True, null=True)
    message = models.TextField(_("Message du demandeur"), blank=True)
    
    # Traitement admin
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='processed_verifications'
    )
    admin_notes = models.TextField(_("Notes internes"), blank=True)
    rejection_reason = models.TextField(_("Motif du rejet"), blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
        ]
    
    def __str__(self):
        return f"#{self.id} {self.get_request_type_display()} - {self.user}"
    
    @property
    def is_final(self):
        return self.status in ('approved', 'rejected', 'cancelled')


class VerificationLog(models.Model):
    """Historique des actions sur une demande"""
    
    request = models.ForeignKey(
        VerificationRequest, on_delete=models.CASCADE, related_name='logs'
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    action = models.CharField(max_length=50)
    old_status = models.CharField(max_length=20, blank=True)
    new_status = models.CharField(max_length=20, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
