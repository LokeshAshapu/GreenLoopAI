import datetime
from django.utils import timezone
from users.models import User, Profile, Achievement
from reports.models import EnvironmentalReport, AIAnalysis, Verification
from missions.models import CleanupMission

def seed():
    print("Starting database seeding...")
    
    # 1. Create Achievements/Badges
    badges = [
        {
            "name": "First Scan",
            "description": "Uploaded your first environmental issue report and analyzed it with NVIDIA NIM VLM.",
            "points_required": 50,
            "badge_icon": "aperture"
        },
        {
            "name": "Eco Advocate",
            "description": "Earned over 150 Eco Points in community action.",
            "points_required": 150,
            "badge_icon": "shield"
        },
        {
            "name": "Trash Buster",
            "description": "Contributed to significant cleanup activities. Earned over 300 Eco Points.",
            "points_required": 300,
            "badge_icon": "zap"
        },
        {
            "name": "Green Loop Commander",
            "description": "Top-tier environmental advocate. Earned over 500 Eco Points.",
            "points_required": 500,
            "badge_icon": "award"
        }
    ]
    
    for b in badges:
        ach, created = Achievement.objects.get_or_create(name=b["name"], defaults=b)
        if created:
            print(f"Created Achievement: {ach.name}")
            
    # 2. Create Default Users (with predefined roles)
    users_data = [
        {"username": "citizen_lisa", "role": User.CITIZEN, "email": "lisa@greenloop.ai", "points": 120},
        {"username": "volunteer_mark", "role": User.VOLUNTEER, "email": "mark@greenloop.ai", "points": 350},
        {"username": "ngo_greenearth", "role": User.NGO, "email": "ngo@greenearth.org", "points": 550},
        {"username": "officer_davis", "role": User.MUNICIPAL_OFFICER, "email": "davis@city.gov", "points": 180},
        {"username": "admin", "role": User.ADMINISTRATOR, "email": "admin@greenloop.ai", "points": 0, "is_superuser": True},
        {"username": "Lokesh", "role": User.CITIZEN, "email": "lokesh@greenloop.ai", "points": 0}
    ]
    
    users = {}
    for ud in users_data:
        # Check if exists
        user = User.objects.filter(username=ud["username"]).first()
        if not user:
            is_super = ud.get("is_superuser", False)
            if is_super:
                user = User.objects.create_superuser(
                    username=ud["username"],
                    email=ud["email"],
                    password="SecurePassword123!"
                )
            else:
                user = User.objects.create_user(
                    username=ud["username"],
                    email=ud["email"],
                    password="SecurePassword123!",
                    role=ud["role"]
                )
            user.eco_points = ud["points"]
            user.is_verified = True
            user.save()
            print(f"Created User: {user.username} ({user.get_role_display()})")
        
        # Profile Setup
        profile, _ = Profile.objects.get_or_create(user=user)
        profile.phone = "+1 (555) 123-0192"
        profile.address = "789 Greenloop Blvd"
        profile.bio = f"Active {user.get_role_display()} coordinating environmental cleanups."
        profile.avatar_url = "/media/avatars/lokesh.png" # Set beautiful generated headshot for everyone
        profile.save()
        
        user.check_and_award_achievements()
        users[ud["username"]] = user

    # 3. Create Sample Environmental Reports
    reports_data = [
        {
            "title": "Severe Plastic Waste Accumulation",
            "description": "Massive pile of water bottles, packaging, and household rubbish dumping site near the community park lake.",
            "category": "plastic_waste",
            "latitude": 40.71280000,
            "longitude": -74.00600000,
            "status": EnvironmentalReport.VERIFIED,
            "reporter": users["citizen_lisa"],
            "image_filename": "reports/plastic_waste.png",
            "ai": {
                "confidence_score": 98.40,
                "severity_score": 8.20,
                "environmental_risk_index": 7.90,
                "recommended_action": "Organize volunteer cleanup, install garbage receptacles, and increase municipal patrols.",
                "health_risk_summary": "Risk of microplastics contamination in soil and water. Attracts minor rodents."
            }
        },
        {
            "title": "Industrial Water Contamination",
            "description": "Strange chemicals and oily foam observed flowing from the storm drain outlet into the local creek.",
            "category": "water_pollution",
            "latitude": 40.73061000,
            "longitude": -73.93524200,
            "status": EnvironmentalReport.VERIFYING,
            "reporter": users["volunteer_mark"],
            "image_filename": "reports/water_pollution.png",
            "ai": {
                "confidence_score": 92.10,
                "severity_score": 9.10,
                "environmental_risk_index": 9.40,
                "recommended_action": "Report to the Environmental Protection Department. Sample water downstream immediately.",
                "health_risk_summary": "High risk of heavy chemical ingestion. Lethal to aquatic life and hazardous to pets/humans."
            }
        },
        {
            "title": "E-Waste Dumped in Canal",
            "description": "Old cathode-ray televisions, computer cases, batteries, and cabling discarded under the bridge.",
            "category": "e_waste",
            "latitude": 40.67817800,
            "longitude": -73.94415800,
            "status": EnvironmentalReport.SUBMITTED,
            "reporter": users["citizen_lisa"],
            "image_filename": "reports/e_waste.png",
            "ai": {
                "confidence_score": 96.80,
                "severity_score": 7.80,
                "environmental_risk_index": 8.50,
                "recommended_action": "Dispatch authorized electronics recycling service. Heavy machinery may be required.",
                "health_risk_summary": "Lead and mercury leakage. Soil erosion and toxic ground runoff risks."
            }
        }
    ]

    for rd in reports_data:
        report = EnvironmentalReport.objects.filter(title=rd["title"]).first()
        image_file = rd.pop("image_filename")
        desc = rd.pop("description")
        ai_info = rd.pop("ai")
        
        if not report:
            report = EnvironmentalReport(**rd)
            report.image = image_file
            report.description = desc
            report.save()
            
            AIAnalysis.objects.create(
                report=report,
                confidence_score=ai_info["confidence_score"],
                severity_score=ai_info["severity_score"],
                environmental_risk_index=ai_info["environmental_risk_index"],
                recommended_action=ai_info["recommended_action"],
                health_risk_summary=ai_info["health_risk_summary"]
            )
            print(f"Created Report & AI Analysis: {report.title}")
            
            # Create a Verification for the verified one
            if report.status == EnvironmentalReport.VERIFIED:
                Verification.objects.create(
                    report=report,
                    user=users["officer_davis"],
                    is_valid=True,
                    comments="Verified on site. High plastic volume needs immediate community mission."
                )
        else:
            # Update image path and description on existing database reports to load correctly
            report.image = image_file
            report.description = desc
            report.save()
            print(f"Updated Image for existing report: {report.title}")

    # 4. Create Sample Cleanup Mission
    mission_title = "Flushing Meadows Canal Garbage Clearance"
    mission = CleanupMission.objects.filter(title=mission_title).first()
    if not mission:
        target_report = EnvironmentalReport.objects.filter(category="plastic_waste").first()
        mission = CleanupMission.objects.create(
            title=mission_title,
            description="Our goal is to clear out all plastic bottles and trash from the creek banks. Trash bags, grabbers, and high-visibility vests will be provided. Please wear protective boots.",
            report=target_report,
            organizer=users["ngo_greenearth"],
            scheduled_time=timezone.now() + datetime.timedelta(days=7),
            status=CleanupMission.PLANNED,
            eco_points_reward=150
        )
        # Add volunteers
        mission.volunteers.add(users["volunteer_mark"])
        mission.volunteers.add(users["citizen_lisa"])
        mission.save()
        print(f"Created Cleanup Mission: {mission.title}")

    print("Database seeding completed successfully!")

if __name__ == '__main__':
    seed()
