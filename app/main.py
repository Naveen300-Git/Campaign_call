"""
FastAPI application for Campaign Calls microservice.
"""
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import uvicorn

from app.database import get_db, init_db
from app import crud, schemas, models
from app.tasks import start_campaign, process_next_call
from app.config import settings

# Initialize FastAPI app
app = FastAPI(
    title="Campaign Calls Microservice",
    description="Microservice for managing outbound voice call campaigns",
    version="1.0.0"
)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    init_db()


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Campaign Calls Microservice",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


# Campaign endpoints

@app.post("/campaigns", response_model=schemas.CampaignResponse, status_code=status.HTTP_201_CREATED)
def create_campaign(
    campaign: schemas.CampaignCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new outbound call campaign.
    
    - **name**: Campaign name
    - **phone_numbers**: List of phone numbers to call
    - **max_concurrent_calls**: Maximum number of concurrent calls (optional)
    - **max_retries**: Maximum retry attempts for failed calls
    - **retry_delay_seconds**: Delay between retry attempts
    - **business_hours**: Business hours configuration (optional)
    """
    db_campaign = crud.create_campaign(db, campaign)
    return crud.get_campaign_response(db, db_campaign)


@app.get("/campaigns", response_model=schemas.CampaignListResponse)
def list_campaigns(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    List all campaigns.
    
    - **skip**: Number of records to skip (pagination)
    - **limit**: Maximum number of records to return
    """
    campaigns = crud.get_campaigns(db, skip=skip, limit=limit)
    campaign_responses = [crud.get_campaign_response(db, c) for c in campaigns]
    total = db.query(models.Campaign).count()
    
    return schemas.CampaignListResponse(
        campaigns=campaign_responses,
        total=total
    )


@app.get("/campaigns/{campaign_id}", response_model=schemas.CampaignResponse)
def get_campaign(
    campaign_id: int,
    db: Session = Depends(get_db)
):
    """
    Get details of a specific campaign.
    
    - **campaign_id**: ID of the campaign
    """
    campaign = crud.get_campaign(db, campaign_id)
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign {campaign_id} not found"
        )
    
    return crud.get_campaign_response(db, campaign)


@app.put("/campaigns/{campaign_id}", response_model=schemas.CampaignResponse)
def update_campaign(
    campaign_id: int,
    campaign_update: schemas.CampaignUpdate,
    db: Session = Depends(get_db)
):
    """
    Update a campaign's configuration.
    
    - **campaign_id**: ID of the campaign
    """
    campaign = crud.update_campaign(db, campaign_id, campaign_update)
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign {campaign_id} not found"
        )
    
    return crud.get_campaign_response(db, campaign)


@app.delete("/campaigns/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_campaign(
    campaign_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a campaign.
    
    - **campaign_id**: ID of the campaign
    """
    success = crud.delete_campaign(db, campaign_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign {campaign_id} not found"
        )


@app.post("/campaigns/{campaign_id}/start", response_model=schemas.CampaignActionResponse)
def start_campaign_endpoint(
    campaign_id: int,
    db: Session = Depends(get_db)
):
    """
    Start a campaign (begin making calls).
    
    - **campaign_id**: ID of the campaign
    """
    campaign = crud.get_campaign(db, campaign_id)
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign {campaign_id} not found"
        )
    
    if campaign.status != models.CampaignStatus.PENDING:
        if campaign.status == models.CampaignStatus.IN_PROGRESS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Campaign is already in progress"
            )
        elif campaign.status == models.CampaignStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Campaign is already completed"
            )
    
    # Start campaign asynchronously
    start_campaign.apply_async(args=[campaign_id])
    
    return schemas.CampaignActionResponse(
        campaign_id=campaign_id,
        message="Campaign started",
        status=models.CampaignStatus.IN_PROGRESS
    )


@app.post("/campaigns/{campaign_id}/pause", response_model=schemas.CampaignActionResponse)
def pause_campaign(
    campaign_id: int,
    db: Session = Depends(get_db)
):
    """
    Pause a campaign (stop making new calls).
    
    - **campaign_id**: ID of the campaign
    """
    campaign = crud.get_campaign(db, campaign_id)
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign {campaign_id} not found"
        )
    
    if campaign.status != models.CampaignStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Campaign is not in progress"
        )
    
    campaign.status = models.CampaignStatus.PAUSED
    db.commit()
    
    return schemas.CampaignActionResponse(
        campaign_id=campaign_id,
        message="Campaign paused",
        status=models.CampaignStatus.PAUSED
    )


@app.post("/campaigns/{campaign_id}/resume", response_model=schemas.CampaignActionResponse)
def resume_campaign(
    campaign_id: int,
    db: Session = Depends(get_db)
):
    """
    Resume a paused campaign.
    
    - **campaign_id**: ID of the campaign
    """
    campaign = crud.get_campaign(db, campaign_id)
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign {campaign_id} not found"
        )
    
    if campaign.status != models.CampaignStatus.PAUSED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Campaign is not paused"
        )
    
    campaign.status = models.CampaignStatus.IN_PROGRESS
    db.commit()
    
    # Resume processing calls
    for _ in range(campaign.max_concurrent_calls):
        process_next_call.apply_async(args=[campaign_id])
    
    return schemas.CampaignActionResponse(
        campaign_id=campaign_id,
        message="Campaign resumed",
        status=models.CampaignStatus.IN_PROGRESS
    )


# Call endpoints

@app.get("/campaigns/{campaign_id}/calls", response_model=schemas.CallListResponse)
def list_campaign_calls(
    campaign_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    List all calls for a campaign.
    
    - **campaign_id**: ID of the campaign
    - **skip**: Number of records to skip (pagination)
    - **limit**: Maximum number of records to return
    """
    campaign = crud.get_campaign(db, campaign_id)
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign {campaign_id} not found"
        )
    
    calls = crud.get_calls_by_campaign(db, campaign_id, skip=skip, limit=limit)
    total = db.query(models.Call).filter(models.Call.campaign_id == campaign_id).count()
    
    return schemas.CallListResponse(
        calls=[schemas.CallResponse.from_orm(c) for c in calls],
        total=total
    )


@app.get("/calls/{call_id}", response_model=schemas.CallResponse)
def get_call_status(
    call_id: int,
    db: Session = Depends(get_db)
):
    """
    Get the status of a specific call.
    
    - **call_id**: ID of the call
    """
    call = crud.get_call(db, call_id)
    if not call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Call {call_id} not found"
        )
    
    return schemas.CallResponse.from_orm(call)


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )
