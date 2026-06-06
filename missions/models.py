from django.db import models
from django.conf import settings
from reports.models import EnvironmentalReport

class CleanupMission(models.Model):
    PLANNED = 'planned'
    ONGOING = 'ongoing'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'
    
    STATUS_CHOICES = [
        (PLANNED, 'Planned'),
        (ONGOING, 'Ongoing'),
        (COMPLETED, 'Completed'),
        (CANCELLED, 'Cancelled'),
    ]
    
    title = models.CharField(max_length=150)
    description = models.TextField()
    report = models.ForeignKey(
        EnvironmentalReport, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='missions'
    )
    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='organized_missions'
    )
    scheduled_time = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PLANNED)
    volunteers = models.ManyToManyField(
        settings.AUTH_USER_MODEL, 
        related_name='joined_missions', 
        blank=True
    )
    eco_points_reward = models.IntegerField(default=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - {self.get_status_display()}"
