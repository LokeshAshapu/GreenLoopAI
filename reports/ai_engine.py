import os
import base64
import requests
import json
import random
from django.conf import settings

def encode_image(image_path_or_file):
    """
    Encodes a file-like image or file path to a base64 string.
    """
    if isinstance(image_path_or_file, str):
        with open(image_path_or_file, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    else:
        # It's an UploadedFile object
        image_path_or_file.seek(0)
        return base64.b64encode(image_path_or_file.read()).decode('utf-8')

def analyze_environmental_image(image_file, category: str) -> dict:
    """
    Analyzes an environmental issue image using NVIDIA API (NIMs) or a local mock fallback.
    Returns a dictionary of analysis details.
    """
    if getattr(settings, 'NVIDIA_MOCK_MODE', True) or not getattr(settings, 'NVIDIA_API_KEY', None):
        return get_mock_analysis(category)
        
    try:
        base64_image = encode_image(image_file)
        api_key = settings.NVIDIA_API_KEY
        if api_key:
            api_key = api_key.strip().strip("'").strip('"')
        api_url = settings.NVIDIA_API_URL
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # System prompt instructs NVIDIA NIM VLM to classify and return details in JSON
        payload = {
            "model": "nvidia/neva-22b", # Standard NVIDIA NIM Multimodal model or similar
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Analyze this environmental hazard image. Identify issues matching the category: "
                                f"{category}. Return a JSON object with the exact keys: "
                                "'confidence_score' (number 0-100), 'severity_score' (number 1-10), "
                                "'environmental_risk_index' (number 1-10), 'recommended_action' (string), "
                                "and 'health_risk_summary' (string). Do not include any explanation or markdown formatting."
                            )
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 512,
            "temperature": 0.2
        }
        
        response = requests.post(api_url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        response_json = response.json()
        content = response_json['choices'][0]['message']['content'].strip()
        
        # Parse output JSON
        # NVIDIA NIMs might return markdown block formatting, let's strip it if present
        if content.startswith("```json"):
            content = content.split("```json")[1].split("```")[0].strip()
        elif content.startswith("```"):
            content = content.split("```")[1].split("```")[0].strip()
            
        data = json.loads(content)
        return {
            "confidence_score": float(data.get("confidence_score", 90.0)),
            "severity_score": float(data.get("severity_score", 5.0)),
            "environmental_risk_index": float(data.get("environmental_risk_index", 5.0)),
            "recommended_action": str(data.get("recommended_action", "Alert municipal authorities immediately.")),
            "health_risk_summary": str(data.get("health_risk_summary", "Potential respiratory and ecological hazard.")),
            "raw_response": response_json
        }
        
    except Exception as e:
        # Fallback to mock on remote network errors or parsing errors to ensure system robustness
        mock_data = get_mock_analysis(category)
        mock_data["error_details"] = str(e)
        mock_data["mock_fallback_active"] = True
        return mock_data


def get_mock_analysis(category: str) -> dict:
    """
    Returns realistic mocked NIM model classification details based on the environmental category.
    """
    # Create deterministic/realistic randomness
    conf = round(random.uniform(82.5, 99.4), 2)
    
    analysis_templates = {
        'plastic_waste': {
            'severity': round(random.uniform(4.0, 7.5), 2),
            'risk_index': round(random.uniform(3.5, 6.8), 2),
            'recommended_action': "Organize volunteer collection mission, separate recyclables, and install signage prohibiting littering.",
            'health_risk_summary': "Microplastic leakage risk. Local fauna ingestion hazard and long-term soil toxicity hazard."
        },
        'e_waste': {
            'severity': round(random.uniform(7.0, 9.5), 2),
            'risk_index': round(random.uniform(8.0, 9.8), 2),
            'recommended_action': "Dispatch professional hazardous materials disposal unit immediately. Do not handle raw metals directly.",
            'health_risk_summary': "High risk of heavy metal poisoning (lead, mercury, cadmium) leaching into groundwater. Toxic to dermal contact."
        },
        'water_pollution': {
            'severity': round(random.uniform(6.5, 9.8), 2),
            'risk_index': round(random.uniform(7.0, 9.6), 2),
            'recommended_action': "Notify local environmental protection agency. Block downstream public use and commence water sampling.",
            'health_risk_summary': "Immediate danger of waterborne pathogens, chemical poisoning, or heavy organic contamination. Lethal if consumed."
        },
        'open_burning': {
            'severity': round(random.uniform(5.5, 8.8), 2),
            'risk_index': round(random.uniform(6.0, 9.0), 2),
            'recommended_action': "Contact local fire department or municipal air quality control. Secure area to prevent wildfire spread.",
            'health_risk_summary': "Direct emission of particulate matter (PM2.5), carbon monoxide, and dioxins. Severe respiratory hazard to nearby residents."
        },
        'illegal_dumping': {
            'severity': round(random.uniform(4.5, 8.0), 2),
            'risk_index': round(random.uniform(5.0, 7.8), 2),
            'recommended_action': "Request municipality trash clearing services. Set up surveillance or camera monitoring to deter future offenses.",
            'health_risk_summary': "Attracts disease-carrying vectors (rodents, mosquitoes). Risk of sharp object lacerations and environmental degradation."
        },
        'deforestation': {
            'severity': round(random.uniform(8.0, 10.0), 2),
            'risk_index': round(random.uniform(8.5, 10.0), 2),
            'recommended_action': "Inquire about land permits. Report to Forestry commission. Initiate reforestation and soil stabilization measures.",
            'health_risk_summary': "Loss of biodiversity, topsoil erosion leading to landslides, and reduction in local oxygen/carbon sequestration capacity."
        }
    }
    
    tmpl = analysis_templates.get(category, {
        'severity': 5.0,
        'risk_index': 5.0,
        'recommended_action': "Inspect area and alert local authorities.",
        'health_risk_summary': "General environmental and sanitation degradation risk."
    })
    
    return {
        "confidence_score": conf,
        "severity_score": tmpl['severity'],
        "environmental_risk_index": tmpl['risk_index'],
        "recommended_action": tmpl['recommended_action'],
        "health_risk_summary": tmpl['health_risk_summary'],
        "raw_response": {"mock": True, "info": "Local simulation engine response"}
    }
