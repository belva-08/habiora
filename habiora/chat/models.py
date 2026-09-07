from django.db import models
from django.contrib.auth.models import User
from properties.models import Property


class Conversation(models.Model):
	participants = models.ManyToManyField(User, related_name='conversations')
	property = models.ForeignKey(
		Property,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='conversations',
	)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['-updated_at']

	def __str__(self):
		return f'Conversation #{self.pk}'


class Message(models.Model):
	conversation = models.ForeignKey(
		Conversation,
		on_delete=models.CASCADE,
		related_name='messages',
	)
	sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
	content = models.TextField()
	is_read = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['created_at']

	def __str__(self):
		return f'Message de {self.sender.username}'
