from rest_framework import serializers
from reports.models import EnvironmentalReport, AIAnalysis, Verification
from users.serializers import UserSerializer

class AIAnalysisSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIAnalysis
        fields = [
            'confidence_score', 'severity_score', 'environmental_risk_index', 
            'recommended_action', 'health_risk_summary', 'analyzed_at'
        ]


class VerificationSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Verification
        fields = ['id', 'user', 'is_valid', 'comments', 'voted_at']


class EnvironmentalReportSerializer(serializers.ModelSerializer):
    reporter = UserSerializer(read_only=True)
    ai_analysis = AIAnalysisSerializer(read_only=True)
    verifications = VerificationSerializer(many=True, read_only=True)
    description = serializers.CharField(write_only=False, required=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = EnvironmentalReport
        fields = [
            'id', 'title', 'description', 'category', 'category_display', 
            'latitude', 'longitude', 'status', 'status_display', 'image', 
            'reporter', 'created_at', 'updated_at', 'ai_analysis', 'verifications'
        ]
        read_only_fields = ['id', 'status', 'reporter', 'created_at', 'updated_at']

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        # Pull decrypted value
        ret['description'] = instance.description
        return ret

    def create(self, validated_data):
        description = validated_data.pop('description', '')
        # Set description which encrypts it
        report = EnvironmentalReport(**validated_data)
        report.description = description
        
        # Save to DB
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            report.reporter = request.user
        
        report.save()
        return report
