from django.urls import path

from .views import chat, clear_anonymous_chat, delete_session, toggle_pin, api_chat

app_name = 'chatbot'

# /chatbot/ 주소로 들어오면 chat view가 실행됩니다.
urlpatterns = [
    path('', chat, name='chat'),
    path('delete/<int:session_id>/', delete_session, name='delete_session'),
    path('clear/', clear_anonymous_chat, name='clear_anonymous_chat'),
    path('pin/<int:session_id>/', toggle_pin, name='toggle_pin'),
    path('api/chat/', api_chat, name='api_chat'),
]
