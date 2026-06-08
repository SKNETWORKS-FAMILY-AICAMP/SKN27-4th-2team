from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class TestResult(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='test_results')
    created_at = models.DateTimeField(auto_now_add=True)
    total_score = models.IntegerField()
    earned_score = models.IntegerField()
    result_data = models.JSONField(help_text="Detailed results of the test in JSON format")

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.earned_score}/{self.total_score} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"
