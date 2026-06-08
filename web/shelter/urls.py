from django.urls import path

from . import views


app_name = "shelter"

urlpatterns = [
    path("", views.shelter_animals_page, name="list"),
    path("<int:pk>/favorite/", views.toggle_favorite, name="toggle_favorite"),
]
