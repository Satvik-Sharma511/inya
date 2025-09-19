from flask import Flask, request, jsonify
import requests
from datetime import datetime, timedelta

app = Flask(__name__)

# Mock data for technicians
technicians = [
    {
        "id": "tech_01",
        "name": "Asha K",
        "skills": ["wm_vibration", "ac_leak"],
        "appliances_supported": ["WashingMachine", "AC"],
        "regions": ["South", "Central"],
        "availability_slots": [
            {"start": "2025-09-20T10:00:00+05:30", "end": "2025-09-20T12:00:00+05:30"},
            {"start": "2025-09-20T15:00:00+05:30", "end": "2025-09-20T16:00:00+05:30"}
        ]
    },
    {
        "id": "tech_02",
        "name": "Ravi S",
        "skills": ["fridge_cooling", "tv_display"],
        "appliances_supported": ["Refrigerator", "TV"],
        "regions": ["North", "Central"],
        "availability_slots": [
            {"start": "2025-09-21T09:00:00+05:30", "end": "2025-09-21T11:00:00+05:30"},
            {"start": "2025-09-21T14:00:00+05:30", "end": "2025-09-21T16:00:00+05:30"}
        ]
    },
    {
        "id": "tech_03",
        "name": "Priya M",
        "skills": ["ac_airflow", "waterpurifier_filter"],
        "appliances_supported": ["AC", "WaterPurifier"],
        "regions": ["South", "West"],
        "availability_slots": [
            {"start": "2025-09-22T10:30:00+05:30", "end": "2025-09-22T12:30:00+05:30"},
            {"start": "2025-09-22T15:30:00+05:30", "end": "2025-09-22T17:00:00+05:30"}
        ]
    },
    {
        "id": "tech_04",
        "name": "Arjun P",
        "skills": ["wm_drainage", "ac_noise"],
        "appliances_supported": ["WashingMachine", "AC"],
        "regions": ["West", "North"],
        "availability_slots": [
            {"start": "2025-09-20T11:00:00+05:30", "end": "2025-09-20T13:00:00+05:30"}
        ]
    },
    {
        "id": "tech_05",
        "name": "Sneha R",
        "skills": ["fridge_frost", "tv_remote"],
        "appliances_supported": ["Refrigerator", "TV"],
        "regions": ["South", "Central"],
        "availability_slots": [
            {"start": "2025-09-21T10:00:00+05:30", "end": "2025-09-21T12:00:00+05:30"}
        ]
    },
    {
        "id": "tech_06",
        "name": "Vikram T",
        "skills": ["waterpurifier_filter", "ac_cooling"],
        "appliances_supported": ["WaterPurifier", "AC"],
        "regions": ["North", "West"],
        "availability_slots": [
            {"start": "2025-09-22T09:00:00+05:30", "end": "2025-09-22T11:00:00+05:30"}
        ]
    }
]

# Region mapping
regions = [
    {"pincode_prefix": "5600xx", "region_label": "Bengaluru Urban"},
    {"pincode_prefix": "4000xx", "region_label": "Mumbai Suburban"},
    {"pincode_prefix": "1100xx", "region_label": "Delhi"}
]

sample_appointments = []

# Helper: Get region from pincode using Zippopotam API
def get_region_label(pincode):
    try:
        response = requests.get(f"https://api.zippopotam.us/IN/{pincode}", timeout=3)
        data = response.json()
        # Pick first place's state as region_label
        return data['places'][0]['state']
    except:
        # fallback to cached region mapping
        for r in regions:
            if pincode.startswith(r['pincode_prefix'][:4]):
                return r['region_label']
        return "Unknown"

# Helper: Find available technician
def find_technician(appliance, required_skill, region):
    available_techs = []
    for tech in technicians:
        if appliance in tech['appliances_supported'] and required_skill in tech['skills'] and region in tech['regions']:
            available_techs.append(tech)
    return available_techs

@app.route('/create_appointment', methods=['POST'])
def create_appointment():
    data = request.json

    # Customer entities
    full_name = data.get("full_name")
    phone = data.get("phone")
    email = data.get("email")
    address_text = data.get("address_text")
    pincode = data.get("pincode")
    preferred_time_slots = data.get("preferred_time_slots", [])
    
    # Job context
    request_type = data.get("request_type")
    appliance_type = data.get("appliance_type")
    model_if_known = data.get("model_if_known", "")
    fault_symptoms = data.get("fault_symptoms", [])
    installation_details = data.get("installation_details", [])
    urgency = data.get("urgency", "normal")
    
    # Map pincode to region_label
    region_label = get_region_label(pincode)
    
    # Determine required skill for fault (simplified: take first symptom)
    required_skill = fault_symptoms[0] if fault_symptoms else appliance_type.lower()
    
    # Find technician
    available_techs = find_technician(appliance_type, required_skill, region_label)
    
    if not available_techs:
        return jsonify({"error": "No technician available for this appliance/region/skill"}), 404
    
    tech = available_techs[0]
    
    # Pick first overlapping slot with customer preference
    slot_start, slot_end = None, None
    for pref_slot in preferred_time_slots:
        pref_start = datetime.fromisoformat(pref_slot['start'])
        pref_end = datetime.fromisoformat(pref_slot['end'])
        for tech_slot in tech['availability_slots']:
            tech_start = datetime.fromisoformat(tech_slot['start'])
            tech_end = datetime.fromisoformat(tech_slot['end'])
            latest_start = max(pref_start, tech_start)
            earliest_end = min(pref_end, tech_end)
            if latest_start < earliest_end:
                slot_start = latest_start.isoformat()
                slot_end = earliest_end.isoformat()
                break
        if slot_start:
            break
    if not slot_start:
        # fallback to first tech slot
        slot_start = tech['availability_slots'][0]['start']
        slot_end = tech['availability_slots'][0]['end']
    
    appointment = {
        "customer_name": full_name,
        "phone": phone,
        "email": email,
        "address_text": address_text,
        "request_type": request_type,
        "appliance_type": appliance_type,
        "model_if_known": model_if_known,
        "fault_symptoms": fault_symptoms,
        "installation_details": installation_details,
        "urgency": urgency,
        "region_label": region_label,
        "technician_id": tech['id'],
        "slot_start": slot_start,
        "slot_end": slot_end,
        "status": "confirmed"
    }
    
    sample_appointments.append(appointment)
    
    return jsonify({
        "message": "Appointment confirmed",
        "appointment": appointment
    })

if __name__ == "__main__":
    app.run(debug=True)
