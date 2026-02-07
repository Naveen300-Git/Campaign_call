"""
Pydantic schemas for request/response validation.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator

from app.models import CampaignStatus, CallStatus


class BusinessHourSlot(BaseModel):
    """Business hour time slot."""
    day: str = Field(..., description="Day of week (monday, tuesday, etc.)")
    start: str = Field(..., description="Start time in HH:MM format")
    end: str = Field(..., description="End time in HH:MM format")
    
    @validator('day')
    def validate_day(cls, v):
        valid_days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        if v.lower() not in valid_days:
            raise ValueError(f'Day must be one of {valid_days}')
        return v.lower()


class BusinessHoursConfig(BaseModel):
    """Business hours configuration."""
    timezone: str = Field(default="UTC", description="Timezone for business hours (e.g., America/New_York)")
    hours: List[BusinessHourSlot] = Field(..., description="List of business hour slots")


class CallCreate(BaseModel):
    """Schema for creating a call (used internally)."""
    phone_number: str = Field(..., min_length=10, max_length=20, description="Phone number to call")


class CampaignCreate(BaseModel):
    """Schema for creating a campaign."""
    name: str = Field(..., min_length=1, max_length=255, description="Campaign name")
    phone_numbers: List[str] = Field(..., min_items=1, description="List of phone numbers to call")
    max_concurrent_calls: Optional[int] = Field(None, ge=1, le=100, description="Maximum concurrent calls")
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum retry attempts")
    retry_delay_seconds: int = Field(default=300, ge=60, description="Delay between retries in seconds")
    business_hours: Optional[BusinessHoursConfig] = Field(None, description="Business hours configuration")


class CampaignUpdate(BaseModel):
    """Schema for updating a campaign."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    max_concurrent_calls: Optional[int] = Field(None, ge=1, le=100)
    max_retries: Optional[int] = Field(None, ge=0, le=10)
    retry_delay_seconds: Optional[int] = Field(None, ge=60)
    business_hours: Optional[BusinessHoursConfig] = None


class CallResponse(BaseModel):
    """Schema for call response."""
    id: int
    campaign_id: int
    phone_number: str
    status: CallStatus
    retry_count: int
    call_duration_seconds: Optional[float]
    error_message: Optional[str]
    external_call_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    scheduled_at: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class CampaignStatistics(BaseModel):
    """Campaign statistics."""
    total_calls: int
    calls_completed: int
    calls_failed: int
    calls_in_progress: int
    calls_pending: int
    retries_attempted: int
    success_rate: float = Field(description="Success rate as a percentage")
    completion_rate: float = Field(description="Completion rate as a percentage")


class CampaignResponse(BaseModel):
    """Schema for campaign response."""
    id: int
    name: str
    status: CampaignStatus
    max_concurrent_calls: int
    business_hours: Optional[Dict[str, Any]]
    max_retries: int
    retry_delay_seconds: int
    statistics: CampaignStatistics
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class CampaignListResponse(BaseModel):
    """Schema for listing campaigns."""
    campaigns: List[CampaignResponse]
    total: int


class CampaignActionResponse(BaseModel):
    """Schema for campaign action responses (start, pause, etc.)."""
    campaign_id: int
    message: str
    status: CampaignStatus


class CallListResponse(BaseModel):
    """Schema for listing calls."""
    calls: List[CallResponse]
    total: int
