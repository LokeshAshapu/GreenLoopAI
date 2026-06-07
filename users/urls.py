from django.urls import path
from users import views

urlpatterns = [
    # HTML form endpoints
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('forgot-password/reset/<str:uidb64>/<str:token>/', views.reset_password_confirm_view, name='password_reset_confirm'),
    
    # REST API endpoints
    path('api/auth/register/', views.APIRegisterView.as_view(), name='api_register'),
    path('api/auth/profile/', views.APIUserProfileView.as_view(), name='api_profile'),
]
