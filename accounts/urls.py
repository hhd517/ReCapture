from django.urls import path
from . import views
from .views import signup_done

app_name = 'accounts'

urlpatterns = [
    path('mypage/', views.mypage, name='mypage'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('logout/', views.logout_view, name='logout'),
    path("signup/done/", signup_done, name="signup_done"),

]