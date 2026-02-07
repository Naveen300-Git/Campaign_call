# Quick Start Guide

Get the Campaign Calls microservice running in 5 minutes!

# Docker Setup

### Step 1: Install Docker

Download from https://www.docker.com/get-started

### Step 2: Start Services

```bash
cd "Campaign Calls"
docker-compose up -d
```

**Wait for services to be ready**:
```bash
# Check status
docker-compose ps

# View logs to confirm services are up
docker-compose logs -f api
```

**Done!** 🚀

- API: http://localhost:8000
- Docs: http://localhost:8000/docs

View all logs:
```bash
docker-compose logs -f
```

Stop services:
```bash
docker-compose down
```

**If containers keep restarting:**
```bash
# Stop all services
docker-compose down

# Rebuild and start fresh
docker-compose up -d --build

# Wait 15 seconds for PostgreSQL to initialize
sleep 15

# Check logs
docker-compose logs api
```

---

## Test Your Setup

### Health Check
```bash
curl http://localhost:8000/health
```

### 1. Create a Campaign
```bash
curl -X POST "http://localhost:8000/campaigns" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Bangalore Sales Campaign",
    "phone_numbers": ["+919876543210", "+919876543211"],
    "max_concurrent_calls": 2,
    "max_retries": 3,
    "retry_delay_seconds": 300
  }'
```

**Response:** Returns campaign with `id: 1`

### 2. List All Campaigns
```bash
curl "http://localhost:8000/campaigns"
```

### 3. Get Campaign Details
```bash
curl "http://localhost:8000/campaigns/{campaign_id}"
```

### 4. Update a Campaign
```bash
curl -X PUT "http://localhost:8000/campaigns/{campaign_id}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Bangalore Sales Campaign - Updated",
    "max_concurrent_calls": 5
  }'
```

### 5. Start the Campaign
```bash
curl -X POST "http://localhost:8000/campaigns/{campaign_id}/start"
```

### 6. Check Campaign Status
```bash
curl "http://localhost:8000/campaigns/{campaign_id}"
```

### 7. Get Campaign Calls
```bash
curl "http://localhost:8000/campaigns/{campaign_id}/calls"
```

### 8. Get Individual Call Status
```bash
# Replace {call_id} with actual call ID from campaign calls
curl "http://localhost:8000/calls/{call_id}"
```

### 9. Pause a Campaign
```bash
curl -X POST "http://localhost:8000/campaigns/{campaign_id}/pause"
```

### 10. Resume a Paused Campaign
```bash
curl -X POST "http://localhost:8000/campaigns/{campaign_id}/resume"
```

### 11. Delete a Campaign
```bash
curl -X DELETE "http://localhost:8000/campaigns/{campaign_id}"
```

### Complete Example Flow
```bash
# 1. Create campaign
RESPONSE=$(curl -s -X POST "http://localhost:8000/campaigns" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Delhi Customer Outreach",
    "phone_numbers": ["+919123456781", "+919123456782", "+919123456783"],
    "max_concurrent_calls": 3,
    "max_retries": 2,
    "retry_delay_seconds": 180,
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
  }')

# Extract campaign ID (requires jq)
CAMPAIGN_ID=$(echo $RESPONSE | jq -r '.id')
echo "Created campaign: $CAMPAIGN_ID"

# 2. Start the campaign
curl -X POST "http://localhost:8000/campaigns/$CAMPAIGN_ID/start"

# 3. Check status
curl "http://localhost:8000/campaigns/$CAMPAIGN_ID"

# 4. Get all calls
curl "http://localhost:8000/campaigns/$CAMPAIGN_ID/calls"

# 5. Pause if needed
curl -X POST "http://localhost:8000/campaigns/$CAMPAIGN_ID/pause"

# 6. Resume
curl -X POST "http://localhost:8000/campaigns/$CAMPAIGN_ID/resume"
```

## Next Steps

- **API Documentation:** http://localhost:8000/docs (Interactive Swagger UI)
- **Examples:** Run scripts in `examples/` directory
- **Monitor:** Use `docker-compose logs -f` to watch real-time logs
- **Experiment:** Try creating campaigns with business hours and different timezones

### Common Use Cases

**1. Campaign with Business Hours (IST):**
```bash
curl -X POST "http://localhost:8000/campaigns" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Pune Office Hours Campaign",
    "phone_numbers": ["+919890123456", "+919890123457"],
    "business_hours": {
      "timezone": "Asia/Kolkata",
      "hours": [
        {"day": "monday", "start": "09:00", "end": "17:00"},
        {"day": "tuesday", "start": "09:00", "end": "17:00"},
        {"day": "wednesday", "start": "09:00", "end": "17:00"},
        {"day": "thursday", "start": "09:00", "end": "17:00"},
        {"day": "friday", "start": "09:00", "end": "17:00"}
      ]
    }
  }'
```

**2. High-Concurrency Campaign:**
```bash
curl -X POST "http://localhost:8000/campaigns" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Bulk SMS Follow-up Calls",
    "phone_numbers": ["+919000000001", "+919000000002", "+919000000003", "+919000000004", "+919000000005"],
    "max_concurrent_calls": 10,
    "max_retries": 5,
    "retry_delay_seconds": 120
  }'
```

**3. Monitor Progress:**
```bash
# Watch campaign progress in real-time
watch -n 2 'curl -s http://localhost:8000/campaigns/{campaign_id} | jq .statistics'
```

---

## Architecture Overview

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ HTTP
       ▼
┌─────────────┐
│  FastAPI    │ ← REST API (Port 8000)
└──────┬──────┘
       │
       ├─────────► ┌────────────┐
       │           │ PostgreSQL │ ← Campaigns & Calls Data
       │           └────────────┘
       │
       └─────────► ┌────────────┐
                   │   Redis    │ ← Task Queue
                   └──────┬─────┘
                          │
                          ▼
                   ┌────────────┐
                   │   Celery   │ ← Background Workers
                   │  Workers   │ ← Process Calls
                   └────────────┘
```

**Key Features:**
- ✅ Asynchronous call processing
- ✅ Automatic retry with configurable delays
- ✅ Business hours scheduling (timezone-aware)
- ✅ Concurrency control per campaign
- ✅ Real-time statistics and monitoring
- ✅ Horizontally scalable architecture

---

## Need Help?

- **Documentation:** Check API docs at http://localhost:8000/docs
- **Logs:** `docker-compose logs -f` for troubleshooting
- **Examples:** Review `examples/` directory for more use cases
- **Issues:** Check GitHub issues or create a new one
