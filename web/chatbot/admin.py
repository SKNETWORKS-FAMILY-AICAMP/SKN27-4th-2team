from django.contrib import admin

from .models import ChatMessage, ChatSession, RecommendationResult


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'title', 'updated_at')
    search_fields = ('title', 'user__username')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'session', 'role', 'intent', 'created_at')
    list_filter = ('role', 'intent')
    search_fields = ('content', 'session__title')
    readonly_fields = ('created_at',)


@admin.register(RecommendationResult)
class RecommendationResultAdmin(admin.ModelAdmin):
    list_display = ('id', 'session', 'message', 'created_at')
    search_fields = ('session__title',)
    readonly_fields = ('created_at',)
