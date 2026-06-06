from django.db import models
from django.conf import settings
from security.encryption import encrypt_value, decrypt_value
from security.validators import validate_image_upload

class EnvironmentalReport(models.Model):
    # Categories
    PLASTIC_WASTE = 'plastic_waste'
    E_WASTE = 'e_waste'
    WATER_POLLUTION = 'water_pollution'
    OPEN_BURNING = 'open_burning'
    ILLEGAL_DUMPING = 'illegal_dumping'
    DEFORESTATION = 'deforestation'
    
    CATEGORY_CHOICES = [
        (PLASTIC_WASTE, 'Plastic Waste'),
        (E_WASTE, 'E-Waste'),
        (WATER_POLLUTION, 'Water Pollution'),
        (OPEN_BURNING, 'Open Burning'),
        (ILLEGAL_DUMPING, 'Illegal Dumping'),
        (DEFORESTATION, 'Deforestation'),
    ]
    
    # Statuses
    SUBMITTED = 'submitted'
    VERIFYING = 'verifying'
    VERIFIED = 'verified'
    IN_PROGRESS = 'in_progress'
    RESOLVED = 'resolved'
    REJECTED = 'rejected'
    
    STATUS_CHOICES = [
        (SUBMITTED, 'Submitted'),
        (VERIFYING, 'Verifying'),
        (VERIFIED, 'Verified'),
        (IN_PROGRESS, 'In Progress'),
        (RESOLVED, 'Resolved'),
        (REJECTED, 'Rejected'),
    ]
    
    title = models.CharField(max_length=150)
    _description_encrypted = models.TextField(db_column='description_encrypted', blank=True)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    latitude = models.DecimalField(max_digits=12, decimal_places=8)
    longitude = models.DecimalField(max_digits=12, decimal_places=8)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=SUBMITTED)
    image = models.ImageField(upload_to='reports/', validators=[validate_image_upload])
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reports')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def description(self):
        return decrypt_value(self._description_encrypted) if self._description_encrypted else ""

    @description.setter
    def description(self, value):
        self._description_encrypted = encrypt_value(value) if value else ""

    def __str__(self):
        return f"{self.title} - {self.get_category_display()} ({self.get_status_display()})"


class AIAnalysis(models.Model):
    report = models.OneToOneField(EnvironmentalReport, on_delete=models.CASCADE, related_name='ai_analysis')
    confidence_score = models.DecimalField(max_digits=5, decimal_places=2) # e.g. 95.50
    severity_score = models.DecimalField(max_digits=4, decimal_places=2)   # e.g. 7.50 (scale 1-10)
    environmental_risk_index = models.DecimalField(max_digits=4, decimal_places=2) # e.g. 8.20
    recommended_action = models.TextField()
    health_risk_summary = models.TextField()
    raw_response = models.JSONField(blank=True, null=True)
    analyzed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"AI Analysis for Report #{self.report.id} ({self.confidence_score}% Conf)"


class Verification(models.Model):
    report = models.ForeignKey(EnvironmentalReport, on_delete=models.CASCADE, related_name='verifications')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    is_valid = models.BooleanField(default=True)
    comments = models.TextField(blank=True)
    voted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('report', 'user')

    def __str__(self):
        vote = "Valid" if self.is_valid else "Invalid"
        return f"Vote: {vote} by {self.user.username} on Report #{self.report.id}"
