# VoiceClaw Cloudflare Deployment Plan

**Date:** 2026-02-03
**Goal:** Deploy VoiceClaw to Cloudflare Pages with Deepgram STT integration for mobile/remote access

## Current State

### Local Setup (Working)
- **Frontend:** React + Vite, runs on localhost:3000
- **Backend:** FastAPI + Python, runs on localhost:8000
- **Speech-to-Text:** Faster Whisper (local ML model, ~50-100ms latency)
- **LLM:** Routes to Clawdbot gateway (localhost:18789) using Sonnet 4.5
- **TTS:** OpenAI TTS API
- **Session Sharing:** Enabled with `CLAWDBOT_SESSION_KEY=agent:main:main`
- **VAD Threshold:** Updated to 0.025 to reduce false positives

### Recent Changes (Committed)
- VAD threshold increase from 0.01 to 0.025
- Session sharing enabled between voice and Telegram
- Backend .env updated with Clawdbot integration settings

## Deployment Architecture

### Frontend → Cloudflare Pages
- Static site deployment
- WebSocket connections to backend
- Already has `wrangler.toml` configured

### Backend Options
**Option 1: Cloudflare Workers (Recommended)**
- Replace Faster Whisper with Deepgram API
- Deploy backend as Cloudflare Worker
- Lowest latency (everything in Cloudflare network)
- Free tier available

**Option 2: External Host (Railway/Fly.io)**
- Keep Faster Whisper local model
- Deploy to separate service
- Requires paid hosting ($5-10/month)

**Decision: Go with Option 1 (Deepgram + Workers)**

## Key Requirements

### 1. Deepgram Integration
- **Model:** Flux (conversational AI optimized, ultra-low latency)
- **Pricing:** $0.0077/min ($200 free credit = ~25,000 minutes)
- **Features needed:**
  - Real-time streaming WebSocket
  - Low latency (<200ms)
  - VAD built-in
- **API Key:** Need to create Deepgram account and get API key

### 2. Clawdbot Gateway Access
- Backend must be able to reach `http://127.0.0.1:18789`
- **Challenge:** Workers can't access localhost
- **Solutions:**
  - Use Cloudflare Tunnel to expose gateway
  - OR deploy gateway to cloud
  - OR use session-based forwarding

### 3. Model Configuration
- Default model: Sonnet 4.5 (`anthropic/claude-sonnet-4-5`)
- Opus 4.5 available as fallback for complex tasks

### 4. Git Workflow
- Current branch: main
- Commit all changes before major refactoring
- Create deployment branch for testing
- Can revert if needed

## Success Criteria

1. ✅ Working Cloudflare Pages URL for frontend
2. ✅ Backend deployed and accessible
3. ✅ Deepgram Flux integration working with low latency
4. ✅ Session sharing functional (voice ↔ Telegram)
5. ✅ VAD properly tuned (no false positives)
6. ✅ Full voice conversation flow working end-to-end
7. ✅ Accessible from mobile devices

## Files to Modify

### Backend
- `backend/services/transcription.py` - Replace Faster Whisper with Deepgram
- `backend/.env` - Add Deepgram API key
- `backend/requirements.txt` - Remove faster-whisper, add deepgram-sdk
- `backend/main.py` - Ensure Workers compatibility

### Frontend
- `frontend/wrangler.toml` - Already configured
- No major changes needed

### New Files
- `wrangler.toml` for backend (if deploying to Workers)
- Deployment scripts

## Resources

- **Deepgram Docs:** https://developers.deepgram.com/docs/
- **Deepgram Flux:** https://developers.deepgram.com/docs/nova-2
- **Cloudflare Workers:** https://developers.cloudflare.com/workers/
- **Cloudflare Pages:** https://developers.cloudflare.com/pages/

## Previous Issues
- Earlier session encountered 404s on Cloudflare Pages after successful uploads
- Need to verify deployment status properly
- Ensure build output directory is correct (`dist/`)
