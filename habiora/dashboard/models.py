from django.db import models
from django.contrib.auth.models import User
from properties.models import Property
from bookings.models import Booking
from django.utils import timezone

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
    
    admin = models.ForeignKey(User, on_delete=models.CASCADE, related_name='admin_actions')
    action_type = models.CharField(max_length=30, choices=ACTION_TYPES)
    description = models.TextField()
    target_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='targeted_actions')
    target_property = models.ForeignKey(Property, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.admin.username} - {self.get_action_type_display()} - {self.created_at}"
    
    class Meta:
        ordering = ['-created_at']

# Create your models here.
