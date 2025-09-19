from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
import requests

app = FastAPI(title="ServEase Scheduling API")

# -----------------------------
# Input Data Models
# -----------------------------
class Customer(BaseModel):
    full_name: str
    phone: str
    email: str
    address_text: str
    pincode: str
    preferred_time_slots: List[dict]

class Job(BaseModel):
    request_type: str  # "service" or "installation"
    appliance_type: str
    model_if_known: Optional[str]
    fault_symptoms: Optional[List[str]] = []
    installation_details: Optional[List[str]] = []
    urgency: Optional[str] = "normal"

# -----------------------------
# Mock Data: 6 Technicians, 3 Regions
# -----------------------------
technicians_data = {
    "technicians": [
        {"id":"tech_01","name":"Asha K","skills":["wm_vibration","ac_leak"],"appliances_supported":["WashingMachine","AC"],"regions":["South","Central"],"availability_slots":[{"start":"2025-09-20T10:00:00+05:30","end":"2025-09-20T12:00:00+05:30"}]},
        {"id":"tech_02","name":"Ravi S","skills":["fridge_cooling","tv_display"],"appliances_supported":["Refrigerator","TV"],"regions":["North","Central"],"availability_slots":[{"start":"2025-09-21T09:00:00+05:30","end":"2025-09-21T11:00:00+05:30"}]},
        {"id":"tech_03","name":"Priya M","skills":["ac_airflow","waterpurifier_filter"],"appliances_supported":["AC","WaterPurifier"],"regions":["South","West"],"availability_slots":[{"start":"2025-09-22T10:30:00+05:30","end":"2025-09-22T12:30:00+05:30"}]},
        {"id":"tech_04","name":"Vikram P","skills":["ac_leak","wm_drum"],"appliances_supported":["AC","WashingMachine"],"regions":["East","North"],"availability_slots":[{"start":"2025-09-23T11:00:00+05:30","end":"2025-09-23T13:00:00+05:30"}]},
        {"id":"tech_05","name":"Nisha T","skills":["tv_display","fridge_cooling"],"appliances_supported":["TV","Refrigerator"],"regions":["South","West"],"availability_slots":[{"start":"2025-09-24T14:00:00+05:30","end":"2025-09-24T16:00:00+05:30"}]},
        {"id":"tech_06","name":"Rohit K","skills":["waterpurifier_filter","wm_vibration"],"appliances_supported":["WaterPurifier","WashingMachine"],"regions":["Central","North"],"availability_slots":[{"start":"2025-09-25T10:00:00+05:30","end":"2025-09-25T12:00:00+05:30"}]}
    ],
    "regions":[
        {"pincode_prefix":"5600xx","region_label":"Bengaluru Urban"},
        {"pincode_prefix":"4000xx","region_label":"Mumbai Suburban"},
        {"pincode_prefix":"1100xx","region_label":"Delhi"}
    ]
}

# -----------------------------
# Appointment Endpoint
# -----------------------------
@app.post("/create_appointment")
def create_appointment(customer: Customer, job: Job):
    
    # Lookup region using Zippopotam API
    try:
        response = requests.get(f"https://api.zippopotam.us/IN/{customer.pincode}", timeout=2)
        data = response.json()
        region_label = data['places'][0]['state']
    except:
        # Fallback to mock regions
        region_label = "Unknown Region"
        for r in technicians_data['regions']:
            if customer.pincode.startswith(r['pincode_prefix'][:3]):
                region_label = r['region_label']
                break
    
    # Find a technician matching appliance and region
    matched_tech = None
    for tech in technicians_data['technicians']:
        if job.appliance_type in tech['appliances_supported'] and region_label in tech['regions']:
            matched_tech = tech
            break
    
    # Prepare appointment details
    appointment = {
        "customer_name": customer.full_name,
        "pincode": customer.pincode,
        "region_label": region_label,
        "appliance_type": job.appliance_type,
        "technician_id": matched_tech['id'] if matched_tech else None,
        "technician_name": matched_tech['name'] if matched_tech else None,
        "status": "confirmed" if matched_tech else "pending",
        "slot_start": matched_tech['availability_slots'][0]['start'] if matched_tech else None,
        "slot_end": matched_tech['availability_slots'][0]['end'] if matched_tech else None
    }
    
    return {"appointment": appointment}
