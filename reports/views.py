from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseRedirect
from django.urls import reverse
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser

from reports.models import EnvironmentalReport, AIAnalysis, Verification
from reports.serializers import EnvironmentalReportSerializer, VerificationSerializer
from reports.ai_engine import analyze_environmental_image
from users.models import User

# --- REST API Endpoints ---

class APIReportListCreateView(generics.ListCreateAPIView):
    serializer_class = EnvironmentalReportSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        return EnvironmentalReport.objects.all().order_by('-created_at')

    def perform_create(self, serializer):
        report = serializer.save(reporter=self.request.user)
        
        # Trigger immediate AI vision analysis
        ai_data = analyze_environmental_image(report.image, report.category)
        
        # Save analysis
        AIAnalysis.objects.create(
            report=report,
            confidence_score=ai_data['confidence_score'],
            severity_score=ai_data['severity_score'],
            environmental_risk_index=ai_data['environmental_risk_index'],
            recommended_action=ai_data['recommended_action'],
            health_risk_summary=ai_data['health_risk_summary'],
            raw_response=ai_data.get('raw_response')
        )
        
        # Award eco-points for submission
        user = self.request.user
        user.add_eco_points(50)
        user.check_and_award_achievements()


class APIReportVerificationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, report_id):
        report = get_object_or_404(EnvironmentalReport, id=report_id)
        is_valid = request.data.get('is_valid', True)
        comments = request.data.get('comments', '')

        # Check if user already verified
        existing = Verification.objects.filter(report=report, user=request.user).first()
        if existing:
            return Response({"error": "You have already voted on this report."}, status=status.HTTP_400_BAD_REQUEST)

        # Create vote
        verification = Verification.objects.create(
            report=report,
            user=request.user,
            is_valid=is_valid,
            comments=comments
        )

        # Apply verification rules:
        # If user is NGO or Municipal Officer, 1 positive vote immediately verifies
        # If user is Citizen/Volunteer, 3 positive votes verify
        role = request.user.role
        
        # Fetch positive votes count
        positive_votes = Verification.objects.filter(report=report, is_valid=True).count()
        
        if (role in [User.NGO, User.MUNICIPAL_OFFICER] and is_valid) or (positive_votes >= 3):
            report.status = EnvironmentalReport.VERIFIED
            report.save()
            
        # Award Eco Points for verifying
        request.user.add_eco_points(10)
        request.user.check_and_award_achievements()

        return Response({
            "message": "Verification submitted successfully",
            "report_status": report.status,
            "verification": VerificationSerializer(verification).data
        })


class APIReportGeoJsonListView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        """
        Returns reports formatted as standard GeoJSON for Leaflet loading.
        """
        reports = EnvironmentalReport.objects.all()
        features = []
        for r in reports:
            # Check if AI Analysis details exist
            has_ai = hasattr(r, 'ai_analysis')
            severity = float(r.ai_analysis.severity_score) if has_ai else 0.0
            
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(r.longitude), float(r.latitude)]
                },
                "properties": {
                    "id": r.id,
                    "title": r.title,
                    "category": r.category,
                    "category_display": r.get_category_display(),
                    "status": r.status,
                    "status_display": r.get_status_display(),
                    "severity": severity,
                    "image_url": r.image.url if r.image else "",
                    "description": r.description
                }
            })
            
        geojson = {
            "type": "FeatureCollection",
            "features": features
        }
        return JsonResponse(geojson)


# --- HTML Template / UI endpoints ---

@login_required
def report_issue_view(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        category = request.POST.get('category')
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')
        image = request.FILES.get('image')

        if not (title and category and latitude and longitude and image):
            messages.error(request, "All fields (including location and image) are required.")
            if request.headers.get('HX-Request'):
                return render(request, 'partials/messages.html')
            return redirect('dashboard')

        try:
            # Create report
            report = EnvironmentalReport(
                title=title,
                category=category,
                latitude=latitude,
                longitude=longitude,
                image=image,
                reporter=request.user
            )
            report.description = description
            report.save()

            # Trigger AI analysis
            ai_data = analyze_environmental_image(report.image, report.category)
            AIAnalysis.objects.create(
                report=report,
                confidence_score=ai_data['confidence_score'],
                severity_score=ai_data['severity_score'],
                environmental_risk_index=ai_data['environmental_risk_index'],
                recommended_action=ai_data['recommended_action'],
                health_risk_summary=ai_data['health_risk_summary'],
                raw_response=ai_data.get('raw_response')
            )

            # Award Eco Points
            request.user.add_eco_points(50)
            request.user.check_and_award_achievements()

            messages.success(request, f"Issue successfully reported! You earned 50 Eco Points. AI scanned confidence: {ai_data['confidence_score']}%")
            
            if request.headers.get('HX-Request'):
                response = HttpResponseRedirect(reverse('scanner_detail', kwargs={'report_id': report.id}))
                response['HX-Redirect'] = reverse('scanner_detail', kwargs={'report_id': report.id})
                return response
            return redirect('scanner_detail', report_id=report.id)

        except Exception as e:
            messages.error(request, f"Failed to submit issue: {e}")
            if request.headers.get('HX-Request'):
                return render(request, 'partials/messages.html')
            return redirect('dashboard')

    return redirect('dashboard')


@login_required
def verify_issue_htmx(request, report_id):
    """
    HTMX-only endpoint for reporting issue verification votes from map/dashboard cards.
    """
    if request.method == 'POST':
        report = get_object_or_404(EnvironmentalReport, id=report_id)
        
        # Check if already voted
        if Verification.objects.filter(report=report, user=request.user).exists():
            return render(request, 'partials/verification_status.html', {
                'report': report,
                'voted_already': True,
                'message': "Already verified."
            })
            
        is_valid = request.POST.get('is_valid', 'true') == 'true'
        comments = request.POST.get('comments', 'Verified via web portal')
        
        # Record vote
        Verification.objects.create(
            report=report,
            user=request.user,
            is_valid=is_valid,
            comments=comments
        )
        
        # Update report status
        positive_votes = Verification.objects.filter(report=report, is_valid=True).count()
        role = request.user.role
        
        if (role in [User.NGO, User.MUNICIPAL_OFFICER] and is_valid) or (positive_votes >= 3):
            report.status = EnvironmentalReport.VERIFIED
            report.save()
            
        request.user.add_eco_points(10)
        request.user.check_and_award_achievements()
        
        return render(request, 'partials/verification_status.html', {
            'report': report,
            'success': True,
            'points_awarded': 10
        })
    return render(request, 'partials/verification_status.html', {'error': "Invalid Request"})


@login_required
def chatbot_view(request):
    """
    Renders the interactive GreenBot AI chatbot interface.
    """
    return render(request, 'chatbot.html')


@login_required
def chatbot_api_view(request):
    """
    API endpoint that receives chat queries and integrates with NVIDIA NIM API to return responses.
    """
    import json
    import requests
    from django.conf import settings

    if request.method == 'POST':
        try:
            body = json.loads(request.body)
            user_msg = body.get('message', '')
            if not user_msg:
                return JsonResponse({"reply": "No query provided. What environmental question can I answer for you?"}, status=400)

            api_key = getattr(settings, 'NVIDIA_API_KEY', None)
            api_url = getattr(settings, 'NVIDIA_API_URL', 'https://integrate.api.nvidia.com/v1/chat/completions')
            mock_mode = getattr(settings, 'NVIDIA_MOCK_MODE', False)

            if api_key:
                api_key = api_key.strip().strip("'").strip('"')

            if mock_mode or not api_key:
                # Fallback mock replies
                return JsonResponse({
                    "reply": f"Hello! (Mock Mode) I received your query: '{user_msg}'. Please activate your NVIDIA API key in settings to enable live chats."
                })

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": "meta/llama-3.1-8b-instruct",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are GreenBot, the dedicated AI assistant for GreenLoop AI. "
                            "GreenLoop AI is a decentralized environmental platform where citizens upload scans of hazards "
                            "(plastic waste, e-waste, water pollution, illegal dumps, deforestation), "
                            "municipal officers verify coordinates, and volunteers coordinate cleanup missions to earn Eco Points. "
                            "Help the user with environmental queries, cleanup guidance, waste recycling advice, and platform details. "
                            "Keep answers concise, helpful, and formatted in Markdown."
                        )
                    },
                    {
                        "role": "user",
                        "content": user_msg
                    }
                ],
                "temperature": 0.5,
                "max_tokens": 1024
            }

            response = requests.post(api_url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()

            response_json = response.json()
            reply = response_json['choices'][0]['message']['content'].strip()
            return JsonResponse({"reply": reply})

        except Exception as e:
            return JsonResponse({
                "reply": f"GreenBot is having trouble connecting to the network right now. Details: {e}"
            }, status=500)

    return JsonResponse({"error": "Method not allowed"}, status=405)

