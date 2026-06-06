from django.urls import path
from missions import views

urlpatterns = [
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('community/', views.leaderboard_view, name='community'),
    path('mission/create/', views.create_mission_view, name='create_mission'),
    path('mission/<int:mission_id>/', views.mission_detail_view, name='mission_detail'),
    path('mission/<int:mission_id>/join/', views.join_mission_htmx, name='join_mission'),
    path('mission/<int:mission_id>/complete/', views.complete_mission, name='complete_mission'),
]
