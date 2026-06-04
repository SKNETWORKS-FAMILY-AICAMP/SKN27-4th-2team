from django.urls import path

from .views import create_pet, delete_pet, update_pet, UserLoginView, UserLogoutView, UserProfileView, UserSignupView

app_name = 'user'

# /users/ 아래에서 사용할 주소들을 정의합니다.
urlpatterns = [
    path('login/', UserLoginView.as_view(), name='login'),
    path('signup/', UserSignupView.as_view(), name='signup'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('profile/pets/', create_pet, name='pet_create'),
    path('profile/pets/<int:pet_id>/edit/', update_pet, name='pet_update'),
    path('profile/pets/<int:pet_id>/delete/', delete_pet, name='pet_delete'),
    path('logout/', UserLogoutView.as_view(), name='logout'),
]
