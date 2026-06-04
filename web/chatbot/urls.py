from django.urls import path

from .views import chat

app_name = 'chatbot'

# /chatbot/ 주소로 들어오면 chat view가 실행됩니다.
urlpatterns = [
    path('', chat, name='chat'),
]
