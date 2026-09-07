from django.db import models
from django.contrib.auth.models import User
from properties.models import Property


class Booking(models.Model):
	STATUS_CHOICES = [
		('pending', 'En attente'),
		('confirmed', 'Confirmée'),
		('completed', 'Terminée'),
		('cancelled', 'Annulée'),
	]

	property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='bookings')
	tenant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
	start_date = models.DateField()
	end_date = models.DateField()
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return f'{self.tenant.username} - {self.property.title}'
