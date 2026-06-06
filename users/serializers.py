from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from users.models import User, Profile, Achievement, UserAchievement

class AchievementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Achievement
        fields = ['id', 'name', 'description', 'points_required', 'badge_icon']


class UserAchievementSerializer(serializers.ModelSerializer):
    achievement = AchievementSerializer(read_only=True)
    
    class Meta:
        model = UserAchievement
        fields = ['id', 'achievement', 'awarded_at']


class ProfileSerializer(serializers.ModelSerializer):
    phone = serializers.CharField(write_only=False, required=False, allow_blank=True)
    address = serializers.CharField(write_only=False, required=False, allow_blank=True)
    
    class Meta:
        model = Profile
        fields = ['bio', 'avatar_url', 'phone', 'address']

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        # Call property getters which decrypt values
        ret['phone'] = instance.phone
        ret['address'] = instance.address
        return ret

    def update(self, instance, validated_data):
        # Handle setting properties which encrypt values
        if 'phone' in validated_data:
            instance.phone = validated_data.pop('phone')
        if 'address' in validated_data:
            instance.address = validated_data.pop('address')
        return super().update(instance, validated_data)


class UserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(required=False)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    achievements = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role', 'role_display', 'eco_points', 'is_verified', 'profile', 'achievements']
        read_only_fields = ['id', 'eco_points', 'is_verified']

    def get_achievements(self, obj):
        user_achievements = UserAchievement.objects.filter(user=obj)
        return UserAchievementSerializer(user_achievements, many=True).data


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    role = serializers.ChoiceField(choices=User.ROLE_CHOICES, default=User.CITIZEN)
    phone = serializers.CharField(write_only=True, required=False, allow_blank=True)
    address = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'role', 'phone', 'address']

    def create(self, validated_data):
        phone = validated_data.pop('phone', '')
        address = validated_data.pop('address', '')
        
        # User password hashing will be handled automatically by create_user (via settings hashers)
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
            role=validated_data.get('role', User.CITIZEN)
        )
        
        # Create profile and assign encrypted phone/address
        profile = Profile.objects.create(user=user)
        if phone:
            profile.phone = phone
        if address:
            profile.address = address
        profile.save()
        
        return user
