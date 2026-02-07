"""
CRUD operations for campaigns and calls.
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app import models, schemas
from app.config import settings


def create_campaign(db: Session, campaign: schemas.CampaignCreate) -> models.Campaign:
    """Create a new campaign with calls."""
    # Create campaign
    db_campaign = models.Campaign(
        name=campaign.name,
        max_concurrent_calls=campaign.max_concurrent_calls or settings.default_max_concurrent_calls,
        max_retries=campaign.max_retries,
        retry_delay_seconds=campaign.retry_delay_seconds,
        business_hours=campaign.business_hours.dict() if campaign.business_hours else None,
        status=models.CampaignStatus.PENDING,
        total_calls=len(campaign.phone_numbers)
    )
    
    db.add(db_campaign)
    db.flush()  # Get the campaign ID
    
    # Create calls
    for phone_number in campaign.phone_numbers:
        db_call = models.Call(
            campaign_id=db_campaign.id,
            phone_number=phone_number,
            status=models.CallStatus.PENDING
        )
        db.add(db_call)
    
    db.commit()
    db.refresh(db_campaign)
    
    return db_campaign


def get_campaign(db: Session, campaign_id: int) -> Optional[models.Campaign]:
    """Get a campaign by ID."""
    return db.query(models.Campaign).filter(models.Campaign.id == campaign_id).first()


def get_campaigns(db: Session, skip: int = 0, limit: int = 100) -> List[models.Campaign]:
    """Get list of campaigns."""
    return db.query(models.Campaign).offset(skip).limit(limit).all()


def update_campaign(db: Session, campaign_id: int, campaign_update: schemas.CampaignUpdate) -> Optional[models.Campaign]:
    """Update a campaign."""
    db_campaign = get_campaign(db, campaign_id)
    if not db_campaign:
        return None
    
    update_data = campaign_update.dict(exclude_unset=True)
    
    # Convert business_hours to dict if present
    if 'business_hours' in update_data and update_data['business_hours']:
        update_data['business_hours'] = update_data['business_hours'].dict()
    
    for field, value in update_data.items():
        setattr(db_campaign, field, value)
    
    db.commit()
    db.refresh(db_campaign)
    
    return db_campaign


def delete_campaign(db: Session, campaign_id: int) -> bool:
    """Delete a campaign."""
    db_campaign = get_campaign(db, campaign_id)
    if not db_campaign:
        return False
    
    db.delete(db_campaign)
    db.commit()
    
    return True


def get_calls_by_campaign(db: Session, campaign_id: int, skip: int = 0, limit: int = 100) -> List[models.Call]:
    """Get calls for a campaign."""
    return db.query(models.Call).filter(
        models.Call.campaign_id == campaign_id
    ).offset(skip).limit(limit).all()


def get_call(db: Session, call_id: int) -> Optional[models.Call]:
    """Get a call by ID."""
    return db.query(models.Call).filter(models.Call.id == call_id).first()


def calculate_campaign_statistics(db: Session, campaign: models.Campaign) -> schemas.CampaignStatistics:
    """Calculate campaign statistics from actual call records."""
    # Query actual counts from database to avoid race conditions
    total = db.query(models.Call).filter(models.Call.campaign_id == campaign.id).count()
    
    completed = db.query(models.Call).filter(
        models.Call.campaign_id == campaign.id,
        models.Call.status == models.CallStatus.COMPLETED
    ).count()
    
    failed = db.query(models.Call).filter(
        models.Call.campaign_id == campaign.id,
        models.Call.status == models.CallStatus.FAILED
    ).count()
    
    in_progress = db.query(models.Call).filter(
        models.Call.campaign_id == campaign.id,
        models.Call.status == models.CallStatus.IN_PROGRESS
    ).count()
    
    pending = db.query(models.Call).filter(
        models.Call.campaign_id == campaign.id,
        models.Call.status.in_([models.CallStatus.PENDING, models.CallStatus.SCHEDULED])
    ).count()
    
    retries_attempted = db.query(func.sum(models.Call.retry_count)).filter(
        models.Call.campaign_id == campaign.id
    ).scalar() or 0
    
    success_rate = (completed / total * 100) if total > 0 else 0
    completion_rate = ((completed + failed) / total * 100) if total > 0 else 0
    
    return schemas.CampaignStatistics(
        total_calls=total,
        calls_completed=completed,
        calls_failed=failed,
        calls_in_progress=in_progress,
        calls_pending=pending,
        retries_attempted=retries_attempted,
        success_rate=round(success_rate, 2),
        completion_rate=round(completion_rate, 2)
    )


def get_campaign_response(db: Session, campaign: models.Campaign) -> schemas.CampaignResponse:
    """Convert campaign model to response schema."""
    statistics = calculate_campaign_statistics(db, campaign)
    
    return schemas.CampaignResponse(
        id=campaign.id,
        name=campaign.name,
        status=campaign.status,
        max_concurrent_calls=campaign.max_concurrent_calls,
        business_hours=campaign.business_hours,
        max_retries=campaign.max_retries,
        retry_delay_seconds=campaign.retry_delay_seconds,
        statistics=statistics,
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
        started_at=campaign.started_at,
        completed_at=campaign.completed_at
    )
