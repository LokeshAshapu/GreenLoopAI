from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from reports.models import EnvironmentalReport, AIAnalysis, Verification
from reports.ai_engine import get_mock_analysis

class ReportsTestCase(TestCase):
    
    def setUp(self):
        self.User = get_user_model()
        self.reporter = self.User.objects.create_user(
            username="testreporter",
            password="SecurePassword123!",
            role="citizen"
        )
        
        # Create a dummy image file
        self.dummy_image = SimpleUploadedFile(
            name="test_pollution.jpg",
            content=b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00\x08\x06\x06",
            content_type="image/jpeg"
        )

    def test_report_creation_and_fields(self):
        """
        Verify that a report can be created with encrypted description.
        """
        report = EnvironmentalReport.objects.create(
            title="Plastic Dumping Site",
            category="plastic_waste",
            latitude=40.71280000,
            longitude=-74.00600000,
            image=self.dummy_image,
            reporter=self.reporter
        )
        report.description = "Near the north corner of Central Park."
        report.save()

        # Check DB model and description property encryption
        self.assertEqual(report.title, "Plastic Dumping Site")
        self.assertEqual(report.description, "Near the north corner of Central Park.")
        self.assertNotEqual(report._description_encrypted, "Near the north corner of Central Park.")
        self.assertEqual(report.status, "submitted")

    def test_ai_mock_classifier_engine(self):
        """
        Verify that local mockup engine produces correct risk ratings and severity indexes.
        """
        e_waste_results = get_mock_analysis("e_waste")
        self.assertIn("confidence_score", e_waste_results)
        self.assertTrue(80.0 <= e_waste_results["confidence_score"] <= 100.0)
        self.assertTrue(7.0 <= e_waste_results["severity_score"] <= 10.0) # High severity for e-waste
        self.assertIn("heavy metal", e_waste_results["health_risk_summary"].lower())

    def test_geojson_api_format(self):
        """
        Verify that GeoJSON endpoint formats data properly for Leaflet integration.
        """
        # Create report
        report = EnvironmentalReport.objects.create(
            title="River Foam Pollution",
            category="water_pollution",
            latitude=35.68950000,
            longitude=139.69170000,
            image=self.dummy_image,
            reporter=self.reporter
        )
        report.description = "Foam visible since morning."
        report.save()

        # Add AI analysis mock details
        AIAnalysis.objects.create(
            report=report,
            confidence_score=94.50,
            severity_score=8.50,
            environmental_risk_index=9.00,
            recommended_action="Notify environmental agents",
            health_risk_summary="High toxic pathogens"
        )

        c = Client()
        c.force_login(self.reporter)
        response = c.get('/api/reports/geojson/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Verify GeoJSON specifications
        self.assertEqual(data["type"], "FeatureCollection")
        self.assertTrue(len(data["features"]) > 0)
        
        feature = data["features"][0]
        self.assertEqual(feature["geometry"]["type"], "Point")
        self.assertEqual(feature["geometry"]["coordinates"], [139.69170000, 35.68950000])
        self.assertEqual(feature["properties"]["title"], "River Foam Pollution")
        self.assertEqual(feature["properties"]["severity"], 8.5)
