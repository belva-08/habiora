from django.contrib.auth.models import User
from django.db import models

from properties.models import Property


class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites')
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='favorites')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'property'],
                name='unique_user_property_favorite',
            ),
        ]

    def __str__(self):
        return f'{self.user.username} - {self.property.title}'
