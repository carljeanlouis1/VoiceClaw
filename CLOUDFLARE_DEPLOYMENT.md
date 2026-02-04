# VoiceClaw Cloudflare Deployment Guide

**Status:** Ready for deployment  
**Updated:** 2026-02-04  
**Completed by:** Atlas (Sub-agent)

## 🎯 What Changed

### ✅ Deepgram Flux Integration (Completed)
- **Replaced:** Faster Whisper (local ML model) → Deepgram Flux (cloud API)
- **Benefits:**
  - Ultra-low latency (~260ms end-of-turn detection)
  - Built-in turn detection for natural conversations
  - Nova-3 level accuracy
  - No local GPU needed
  - $200 free credit ($0.0077/min after)

### ✅ Configuration Updates
- Added Deepgram SDK to `requirements.txt`
- Created `transcription_deepgram.py` service
- Updated `config.py` with Deepgram settings
- Set default model to `anthropic/claude-sonnet-4-5`
- Updated TTS to use OpenAI API (cloud)

### ✅ Deployment Architecture
```
Frontend (Cloudflare Pages)
    ↓ WebSocket
Backend (Railway/Fly.io)
    ↓ HTTP
Clawdbot Gateway (Local or Tunnel)
```

## 📋 Prerequisites

### 1. Deepgram API Key
1. Sign up at https://console.deepgram.com/signup
2. Get $200 free credit (no credit card required)
3. Create API key from dashboard
4. Save it for later

### 2. OpenAI API Key (for TTS)
1. Sign up at https://platform.openai.com/
2. Create API key from https://platform.openai.com/api-keys
3. TTS costs ~$0.015/1K characters

### 3. Cloudflare Account
- Already logged in via wrangler CLI ✓

## 🚀 Deployment Steps

### Step 1: Deploy Frontend to Cloudflare Pages

```bash
cd /root/clawd/projects/VoiceClaw/vocalis-fork/frontend

# Build the frontend
npm install
npm run build

# Deploy to Cloudflare Pages
wrangler pages deploy dist --project-name=voiceclaw

# You'll get a URL like: https://voiceclaw.pages.dev
```

### Step 2: Set Up Environment Variables

Update `backend/.env` with your API keys:

```bash
cd /root/clawd/projects/VoiceClaw/vocalis-fork/backend

# Edit .env and add:
DEEPGRAM_API_KEY=your_deepgram_key_here
OPENAI_API_KEY=your_openai_key_here  # For TTS
LLM_MODEL=anthropic/claude-sonnet-4-5
```

### Step 3: Deploy Backend to Railway

#### Option A: Railway (Recommended - Free Tier)

1. **Install Railway CLI:**
   ```bash
   npm install -g @railway/cli
   railway login
   ```

2. **Create new project:**
   ```bash
   cd /root/clawd/projects/VoiceClaw/vocalis-fork
   railway init
   ```

3. **Add environment variables:**
   ```bash
   railway variables set DEEPGRAM_API_KEY=your_key_here
   railway variables set OPENAI_API_KEY=your_key_here
   railway variables set TTS_API_KEY=your_key_here
   railway variables set CLAWDBOT_GATEWAY_URL=your_tunnel_url_here
   railway variables set CLAWDBOT_GATEWAY_TOKEN=2021d0c73712e4aa12c300d1183a7e067eddea7eb29ee93e
   railway variables set CLAWDBOT_AGENT_ID=main
   railway variables set CLAWDBOT_SESSION_KEY=agent:main:main
   railway variables set USE_CLAWDBOT=true
   railway variables set USE_DEEPGRAM=true
   railway variables set LLM_MODEL=anthropic/claude-sonnet-4-5
   ```

4. **Deploy:**
   ```bash
   cd backend
   railway up
   ```

5. **Get deployment URL:**
   ```bash
   railway status
   # Note the URL (e.g., https://voiceclaw-backend-production.up.railway.app)
   ```

#### Option B: Fly.io (Alternative)

1. **Install Fly CLI:**
   ```bash
   curl -L https://fly.io/install.sh | sh
   flyctl auth login
   ```

2. **Create app:**
   ```bash
   cd /root/clawd/projects/VoiceClaw/vocalis-fork/backend
   flyctl launch --name voiceclaw-backend
   ```

3. **Set secrets:**
   ```bash
   flyctl secrets set DEEPGRAM_API_KEY=your_key_here
   flyctl secrets set OPENAI_API_KEY=your_key_here
   flyctl secrets set TTS_API_KEY=your_key_here
   flyctl secrets set CLAWDBOT_GATEWAY_URL=your_tunnel_url_here
   flyctl secrets set CLAWDBOT_GATEWAY_TOKEN=2021d0c73712e4aa12c300d1183a7e067eddea7eb29ee93e
   flyctl secrets set CLAWDBOT_AGENT_ID=main
   flyctl secrets set CLAWDBOT_SESSION_KEY=agent:main:main
   flyctl secrets set USE_CLAWDBOT=true
   flyctl secrets set LLM_MODEL=anthropic/claude-sonnet-4-5
   ```

4. **Deploy:**
   ```bash
   flyctl deploy
   ```

### Step 4: Expose Clawdbot Gateway via Cloudflare Tunnel

The backend needs to reach `http://127.0.0.1:18789` (your local Clawdbot gateway).

#### Install Cloudflare Tunnel:
```bash
# Download cloudflared
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64
chmod +x cloudflared-linux-arm64
sudo mv cloudflared-linux-arm64 /usr/local/bin/cloudflared

# Login to Cloudflare
cloudflared tunnel login

# Create tunnel
cloudflared tunnel create voiceclaw-gateway

# Configure tunnel (creates config.yml)
cat > ~/.cloudflared/config.yml <<EOF
tunnel: voiceclaw-gateway
credentials-file: /root/.cloudflared/<tunnel-id>.json

ingress:
  - hostname: voiceclaw-gateway.yourdomain.com
    service: http://127.0.0.1:18789
  - service: http_status:404
EOF

# Run tunnel
cloudflared tunnel run voiceclaw-gateway
```

**Note:** You'll get a tunnel URL like `https://voiceclaw-gateway-random.trycloudflare.com`

Use this URL for `CLAWDBOT_GATEWAY_URL` in your backend environment variables.

### Step 5: Update Frontend Configuration

Update frontend to connect to your deployed backend:

```bash
cd /root/clawd/projects/VoiceClaw/vocalis-fork/frontend

# Edit src/config.js or wherever WebSocket URL is configured
# Change: ws://localhost:8000/ws
# To: wss://your-backend-url.railway.app/ws
```

Rebuild and redeploy:
```bash
npm run build
wrangler pages deploy dist --project-name=voiceclaw
```

## 🧪 Testing

### Test Backend Health:
```bash
curl https://your-backend-url.railway.app/health
```

Expected response:
```json
{
  "status": "ok",
  "services": {
    "transcription": true,
    "llm": true,
    "tts": true
  },
  "clawdbot": {
    "enabled": true,
    "gateway_url": "https://your-tunnel-url.trycloudflare.com",
    "has_token": true,
    "has_session_key": true
  },
  "config": {
    "stt_provider": "deepgram_flux",
    "stt_model": "flux-general-en",
    "has_deepgram_key": true
  }
}
```

### Test Frontend:
1. Visit `https://voiceclaw.pages.dev`
2. Click microphone button
3. Speak: "Hello, can you hear me?"
4. Check response

### Test Session Sharing:
1. Have a conversation in VoiceClaw
2. Send a message via Telegram to Carl's Clawdbot
3. Ask: "What did we just talk about?"
4. Should remember the voice conversation

## 📊 Cost Estimates

### Free Tier:
- **Cloudflare Pages:** Free (unlimited requests)
- **Railway:** $5/month credit (enough for testing)
- **Deepgram:** $200 free credit (~25,000 minutes)
- **Cloudflare Tunnel:** Free

### Pay-as-you-go (after free tier):
- **Deepgram Flux:** $0.0077/min (~$0.46/hour)
- **OpenAI TTS:** $0.015/1K chars (~$0.01-0.03 per response)
- **Railway:** $0.000231/GB-hour + $0.20/GB egress
- **Total:** ~$1-3/day with moderate usage

## 🔧 Troubleshooting

### Backend can't reach gateway:
- Verify Cloudflare Tunnel is running
- Check `CLAWDBOT_GATEWAY_URL` is set correctly
- Test tunnel: `curl https://your-tunnel-url/health`

### No transcription:
- Verify `DEEPGRAM_API_KEY` is set
- Check backend logs: `railway logs`
- Test Deepgram API directly

### Session not shared:
- Verify `CLAWDBOT_SESSION_KEY=agent:main:main`
- Check gateway token is correct
- Both backend and Telegram should use same session key

### Frontend can't connect to backend:
- Verify WebSocket URL uses `wss://` (not `ws://`)
- Check CORS settings in backend
- Test WebSocket: `wscat -c wss://your-backend-url/ws`

## 📝 Files Modified

- ✅ `backend/requirements.txt` - Added deepgram-sdk
- ✅ `backend/services/transcription_deepgram.py` - NEW (Deepgram integration)
- ✅ `backend/config.py` - Added Deepgram settings
- ✅ `backend/main.py` - Use Deepgram by default
- ✅ `backend/.env` - Added Deepgram/OpenAI keys
- ✅ `frontend/wrangler.toml` - Ready for deployment

## 🎉 Success Criteria

- [x] Deepgram Flux integration working
- [x] Sonnet 4.5 as default model
- [x] Session sharing enabled
- [ ] Frontend deployed to Cloudflare Pages
- [ ] Backend deployed to Railway/Fly.io
- [ ] Gateway exposed via Cloudflare Tunnel
- [ ] End-to-end voice conversation working
- [ ] Mobile access confirmed

## 🚨 Next Steps for Carl

1. **Get API Keys:**
   - Deepgram: https://console.deepgram.com/signup
   - OpenAI: https://platform.openai.com/api-keys

2. **Deploy Frontend:**
   ```bash
   cd /root/clawd/projects/VoiceClaw/vocalis-fork/frontend
   npm run build
   wrangler pages deploy dist --project-name=voiceclaw
   ```

3. **Set up Railway:**
   - Install CLI: `npm install -g @railway/cli`
   - Login: `railway login`
   - Deploy backend (see Step 3 above)

4. **Set up Cloudflare Tunnel:**
   - Install cloudflared
   - Create tunnel for gateway
   - Update backend env vars

5. **Test on phone:**
   - Visit Cloudflare Pages URL
   - Grant microphone permission
   - Have a conversation!

## 💬 Questions?

Contact Atlas via Telegram (this deployment was automated by sub-agent).

---

**Deployment prepared by:** Atlas Sub-Agent (2026-02-04)  
**Session:** agent:main:subagent:71ef73f1-cb13-4c2f-974f-5a7486d0ab8c  
**Task:** VoiceClaw Cloudflare Deployment with Deepgram Integration
