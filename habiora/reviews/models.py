from django.db import models
from django.contrib.auth.models import User
from properties.models import Property


class Review(models.Model):
	property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='reviews')
	author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
	rating = models.PositiveSmallIntegerField(default=5)
	comment = models.TextField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True)


class IncidentReport(models.Model):
	STATUS_CHOICES = [
		('pending', 'En attente'),
		('resolved', 'Résolu'),
		('rejected', 'Rejeté'),
	]

	reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='incident_reports')
	property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='incident_reports')
	description = models.TextField()
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
	admin_notes = models.TextField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
