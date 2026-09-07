from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=30, blank=True)
    address = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.user.username


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

# Create your models here.
