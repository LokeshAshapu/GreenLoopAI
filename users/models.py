from django.db import models
from django.contrib.auth.models import AbstractUser
from security.encryption import encrypt_value, decrypt_value

class User(AbstractUser):
    # User Roles
    CITIZEN = 'citizen'
    VOLUNTEER = 'volunteer'
    NGO = 'ngo'
    MUNICIPAL_OFFICER = 'municipal_officer'
    ADMINISTRATOR = 'administrator'
    
    ROLE_CHOICES = [
        (CITIZEN, 'Citizen'),
        (VOLUNTEER, 'Volunteer'),
        (NGO, 'NGO'),
        (MUNICIPAL_OFFICER, 'Municipal Officer'),
        (ADMINISTRATOR, 'Administrator'),
    ]
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=CITIZEN)
    eco_points = models.IntegerField(default=0)
    is_verified = models.BooleanField(default=False)
    
    def add_eco_points(self, points: int):
        self.eco_points += points
        self.save()
        
    def check_and_award_achievements(self):
        """
        Check eco_points or action history and award badges/achievements.
        """
        achievements = Achievement.objects.filter(points_required__lte=self.eco_points)
        for ach in achievements:
            UserAchievement.objects.get_or_create(user=self, achievement=ach)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(blank=True, max_length=500)
    avatar_url = models.URLField(blank=True, default="https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&q=80&w=150")
    
    # Encrypted fields to comply with cybersecurity requirements
    _phone_encrypted = models.CharField(max_length=255, db_column='phone_encrypted', blank=True)
    _address_encrypted = models.TextField(db_column='address_encrypted', blank=True)

    @property
    def phone(self):
        return decrypt_value(self._phone_encrypted) if self._phone_encrypted else ""

    @phone.setter
    def phone(self, value):
        self._phone_encrypted = encrypt_value(value) if value else ""

    @property
    def address(self):
        return decrypt_value(self._address_encrypted) if self._address_encrypted else ""

    @address.setter
    def address(self, value):
        self._address_encrypted = encrypt_value(value) if value else ""

    def __str__(self):
        return f"Profile of {self.user.username}"


class Achievement(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    points_required = models.IntegerField(default=0)
    badge_icon = models.CharField(max_length=50, default="award") # Icon string (Lucide icon names)

    def __str__(self):
        return self.name


class UserAchievement(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='achievements')
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE)
    awarded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'achievement')

    def __str__(self):
        return f"{self.user.username} earned {self.achievement.name}"


class AuditLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=255)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    status = models.IntegerField()
    description = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        user_str = self.user.username if self.user else "Anonymous"
        return f"[{self.timestamp.isoformat()}] {user_str} - {self.action} ({self.status})"
