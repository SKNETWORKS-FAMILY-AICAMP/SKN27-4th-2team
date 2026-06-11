from django.urls import path
from django.views.generic import RedirectView

from . import views

app_name = "dog"

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="dog:search", permanent=False), name="home"),
    path("breeds/", views.search, name="search"),
    path("breeds/<int:pk>/", views.detail, name="detail"),
    path("breeds/<int:pk>/favorite/", views.toggle_favorite, name="toggle_favorite"),
]
