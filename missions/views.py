from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.db.models import Sum, Count

from missions.models import CleanupMission
from reports.models import EnvironmentalReport
from users.models import User

# --- Leaderboard View ---

def leaderboard_view(request):
    """
    Renders user leaderboard data sorted by eco_points.
    Splits into Top Volunteers, Top NGOs, and Top Citizens.
    """
    top_citizens = User.objects.filter(role=User.CITIZEN).order_by('-eco_points')[:10]
    top_volunteers = User.objects.filter(role=User.VOLUNTEER).order_by('-eco_points')[:10]
    top_ngos = User.objects.filter(role=User.NGO).order_by('-eco_points')[:10]
    
    context = {
        'top_citizens': top_citizens,
        'top_volunteers': top_volunteers,
        'top_ngos': top_ngos,
    }
    return render(request, 'community.html', context)


# --- Mission Management Actions ---

@login_required
def join_mission_htmx(request, mission_id):
    """
    HTMX action to join or leave a cleanup mission.
    """
    mission = get_object_or_404(CleanupMission, id=mission_id)
    user = request.user
    
    if user in mission.volunteers.all():
        mission.volunteers.remove(user)
        joined = False
    else:
        mission.volunteers.add(user)
        joined = True
        
    return render(request, 'partials/mission_join_btn.html', {
        'mission': mission,
        'joined': joined
    })


@login_required
def complete_mission(request, mission_id):
    """
    Mark a mission as completed. Only the organizer, an NGO, or Municipal Officer/Admin can complete.
    """
    mission = get_object_or_404(CleanupMission, id=mission_id)
    user = request.user
    
    # Permission check
    is_organizer = (mission.organizer == user)
    is_officer_or_ngo = (user.role in [User.NGO, User.MUNICIPAL_OFFICER, User.ADMINISTRATOR])
    
    if not (is_organizer or is_officer_or_ngo):
        messages.error(request, "You do not have permission to mark this mission as completed.")
        return redirect('mission_detail', mission_id=mission.id)
        
    if mission.status == CleanupMission.COMPLETED:
        messages.warning(request, "This mission is already completed.")
        return redirect('mission_detail', mission_id=mission.id)
        
    # Mark completed
    mission.status = CleanupMission.COMPLETED
    mission.save()
    
    # Resolve associated environmental report
    if mission.report:
        mission.report.status = EnvironmentalReport.RESOLVED
        mission.report.save()
        
    # Award Eco Points to all volunteers
    reward = mission.eco_points_reward
    volunteers = mission.volunteers.all()
    for vol in volunteers:
        vol.add_eco_points(reward)
        vol.check_and_award_achievements()
        
    # Award points to organizer
    mission.organizer.add_eco_points(reward + 50) # Bonus points
    mission.organizer.check_and_award_achievements()
    
    messages.success(request, f"Mission '{mission.title}' successfully completed! {volunteers.count()} volunteers were awarded {reward} Eco Points.")
    return redirect('mission_detail', mission_id=mission.id)


@login_required
def create_mission_view(request):
    """
    Creates a new cleanup mission.
    """
    if request.method == 'POST':
        # Enforce Role-Based Access Control (RBAC)
        if request.user.role not in [User.NGO, User.MUNICIPAL_OFFICER, User.ADMINISTRATOR]:
            messages.error(request, "Permission Denied: Only NGOs, Municipal Officers, or Administrators can schedule cleanup missions.")
            return redirect('dashboard')

        title = request.POST.get('title')
        description = request.POST.get('description')
        report_id = request.POST.get('report_id')
        scheduled_time = request.POST.get('scheduled_time')
        points = request.POST.get('eco_points_reward', 100)

        # Allow Citizens, Volunteers, NGOs, and Officers to organize.
        if not (title and description and scheduled_time):
            messages.error(request, "Please fill in all required fields.")
            return redirect('dashboard')

        try:
            report = None
            if report_id:
                report = EnvironmentalReport.objects.get(id=report_id)

            mission = CleanupMission.objects.create(
                title=title,
                description=description,
                report=report,
                organizer=request.user,
                scheduled_time=scheduled_time,
                eco_points_reward=int(points)
            )
            
            # Auto-join organizer
            mission.volunteers.add(request.user)
            
            # If report is set, update status to IN_PROGRESS
            if report:
                report.status = EnvironmentalReport.IN_PROGRESS
                report.save()

            messages.success(request, f"Cleanup mission '{title}' scheduled successfully!")
            return redirect('mission_detail', mission_id=mission.id)
        except Exception as e:
            messages.error(request, f"Failed to schedule mission: {e}")
            return redirect('dashboard')

    return redirect('dashboard')


@login_required
def mission_detail_view(request, mission_id):
    mission = get_object_or_404(CleanupMission, id=mission_id)
    joined = request.user in mission.volunteers.all()
    
    # Permissions to complete
    can_complete = (
        mission.status != CleanupMission.COMPLETED and
        (mission.organizer == request.user or request.user.role in [User.NGO, User.MUNICIPAL_OFFICER, User.ADMINISTRATOR])
    )
    
    return render(request, 'mission_detail.html', {
        'mission': mission,
        'joined': joined,
        'can_complete': can_complete
    })


# --- Dashboard Analytics ---

@login_required
def dashboard_view(request):
    """
    Dynamic analytics dashboard with interactive Leaflet maps,
    summarizing environmental KPIs.
    """
    user = request.user
    
    # Totals
    total_reported = EnvironmentalReport.objects.count()
    total_verified = EnvironmentalReport.objects.filter(status=EnvironmentalReport.VERIFIED).count()
    total_resolved = EnvironmentalReport.objects.filter(status=EnvironmentalReport.RESOLVED).count()
    active_missions_count = CleanupMission.objects.exclude(status=CleanupMission.COMPLETED).exclude(status=CleanupMission.CANCELLED).count()
    
    # Chart dataset: category distribution
    categories = EnvironmentalReport.CATEGORY_CHOICES
    category_counts = []
    for code, label in categories:
        count = EnvironmentalReport.objects.filter(category=code).count()
        category_counts.append({
            'label': label,
            'count': count
        })
        
    # Severity average
    average_severity = EnvironmentalReport.objects.filter(ai_analysis__isnull=False).aggregate(AvgSeverity=Avg('ai_analysis__severity_score'))['AvgSeverity'] or 0.0
    average_severity = round(float(average_severity), 1)
    
    # Fetch recent active reports
    recent_reports = EnvironmentalReport.objects.all().order_by('-created_at')[:6]
    
    # Fetch active cleanup missions
    active_missions = CleanupMission.objects.exclude(status=CleanupMission.COMPLETED).order_by('scheduled_time')[:5]
    
    context = {
        'total_reported': total_reported,
        'total_verified': total_verified,
        'total_resolved': total_resolved,
        'active_missions_count': active_missions_count,
        'category_counts': category_counts,
        'average_severity': average_severity,
        'recent_reports': recent_reports,
        'active_missions': active_missions,
        'user': user,
    }
    return render(request, 'dashboard.html', context)


# Let's import Avg from django.db.models to fix compilation
from django.db.models import Avg
