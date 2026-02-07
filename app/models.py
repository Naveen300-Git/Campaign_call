"""
Database models for campaigns and calls.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum

from app.database import Base


class CampaignStatus(str, enum.Enum):
    """Campaign status enumeration."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class CallStatus(str, enum.Enum):
    """Call status enumeration."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SCHEDULED = "scheduled"


class Campaign(Base):
    """Campaign model representing an outbound call campaign."""
    __tablename__ = "campaigns"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    status = Column(SQLEnum(CampaignStatus), default=CampaignStatus.PENDING, nullable=False)
    
    # Concurrency control
    max_concurrent_calls = Column(Integer, default=10, nullable=False)
    
    # Business hours configuration (stored as JSON)
    # Format: {"timezone": "America/New_York", "hours": [{"day": "monday", "start": "09:00", "end": "17:00"}]}
    business_hours = Column(JSON, nullable=True)
    
    # Retry configuration
    max_retries = Column(Integer, default=3, nullable=False)
    retry_delay_seconds = Column(Integer, default=300, nullable=False)  # 5 minutes default
    
    # Statistics
    total_calls = Column(Integer, default=0, nullable=False)
    calls_completed = Column(Integer, default=0, nullable=False)
    calls_failed = Column(Integer, default=0, nullable=False)
    calls_in_progress = Column(Integer, default=0, nullable=False)
    retries_attempted = Column(Integer, default=0, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    calls = relationship("Call", back_populates="campaign", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Campaign(id={self.id}, name='{self.name}', status='{self.status}')>"


class Call(Base):
    """Call model representing an individual call within a campaign."""
    __tablename__ = "calls"
    
    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False, index=True)
    phone_number = Column(String(20), nullable=False)
    status = Column(SQLEnum(CallStatus), default=CallStatus.PENDING, nullable=False)
    
    # Retry tracking
    retry_count = Column(Integer, default=0, nullable=False)
    
    # Call details
    call_duration_seconds = Column(Float, nullable=True)
    error_message = Column(String(500), nullable=True)
    
    # External call ID from telephony provider
    external_call_id = Column(String(255), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    scheduled_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationship
    campaign = relationship("Campaign", back_populates="calls")
    
    def __repr__(self):
        return f"<Call(id={self.id}, phone_number='{self.phone_number}', status='{self.status}')>"
