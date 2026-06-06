from django.conf import settings
from django.db import models


class ChatSession(models.Model):
    """A single chatbot conversation owned by a user."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chat_sessions')
    title = models.CharField(max_length=80, default='새 대화')
    context_summary = models.TextField(blank=True)
    last_user_preferences = models.JSONField(default=dict, blank=True)
    last_recommended_breeds = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f'{self.title} - {self.user}'


class ChatMessage(models.Model):
    """A single user or assistant message inside a chat session."""

    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
    ]

    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    intent = models.CharField(max_length=50, blank=True)
    sources = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.role}: {self.content[:30]}'


class RecommendationResult(models.Model):
    """Stores breed recommendation results generated during a chat."""

    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name='recommendation_results',
    )
    message = models.ForeignKey(
        ChatMessage,
        on_delete=models.CASCADE,
        related_name='recommendation_results',
    )
    breeds = models.JSONField(default=list, blank=True)
    user_preferences = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        breed_names = ', '.join(self.breeds[:3]) if self.breeds else 'No breeds'
        return f'{breed_names} - {self.session_id}'
