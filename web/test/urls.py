from django.urls import path
from .views import get_page, view_saved_result

app_name = 'test'

urlpatterns = [
    path('', get_page, name='test_home'),
    path('result/<int:result_id>/', view_saved_result, name='view_saved_result'),
]