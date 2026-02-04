# Railway Control Setup

Quick setup to let Atlas pause/resume your VoiceClaw Railway deployment on command.

## Step 1: Get Your Railway API Token

1. Go to https://railway.app/account/tokens
2. Click "Create Token"
3. Copy the token

## Step 2: Get Project and Service IDs

1. Open your VoiceClaw project in Railway
2. Look at the URL: `https://railway.app/project/{PROJECT_ID}/service/{SERVICE_ID}`
3. Copy both IDs

## Step 3: Add to Environment

Add these to `/root/clawd/.env`:

```bash
# Railway Control
RAILWAY_API_TOKEN=your_token_here
RAILWAY_PROJECT_ID=your_project_id_here
RAILWAY_SERVICE_ID=your_service_id_here
```

## Step 4: Test It

```bash
# Check status
/root/clawd/scripts/railway-control.sh status

# Pause deployment (stops burning credits)
/root/clawd/scripts/railway-control.sh pause

# Resume deployment (starts server)
/root/clawd/scripts/railway-control.sh resume
```

## Atlas Integration

Once configured, you can just ask me:
- "Pause VoiceClaw Railway"
- "Start VoiceClaw Railway"
- "Check VoiceClaw status"

And I'll handle it automatically!

---

**Credit Saving Strategy:**
- Keep it paused when not in use
- Resume when you want to use voice chat
- Takes ~30 seconds to start up after resume
- Completely free when paused (no compute charges)
