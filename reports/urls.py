from django.urls import path
from reports import views

urlpatterns = [
    # REST API endpoints
    path('api/reports/', views.APIReportListCreateView.as_view(), name='api_reports'),
    path('api/reports/geojson/', views.APIReportGeoJsonListView.as_view(), name='api_reports_geojson'),
    path('api/reports/<int:report_id>/verify/', views.APIReportVerificationView.as_view(), name='api_reports_verify'),
    
    # HTML/HTMX endpoints
    path('report/submit/', views.report_issue_view, name='report_submit'),
    path('report/<int:report_id>/verify-vote/', views.verify_issue_htmx, name='report_verify_htmx'),
    path('chatbot/', views.chatbot_view, name='chatbot'),
    path('chatbot/api/', views.chatbot_api_view, name='chatbot_api'),
]
