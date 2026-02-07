"""
Celery tasks for processing calls.
"""
import asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from celery import Task

from app.celery_app import celery_app
from app.database import SessionLocal
from app.models import Campaign, Call, CampaignStatus, CallStatus
from app.telephony_mock import telephony_service
from app.business_hours import is_within_business_hours, calculate_next_business_hour


class DatabaseTask(Task):
    """Base task with database session management."""
    _db = None
    
    @property
    def db(self) -> Session:
        if self._db is None:
            self._db = SessionLocal()
        return self._db
    
    def after_return(self, *args, **kwargs):
        if self._db is not None:
            self._db.close()
            self._db = None


@celery_app.task(base=DatabaseTask, bind=True, max_retries=0)
def process_call(self, call_id: int):
    """
    Process a single call.
    
    Args:
        call_id: ID of the call to process
    """
    db = self.db
    
    # Get call
    call = db.query(Call).filter(Call.id == call_id).first()
    if not call:
        return {"error": f"Call {call_id} not found"}
    
    # Get campaign
    campaign = db.query(Campaign).filter(Campaign.id == call.campaign_id).first()
    if not campaign:
        return {"error": f"Campaign {call.campaign_id} not found"}
    
    # Check business hours
    if not is_within_business_hours(campaign.business_hours):
        # Schedule for next business hour
        next_time = calculate_next_business_hour(campaign.business_hours)
        if next_time:
            call.status = CallStatus.SCHEDULED
            call.scheduled_at = next_time
            db.commit()
            
            # Schedule task to run at next business hour
            delay_seconds = (next_time - datetime.now(timezone.utc)).total_seconds()
            process_call.apply_async(args=[call_id], countdown=max(0, delay_seconds))
            
            return {"message": f"Call scheduled for {next_time}", "call_id": call_id}
    
    # Update call status
    call.status = CallStatus.IN_PROGRESS
    call.started_at = datetime.now(timezone.utc)
    
    db.commit()
    
    # Make the call (run async function in sync context)
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        external_call_id, success, duration, error_message = loop.run_until_complete(
            telephony_service.initiate_call(call.phone_number)
        )
        loop.close()
        
        # Update call with results
        call.external_call_id = external_call_id
        call.call_duration_seconds = duration
        call.completed_at = datetime.now(timezone.utc)
        
        if success:
            call.status = CallStatus.COMPLETED
        else:
            call.error_message = error_message
            
            # Check if we should retry
            if call.retry_count < campaign.max_retries:
                call.retry_count += 1
                call.status = CallStatus.PENDING
                
                # Schedule retry
                retry_call.apply_async(
                    args=[call_id],
                    countdown=campaign.retry_delay_seconds
                )
            else:
                call.status = CallStatus.FAILED
        
        db.commit()
        
        # Check if campaign is complete
        check_campaign_completion.apply_async(args=[campaign.id])
        
        # Process next call in queue (respecting concurrency limits)
        process_next_call.apply_async(args=[campaign.id])
        
        return {
            "call_id": call_id,
            "status": call.status.value,
            "success": success,
            "external_call_id": external_call_id
        }
        
    except Exception as e:
        # Handle errors
        call.status = CallStatus.FAILED
        call.error_message = str(e)
        call.completed_at = datetime.now(timezone.utc)
        
        db.commit()
        
        return {"error": str(e), "call_id": call_id}


@celery_app.task(base=DatabaseTask, bind=True)
def retry_call(self, call_id: int):
    """
    Retry a failed call.
    
    Args:
        call_id: ID of the call to retry
    """
    # Simply requeue the call for processing
    # Retries are prioritized over new calls
    process_call.apply_async(args=[call_id])
    return {"message": f"Call {call_id} queued for retry"}


@celery_app.task(base=DatabaseTask, bind=True)
def process_next_call(self, campaign_id: int):
    """
    Process the next pending call in a campaign, respecting concurrency limits.
    
    Args:
        campaign_id: ID of the campaign
    """
    db = self.db
    
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        return {"error": f"Campaign {campaign_id} not found"}
    
    # Check if campaign is paused or completed
    if campaign.status in [CampaignStatus.PAUSED, CampaignStatus.COMPLETED, CampaignStatus.FAILED]:
        return {"message": "Campaign is not active"}
    
    # Check concurrency limit
    current_in_progress = db.query(Call).filter(
        Call.campaign_id == campaign_id,
        Call.status == CallStatus.IN_PROGRESS
    ).count()
    
    if current_in_progress >= campaign.max_concurrent_calls:
        return {"message": "Concurrency limit reached"}
    
    # First, prioritize retries (failed calls with retry attempts remaining)
    pending_call = db.query(Call).filter(
        Call.campaign_id == campaign_id,
        Call.status == CallStatus.PENDING,
        Call.retry_count > 0
    ).order_by(Call.updated_at).first()
    
    # If no retries, get next new call
    if not pending_call:
        pending_call = db.query(Call).filter(
            Call.campaign_id == campaign_id,
            Call.status == CallStatus.PENDING,
            Call.retry_count == 0
        ).order_by(Call.created_at).first()
    
    if pending_call:
        # Process this call
        process_call.apply_async(args=[pending_call.id])
        return {"message": f"Processing call {pending_call.id}"}
    
    return {"message": "No pending calls"}


@celery_app.task(base=DatabaseTask, bind=True)
def start_campaign(self, campaign_id: int):
    """
    Start a campaign by initiating calls up to the concurrency limit.
    
    Args:
        campaign_id: ID of the campaign to start
    """
    db = self.db
    
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        return {"error": f"Campaign {campaign_id} not found"}
    
    # Update campaign status
    campaign.status = CampaignStatus.IN_PROGRESS
    campaign.started_at = datetime.now(timezone.utc)
    db.commit()
    
    # Start processing calls up to concurrency limit
    for _ in range(campaign.max_concurrent_calls):
        process_next_call.apply_async(args=[campaign_id])
    
    return {"message": f"Campaign {campaign_id} started"}


@celery_app.task(base=DatabaseTask, bind=True)
def check_campaign_completion(self, campaign_id: int):
    """
    Check if a campaign has completed all calls.
    
    Args:
        campaign_id: ID of the campaign
    """
    db = self.db
    
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        return {"error": f"Campaign {campaign_id} not found"}
    
    # Check if there are any pending or in-progress calls
    active_calls = db.query(Call).filter(
        Call.campaign_id == campaign_id,
        Call.status.in_([CallStatus.PENDING, CallStatus.IN_PROGRESS, CallStatus.SCHEDULED])
    ).count()
    
    if active_calls == 0 and campaign.status == CampaignStatus.IN_PROGRESS:
        # Campaign is complete
        campaign.status = CampaignStatus.COMPLETED
        campaign.completed_at = datetime.now(timezone.utc)
        db.commit()
        
        return {"message": f"Campaign {campaign_id} completed"}
    
    return {"message": "Campaign still has active calls"}
