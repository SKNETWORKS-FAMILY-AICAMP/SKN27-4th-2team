from django.urls import path

from . import views


app_name = "shelter"

urlpatterns = [
    path("", views.shelter_animals_page, name="list"),
]
