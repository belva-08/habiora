from django.db import models
from django.contrib.auth.models import User

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('property_validation', 'Validation annonce'),
        ('property_rejection', 'Rejet annonce'),
        ('new_property', 'Nouvelle annonce'),
        ('booking_request', 'Demande réservation'),
        ('booking_confirmed', 'Réservation confirmée'),
        ('booking_cancelled', 'Réservation annulée'),
        ('owner_verification', 'Vérification propriétaire'),
        ('availability_reminder', 'Rappel disponibilité'),
        ('new_message', 'Nouveau message'),
        ('incident_report', 'Signalement'),
        ('system', 'Notification système'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    link = models.URLField(blank=True, null=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Notification pour {self.user.username} - {self.get_type_display()}"
# Create your models here.
