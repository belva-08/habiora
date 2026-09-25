from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

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



class Profile(models.Model):

    GENDER_CHOICES = [
        ('M', _('Homme')),
        ('F', _('Femme')),
        ('O', _('Autre')),
        ('N', _('Préfère ne pas dire')),
    ]

    LANGUAGE_CHOICES = [
        ('fr', 'Français'),
        ('en', 'English'),
        ('es', 'Español'),
    ]

    THEME_CHOICES = [
        ('light', _('Clair')),
        ('dark', _('Sombre')),
        ('auto', _('Automatique')),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='account_profile')

    avatar = models.ImageField(_("avatar"), upload_to='avatars/%Y/%m/', blank=True, null=True)
    bio = models.TextField(_("biographie"), max_length=500, blank=True)
    birth_date = models.DateField(_("date de naissance"), null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    location = models.CharField(_("localisation"), max_length=100, blank=True)
    website = models.URLField(_("site web"), blank=True)

    language = models.CharField(max_length=5, choices=LANGUAGE_CHOICES, default='fr')
    timezone = models.CharField(max_length=50, default='UTC')
    theme = models.CharField(max_length=10, choices=THEME_CHOICES, default='auto')
    email_notifications = models.BooleanField(default=True)
    push_notifications = models.BooleanField(default=False)

    # Spécifique propriétaire
    company_name = models.CharField(max_length=100, blank=True)
    siret = models.CharField(max_length=14, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("profil")
        verbose_name_plural = _("profils")

    def __str__(self):
        return f"Profil de {self.user.username}"

    @property
    def age(self):
        if not self.birth_date:
            return None
        today = timezone.now().date()
        return today.year - self.birth_date.year - (
            (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
        )


class UserSession(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    session_key = models.CharField(max_length=40, unique=True, db_index=True)

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    device_name = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-last_activity']
        verbose_name = _("session")
        verbose_name_plural = _("sessions")

    def __str__(self):
        return f"Session {self.user.username} - {self.ip_address}"


class LoginHistory(models.Model):

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='login_history',
        null=True, blank=True
    )
    email_attempted = models.EmailField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    success = models.BooleanField(default=True)
    failure_reason = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _("historique de connexion")
        verbose_name_plural = _("historiques de connexion")


class EmailChangeRequest(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='email_changes')
    new_email = models.EmailField()
    token = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    confirmed_at = models.DateTimeField(null=True, blank=True)

    def is_valid(self):
        return not self.confirmed_at and self.expires_at > timezone.now()

        # accounts/models.py — AJOUTER ce modèle

class OwnerRequest(models.Model):

    STATUS_CHOICES = [
        ('pending', _('En attente')),
        ('in_review', _('En cours d\'examen')),
        ('approved', _('Approuvée')),
        ('rejected', _('Rejetée')),
    ]

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='owner_request'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)

    # Informations demandées au propriétaire
    company_name = models.CharField(max_length=100, blank=True)
    siret = models.CharField(max_length=14, blank=True)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=10)
    phone = models.CharField(max_length=20)
    message = models.TextField(blank=True, help_text="Pourquoi souhaitez-vous devenir propriétaire ?")

    # Validation admin
    processed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='processed_owner_requests'
    )
    processed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Demande propriétaire - {self.user.email} ({self.status})"

    @property
    def is_final(self):
        return self.status in ('approved', 'rejected')