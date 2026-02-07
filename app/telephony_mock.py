"""
Mock telephony service for simulating outbound calls.
In production, replace with real telephony provider (Twilio, Plivo, etc.)
"""
import random
import asyncio
import uuid
from typing import Tuple
from datetime import datetime, timezone

from app.config import settings


class TelephonyMockService:
    """Mock service to simulate telephony operations."""
    
    def __init__(self):
        self.min_duration = settings.mock_call_duration_min
        self.max_duration = settings.mock_call_duration_max
        self.failure_rate = settings.mock_call_failure_rate
    
    async def initiate_call(self, phone_number: str) -> Tuple[str, bool, float, str]:
        """
        Initiate a mock outbound call.
        
        Args:
            phone_number: The phone number to call
            
        Returns:
            Tuple of (external_call_id, success, duration, error_message)
        """
        # Generate a unique call ID
        external_call_id = f"CALL-{uuid.uuid4().hex[:12].upper()}"
        
        # Simulate call duration (5-30 seconds by default)
        duration = random.uniform(self.min_duration, self.max_duration)
        
        # Simulate the call (sleep for duration)
        await asyncio.sleep(duration)
        
        # Randomly determine if call succeeds or fails
        success = random.random() > self.failure_rate
        
        error_message = None
        if not success:
            # Simulate different failure reasons
            errors = [
                "No answer",
                "Busy",
                "Invalid number",
                "Network error",
                "Call rejected",
                "Timeout"
            ]
            error_message = random.choice(errors)
        
        return external_call_id, success, duration, error_message
    
    async def check_call_status(self, external_call_id: str) -> dict:
        """
        Check the status of a call (mock implementation).
        
        Args:
            external_call_id: The external call ID
            
        Returns:
            Dictionary with call status information
        """
        # In a real implementation, this would query the telephony provider
        return {
            "external_call_id": external_call_id,
            "status": "completed",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# Singleton instance
telephony_service = TelephonyMockService()
