from django.urls import path

from .guide_pages import guide_page


app_name = "guide"

urlpatterns = [
    path("", guide_page, name="guide"),
]
