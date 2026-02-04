# VoiceClaw Troubleshooting & Optimization Summary

**Session Date:** February 3-4, 2026  
**Session Lead:** Claude Code (Opus 4.5)  
**Objective:** Fix deployment issues, implement performance optimizations, establish permanent infrastructure

---

## Overview

Claude Code (Opus 4.5) helped Carl troubleshoot and optimize VoiceClaw, a real-time voice-to-voice interface that connects to Clawdbot/Atlas through a Railway-deployed backend. The session involved fixing deployment issues, implementing performance optimizations, and setting up permanent infrastructure.

---

## Part 1: Railway Deployment Debugging (502 Errors)

### Initial Problem
VoiceClaw backend was deployed on Railway and showed "Online" status, but returned 502 errors on all endpoints. The app was built successfully but crashed during startup.

### Root Cause Discovery
Error in logs:
```
ModuleNotFoundError: No module named 'requests'
```

The `services/llm.py` and `services/tts.py` files imported `requests`, but it was missing from `requirements.txt`.

### Fix Applied
1. Added `requests>=2.31.0` to `/root/clawd/projects/VoiceClaw/vocalis-fork/backend/requirements.txt`
2. Changed `services/transcription.py` to warn instead of crash when `DEEPGRAM_API_KEY` is missing
3. Committed and pushed to GitHub for Railway auto-deploy

**Commit:** `b6e5e55` - "Fix: Add missing requests dependency, soften API key check"

---

## Part 2: Gateway URL Resolution (openclaw.ai → clawd.bot)

### Problem
After fixing the 502 error, VoiceClaw was trying to connect to `https://openclaw.ai/v1/chat/completions` which returned 404 errors. The health endpoint showed `clawd.bot` but actual LLM requests went to `openclaw.ai`.

### Root Cause Discovery
Ran this test:
```bash
curl -sL https://clawd.bot/v1/chat/completions
```
Result: `clawd.bot` was redirecting (301) to `openclaw.ai`, which doesn't exist.

### Understanding
Carl's Clawdbot gateway runs locally in WSL at `localhost:18789`. Railway (cloud) cannot access localhost, so a tunnel is needed to expose the local gateway to the internet.

### Fix Applied
1. Installed `cloudflared` (ARM64 version for WSL)
2. Started a temporary Cloudflare tunnel:
   ```bash
   cloudflared tunnel --url http://localhost:18789
   ```
3. Got temporary URL: `https://portal-residents-congratulations-beats.trycloudflare.com`
4. Updated `config.py` with the tunnel URL
5. Pushed to GitHub

**Commit:** `a469475` - "Fix: Use Cloudflare tunnel URL for gateway access"

---

## Part 3: Authentication Fix (401 Unauthorized)

### Problem
After fixing the URL, got 401 Unauthorized errors - the tunnel was working but authentication was failing.

### Root Cause
Railway didn't have the `CLAWDBOT_GATEWAY_TOKEN` environment variable set.

### Fix Applied
Found the token in `~/.clawdbot/clawdbot.json`:
```json
{
  "gateway": {
    "auth": {
      "mode": "token",
      "token": "2021d0c73712e4aa12c300d1183a7e067eddea7eb29ee93e"
    }
  }
}
```

Carl added this to Railway's environment variables:
- **Variable:** `CLAWDBOT_GATEWAY_TOKEN`
- **Value:** `2021d0c73712e4aa12c300d1183a7e067eddea7eb29ee93e`

**Result:** VoiceClaw started working! ✅

---

## Part 4: Performance Optimization (Phase 1 - Streaming)

### Problem
VoiceClaw had 3-5 second latency before the user heard a response.

### Bottleneck Analysis
**Old flow (blocking):**
1. User speaks → Deepgram STT (300-500ms)
2. ⚠️ WAIT for complete LLM response (2-4 seconds)
3. Full response → OpenAI TTS (500-800ms)
4. ⚠️ WAIT for complete audio (200-400ms)
5. Play audio

### Solution Implemented: LLM Streaming + Sentence Buffering

#### 1. Updated `services/llm.py`
Added new `stream_response()` async method that:
- Uses `httpx` for async HTTP streaming
- Enables `"stream": true` in the API request
- Yields tokens as they arrive from the LLM
- Maintains conversation history

#### 2. Created `services/streaming.py`
New module with sentence buffering logic:
- `is_sentence_complete()` - detects sentence endings (. ! ? \n)
- `stream_speech_with_buffering()` - orchestrates the streaming pipeline:
  - Buffers tokens until a complete sentence is detected
  - Sends each sentence to TTS immediately
  - Streams audio chunks to the frontend as they're ready

#### 3. Updated `routes/websocket.py`
- Added import for streaming module
- Modified `_process_speech_segment()` to use streaming for normal (non-vision) speech processing
- Vision processing path left unchanged (uses full response)

### Expected Improvement
- **Before:** First audio at 3-5 seconds
- **After:** First audio at ~1-1.5 seconds

**Commit:** `82ddda5` - "Perf: Add LLM streaming + sentence buffering for lower latency"

---

## Part 5: Permanent Cloudflare Tunnel Setup

### Problem
The temporary tunnel URL (trycloudflare.com) changes every time it restarts, requiring manual config updates.

### Solution: Named Cloudflare Tunnel

#### Steps Performed:
1. **Authenticated cloudflared:**
   ```bash
   cloudflared tunnel login
   ```
   - Carl authorized via browser on `nimblelogicai.com` domain

2. **Created named tunnel:**
   ```bash
   cloudflared tunnel create voiceclaw-gateway
   ```
   - Tunnel ID: `b88b66a2-5f2e-4fc6-8697-e6c9c2e4cb2f`

3. **Created config file** at `/root/.cloudflared/config.yml`:
   ```yaml
   tunnel: voiceclaw-gateway
   credentials-file: /root/.cloudflared/b88b66a2-5f2e-4fc6-8697-e6c9c2e4cb2f.json
   
   ingress:
     - service: http://localhost:18789
   ```

4. **Set up DNS route:**
   ```bash
   cloudflared tunnel route dns voiceclaw-gateway gateway.nimblelogicai.com
   ```

5. **Updated VoiceClaw config** with permanent URL:
   ```python
   CLAWDBOT_GATEWAY_URL = "https://gateway.nimblelogicai.com"
   ```

**Commit:** `4cced19` - "Config: Use permanent Cloudflare tunnel URL"

### Permanent URL
**https://gateway.nimblelogicai.com** - This URL never changes.

---

## Part 6: Auto-Start Services on WSL Boot

### Problem
After PC restart, Clawdbot and the tunnel need to be manually started.

### Solution: Startup Script

Created `/root/start-services.sh`:
```bash
#!/bin/bash
echo "Starting Clawdbot gateway..."
pgrep -f clawdbot-gateway > /dev/null || nohup /usr/bin/clawdbot gateway > /tmp/clawdbot.log 2>&1 &

sleep 2

echo "Starting Cloudflare tunnel..."
pgrep -f 'cloudflared tunnel run' > /dev/null || nohup cloudflared tunnel run voiceclaw-gateway > /tmp/cloudflared.log 2>&1 &

sleep 3

echo ""
echo "Status:"
pgrep -f clawdbot-gateway > /dev/null && echo "  ✓ Clawdbot running" || echo "  ✗ Clawdbot NOT running"
pgrep -f 'cloudflared tunnel run' > /dev/null && echo "  ✓ Tunnel running" || echo "  ✗ Tunnel NOT running"
```

Added to `/root/.bashrc` so it runs automatically when Ubuntu terminal opens.

### Manual Commands (if needed)
```bash
# Start services
/root/start-services.sh

# Check status
pgrep -a clawdbot
pgrep -a cloudflared

# View logs
tail -f /tmp/clawdbot.log
tail -f /tmp/cloudflared.log
```

---

## Part 7: Mobile UI Fix (Buttons Not Visible)

### Problem
On mobile phones, the phone/mic buttons at the bottom of VoiceClaw were not visible - cut off by the browser's navigation bar.

### Root Cause
Buttons were positioned at `bottom-8` (32px) which gets hidden by mobile browser chrome.

### Fix Applied

#### 1. Updated `ChatInterface.tsx`
Changed button container positioning:
```tsx
// Before
<div className="absolute bottom-8 left-1/2 ...">

// After
<div className="absolute bottom-20 sm:bottom-8 left-1/2 pb-safe ...">
```
- Mobile: 80px from bottom (`bottom-20`)
- Desktop: 32px from bottom (`sm:bottom-8`)

#### 2. Updated `index.css`
Added safe area support for iPhone notches:
```css
@supports (padding-bottom: env(safe-area-inset-bottom)) {
  .pb-safe {
    padding-bottom: env(safe-area-inset-bottom);
  }
}

html {
  height: -webkit-fill-available;
}

body {
  min-height: 100vh;
  min-height: -webkit-fill-available;
}
```

**Commit:** `6b641c6` - "Fix: Mobile button visibility - increase bottom margin for phone browsers"

---

## Summary of All Commits

| Commit  | Description                                    |
|---------|------------------------------------------------|
| b6e5e55 | Fix: Add missing requests dependency          |
| a469475 | Fix: Use Cloudflare tunnel URL for gateway    |
| 82ddda5 | Perf: Add LLM streaming + sentence buffering   |
| 4cced19 | Config: Use permanent Cloudflare tunnel URL    |
| 6b641c6 | Fix: Mobile button visibility                  |

---

## Current Architecture

```
┌─────────────────┐     ┌──────────────────────────────┐
│  Phone/Browser  │────▶│  voiceclaw.pages.dev         │
│  (Frontend)     │     │  (Cloudflare Pages)          │
└─────────────────┘     └──────────────────────────────┘
                                      │
                                      │ WebSocket
                                      ▼
                        ┌──────────────────────────────┐
                        │  voiceclaw-production.       │
                        │  up.railway.app              │
                        │  (Railway - FastAPI Backend) │
                        └──────────────────────────────┘
                                      │
                                      │ HTTPS + Auth Token
                                      ▼
                        ┌──────────────────────────────┐
                        │  gateway.nimblelogicai.com   │
                        │  (Cloudflare Tunnel)         │
                        └──────────────────────────────┘
                                      │
                                      │ localhost:18789
                                      ▼
                        ┌──────────────────────────────┐
                        │  Clawdbot Gateway (WSL)      │
                        │  → Atlas (Sonnet 4.5)        │
                        └──────────────────────────────┘
```

---

## Key Files Modified

### Backend (`vocalis-fork/backend/`)
- `requirements.txt` - Added requests>=2.31.0
- `config.py` - Hardcoded permanent gateway URL
- `services/llm.py` - Added streaming support
- `services/streaming.py` - New file for sentence buffering
- `services/transcription.py` - Softened API key check
- `routes/websocket.py` - Use streaming for speech processing

### Frontend (`vocalis-fork/frontend/`)
- `src/components/ChatInterface.tsx` - Mobile button positioning
- `src/index.css` - Safe area CSS for mobile

### System (`/root/`)
- `.cloudflared/config.yml` - Tunnel configuration
- `start-services.sh` - Auto-start script
- `.bashrc` - Auto-run startup script

---

## Important URLs & Credentials

| Resource       | URL/Value                                     |
|----------------|-----------------------------------------------|
| Frontend       | https://voiceclaw.pages.dev                   |
| Backend        | https://voiceclaw-production.up.railway.app   |
| Gateway Tunnel | https://gateway.nimblelogicai.com             |
| Tunnel Name    | voiceclaw-gateway                             |
| Tunnel ID      | b88b66a2-5f2e-4fc6-8697-e6c9c2e4cb2f          |
| Gateway Token  | 2021d0c73712e4aa12c300d1183a7e067eddea7eb29ee93e |

---

## After PC Restart Checklist

1. Open Ubuntu terminal (services auto-start via `.bashrc`)
2. Verify with: `pgrep -a clawdbot && pgrep -a cloudflared`
3. If needed, manually run: `/root/start-services.sh`

---

## Next Phases (Future Work)

Based on the PERFORMANCE_OPTIMIZATION.md guide created during this session:

### Phase 2: TTS Streaming (Not Yet Implemented)
- Replace synchronous OpenAI TTS with streaming
- Stream audio chunks as they're generated
- Expected improvement: ~500ms faster first audio

### Phase 3: Parallel Processing (Not Yet Implemented)
- Run STT → LLM → TTS pipeline in parallel
- Use asyncio.gather() for concurrent operations
- Potential improvement: ~1-2 seconds faster overall

### Phase 4: Caching & Pre-warming (Not Yet Implemented)
- Cache common responses
- Pre-warm TTS for frequent phrases
- WebSocket connection pooling

---

**Generated by:** Claude Code (Opus 4.5) for Atlas/Clawdbot context sharing  
**Date:** February 3-4, 2026  
**Saved by:** Atlas
