# Quick Start for Claude Code

## What's Happening
VoiceClaw (FastAPI voice assistant) deploys to Railway but returns 502 errors despite showing "Online". We've tried 8 fixes over 2 hours.

## Files to Read First
1. `/root/clawd/projects/VoiceClaw/RAILWAY_TROUBLESHOOTING_SUMMARY.md` - Full debugging history
2. `/root/clawd/projects/VoiceClaw/vocalis-fork/backend/main.py` - App entry point
3. `/root/clawd/projects/VoiceClaw/vocalis-fork/backend/config.py` - Environment config
4. `/root/clawd/projects/VoiceClaw/vocalis-fork/backend/requirements.txt` - Dependencies
5. `/root/clawd/projects/VoiceClaw/vocalis-fork/backend/Procfile` - Railway start command

## The 502 Problem
- Railway dashboard says "Online"
- `curl https://voiceclaw-production.up.railway.app/health` returns 502
- Logs show uvicorn starts but crashes during app initialization

## Most Likely Culprits
1. **Missing env var crashes startup** - Check if DEEPGRAM_API_KEY is required in `services/transcription.py`
2. **Port binding issue** - Procfile uses `$PORT` but does FastAPI actually bind to it?
3. **Import error we missed** - There might be another hidden import dependency
4. **Startup timeout** - App takes too long to initialize, Railway kills it

## Quick Test
Run locally to see if code works at all:
```bash
cd /root/clawd/projects/VoiceClaw/vocalis-fork/backend
export DEEPGRAM_API_KEY="dummy"
export TTS_API_KEY="dummy"
export PORT=8000
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

If it works locally, the problem is Railway-specific (env vars, port binding, etc).

## Your Mission
Find why Railway returns 502 when the app shows "Online". Focus on startup logic in `main.py` and environment variable handling in `config.py` and service constructors.

Latest logs are in the troubleshooting summary doc.

Good luck! 🔍
