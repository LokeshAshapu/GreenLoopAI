from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from reports.models import EnvironmentalReport

# Global Views
def landing_view(request):
    """
    Renders GreenLoop AI landing page.
    """
    return render(request, 'landing.html')


@login_required
def ai_scanner_view(request):
    """
    Renders VLM drag & drop scanner utility.
    """
    # List current user's scans
    my_scans = EnvironmentalReport.objects.filter(reporter=request.user).order_by('-created_at')
    
    categories = EnvironmentalReport.CATEGORY_CHOICES
    
    return render(request, 'ai_scanner.html', {
        'my_scans': my_scans,
        'categories': categories
    })


@login_required
def scanner_detail_view(request, report_id):
    """
    Detailed diagnostic view of a specific scanned image report.
    """
    report = get_object_or_404(EnvironmentalReport, id=report_id)
    has_ai = hasattr(report, 'ai_analysis')
    
    # Calculate visual scores out of 100
    severity_pct = 0
    risk_pct = 0
    if has_ai:
        severity_pct = int(report.ai_analysis.severity_score * 10)
        risk_pct = int(report.ai_analysis.environmental_risk_index * 10)
        
    return render(request, 'scanner_detail.html', {
        'report': report,
        'has_ai': has_ai,
        'severity_pct': severity_pct,
        'risk_pct': risk_pct
    })


def privacy_view(request):
    """
    Renders Privacy Policy page.
    """
    return render(request, 'privacy.html')


def terms_view(request):
    """
    Renders Terms of Service page.
    """
    return render(request, 'terms.html')


def api_docs_view(request):
    """
    Renders API reference documentation.
    """
    return render(request, 'api_docs.html')


urlpatterns = [
    # Admin Interface
    path('admin/', admin.site.urls),
    
    # Core Frontends
    path('', landing_view, name='landing'),
    path('scanner/', ai_scanner_view, name='scanner'),
    path('scanner/<int:report_id>/', scanner_detail_view, name='scanner_detail'),
    path('privacy/', privacy_view, name='privacy'),
    path('terms/', terms_view, name='terms'),
    path('docs/', api_docs_view, name='api_docs'),
    
    # App-Specific Endpoints
    path('', include('users.urls')),
    path('', include('reports.urls')),
    path('', include('missions.urls')),
    
    # Token Auth APIs
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]

# Add media and static file routes
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
