from django.conf import settings
from django.db import models


class ChatSession(models.Model):
    """한 번의 챗봇 대화방을 의미합니다."""

    # 한 사용자는 여러 개의 대화방을 가질 수 있습니다.
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chat_sessions')
    title = models.CharField(max_length=80, default='새 대화')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # 채팅 내역에서 최근 대화가 위에 오도록 정렬합니다.
        ordering = ['-updated_at']

    def __str__(self):
        return f'{self.title} - {self.user}'


class ChatMessage(models.Model):
    """챗봇 대화방 안에 저장되는 개별 메시지입니다."""

    # role이 user이면 사용자가 보낸 말, assistant이면 챗봇 답변입니다.
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
    ]

    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    intent = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # 한 대화방 안에서는 오래된 메시지부터 순서대로 보여줍니다.
        ordering = ['created_at']

    def __str__(self):
        return f'{self.role}: {self.content[:30]}'
