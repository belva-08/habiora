from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Property(models.Model):
    PROPERTY_TYPES = [
        ('appartement', 'Appartement'),
        ('maison', 'Maison'),
        ('studio', 'Studio'),
        ('duplex', 'Duplex'),
        ('villa', 'Villa'),
        ('chambre', 'Chambre à louer'),
    ]

    AVAILABILITY_STATUS = [
        ('disponible', 'Disponible'),
        ('occupe', 'Occupé'),
        ('en_travaux', 'En travaux'),
        ('indisponible', 'Indisponible'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    property_type = models.CharField(max_length=20, choices=PROPERTY_TYPES)
    price = models.DecimalField(max_digits=10, decimal_places=0)
    surface_area = models.IntegerField(help_text="Surface en m²")

    quartier = models.CharField(max_length=100)
    address = models.CharField(max_length=255)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    number_rooms = models.IntegerField(default=0)
    number_bathrooms = models.IntegerField(default=0)
    furnished = models.BooleanField(default=False)
    has_kitchen = models.BooleanField(default=True)
    has_parking = models.BooleanField(default=False)
    has_security = models.BooleanField(default=False)
    has_wifi = models.BooleanField(default=False)
    has_air_conditioning = models.BooleanField(default=False)
    has_balcony = models.BooleanField(default=False)

    availability_status = models.CharField(max_length=20, choices=AVAILABILITY_STATUS, default='disponible')
    is_approved = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    views_count = models.IntegerField(default=0)
    virtual_tour_url = models.URLField(blank=True, null=True)

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='properties')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_confirmation_date = models.DateTimeField(default=timezone.now)
    confirmation_pending = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.quartier}"

    def get_equipments_list(self):
        equipments = []
        if self.has_wifi:
            equipments.append('WiFi')
        if self.has_parking:
            equipments.append('Parking')
        if self.has_security:
            equipments.append('Sécurité')
        if self.has_air_conditioning:
            equipments.append('Climatisation')
        if self.has_balcony:
            equipments.append('Balcon')
        if self.has_kitchen:
            equipments.append('Cuisine équipée')
        if self.furnished:
            equipments.append('Meublé')
        return equipments

    def get_rating(self):
        reviews = self.reviews.all()
        if reviews:
            total = sum(r.rating for r in reviews)
            return round(total / reviews.count(), 1)
        return 0

    def get_reviews_count(self):
        return self.reviews.count()


class PropertyImage(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='property_images/')
    is_main = models.BooleanField(default=False)
    caption = models.CharField(max_length=100, blank=True)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f'Image de {self.property.title}'
