from django.urls import path
from users import views

urlpatterns = [
    # HTML form endpoints
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    
    # REST API endpoints
    path('api/auth/register/', views.APIRegisterView.as_view(), name='api_register'),
    path('api/auth/profile/', views.APIUserProfileView.as_view(), name='api_profile'),
]
