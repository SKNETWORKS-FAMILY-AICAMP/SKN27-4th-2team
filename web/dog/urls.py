from django.urls import path

from . import views
from .views import get_page

app_name = "dog"

urlpatterns = [
    path("", get_page, name="home"),
    path("breeds/", views.search, name="search"),
    path("breeds/<int:pk>/", views.detail, name="detail"),
    path("breeds/<int:pk>/favorite/", views.toggle_favorite, name="toggle_favorite"),
]