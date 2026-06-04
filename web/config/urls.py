from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView


# 프로젝트 전체 URL 연결표입니다.
# include(...)는 각 앱의 urls.py로 주소 처리를 넘기는 역할을 합니다.
urlpatterns = [
    path('', TemplateView.as_view(template_name='main/home.html'), name='home'),
    path('admin/', admin.site.urls),
    path('chatbot/', include('chatbot.urls')),
    path('users/', include('user.urls')),
]
