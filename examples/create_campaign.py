"""
Example script to create a campaign using the API.
"""
import requests
import json

API_BASE_URL = "http://localhost:8000"


def create_campaign_example():
    """Create a campaign with business hours."""
    
    # Campaign data
    campaign_data = {
        "name": "Mumbai Sales Outreach - Q1 2026",
        "phone_numbers": [
            "+919876543210",
            "+919876543211",
            "+919876543212",
            "+919876543213",
            "+919876543214",
            "+919876543215",
            "+919876543216",
            "+919876543217",
            "+919876543218",
            "+919876543219"
        ],
        "max_concurrent_calls": 5,
        "max_retries": 3,
        "retry_delay_seconds": 300,
        "business_hours": {
            "timezone": "Asia/Kolkata",
            "hours": [
                {"day": "monday", "start": "10:00", "end": "18:00"},
                {"day": "tuesday", "start": "10:00", "end": "18:00"},
                {"day": "wednesday", "start": "10:00", "end": "18:00"},
                {"day": "thursday", "start": "10:00", "end": "18:00"},
                {"day": "friday", "start": "10:00", "end": "18:00"}
            ]
        }
    }
    
    # Create campaign
    response = requests.post(
        f"{API_BASE_URL}/campaigns",
        json=campaign_data
    )
    
    if response.status_code == 201:
        campaign = response.json()
        print("Campaign created successfully!")
        print(json.dumps(campaign, indent=2))
        return campaign["id"]
    else:
        print(f"Error creating campaign: {response.status_code}")
        print(response.json())
        return None


def create_simple_campaign():
    """Create a simple campaign without business hours."""
    
    campaign_data = {
        "name": "Bangalore Customer Follow-up Campaign",
        "phone_numbers": [
            "+918012345671",
            "+918012345672",
            "+918012345673",
            "+918012345674",
            "+918012345675"
        ],
        "max_concurrent_calls": 3,
        "max_retries": 2,
        "retry_delay_seconds": 180
    }
    
    response = requests.post(
        f"{API_BASE_URL}/campaigns",
        json=campaign_data
    )
    
    if response.status_code == 201:
        campaign = response.json()
        print("Simple campaign created successfully!")
        print(json.dumps(campaign, indent=2))
        return campaign["id"]
    else:
        print(f"Error creating campaign: {response.status_code}")
        print(response.json())
        return None


def start_campaign(campaign_id: int):
    """Start a campaign."""
    
    response = requests.post(f"{API_BASE_URL}/campaigns/{campaign_id}/start")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Campaign {campaign_id} started!")
        print(json.dumps(result, indent=2))
    else:
        print(f"Error starting campaign: {response.status_code}")
        print(response.json())


def get_campaign_status(campaign_id: int):
    """Get campaign status."""
    
    response = requests.get(f"{API_BASE_URL}/campaigns/{campaign_id}")
    
    if response.status_code == 200:
        campaign = response.json()
        print(f"Campaign {campaign_id} status:")
        print(json.dumps(campaign, indent=2))
    else:
        print(f"Error getting campaign: {response.status_code}")
        print(response.json())


if __name__ == "__main__":
    print("=" * 80)
    print("Creating campaigns...")
    print("=" * 80)
    
    # Create a campaign with business hours
    print("\n1. Creating campaign with business hours...")
    campaign_id = create_campaign_example()
    
    if campaign_id:
        print(f"\n2. Starting campaign {campaign_id}...")
        start_campaign(campaign_id)
        
        print(f"\n3. Getting campaign status...")
        get_campaign_status(campaign_id)
    
    # Create a simple campaign
    print("\n" + "=" * 80)
    print("\n4. Creating simple campaign...")
    simple_campaign_id = create_simple_campaign()
    
    if simple_campaign_id:
        print(f"\n5. Starting simple campaign {simple_campaign_id}...")
        start_campaign(simple_campaign_id)
