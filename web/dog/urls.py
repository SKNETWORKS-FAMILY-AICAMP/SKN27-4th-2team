from django.urls import path
from .views import get_page

urlpatterns = [
    path('', get_page, name='home')
]