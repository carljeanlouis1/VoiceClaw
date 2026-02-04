# VoiceClaw Railway Deployment - Troubleshooting Summary

**Date:** February 3, 2026  
**Duration:** ~2 hours (8 deployment attempts)  
**Current Status:** Build succeeds, Railway shows "Online", but app returns 502 errors  
**Platform:** Railway.app  
**Deployment URL:** https://voiceclaw-production.up.railway.app  

---

## Project Structure

**Backend Location:** `/root/clawd/projects/VoiceClaw/vocalis-fork/backend/`

**Stack:**
- FastAPI
- Uvicorn web server
- Python 3.11.14
- WebSocket for real-time audio
- Deepgram API for transcription (no local models)

**Entry Point:** `main.py` → FastAPI app  
**Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT` (via Procfile)

---

## Deployment Attempts & Errors

### Attempt 1: Heavy Dependencies
**Error:** Build took 6+ minutes, crashed on startup  
**Issue:** `transformers` and `faster-whisper` packages were downloading large models  
**Fix:** Removed heavy dependencies  

### Attempt 2: Python Version Issues  
**Error:** `ModuleNotFoundError` for various packages  
**Issue:** Python 3.13 missing prebuilt binaries  
**Fix:** Downgraded to Python 3.11.14 via `runtime.txt`  

### Attempt 3: Import Errors at Module Level
**Error:** Crash during import of WhisperTranscriber  
**Issue:** Heavy imports happening at module load time  
**Fix:** Moved to lazy loading in conditional blocks  

### Attempt 4: Relative Import Issues
**Error:** `ImportError` on module imports  
**Issue:** Mixed relative (`from ..services`) and absolute imports  
**Fix:** Changed all imports to absolute (`from services.transcription`)  

### Attempt 5: Missing Deepgram SDK
**Error:** `ModuleNotFoundError: No module named 'deepgram'`  
**Issue:** `transcription_deepgram.py` trying to import Deepgram SDK  
**Fix:** Replaced with API-based transcription (HTTP calls only)  

### Attempt 6-8: uvicorn Crash Pattern
**Error:** Application starts, shows "Online", but returns 502  
**Logs Show:**
```
File "/app/.venv/lib/python3.11/site-packages/uvicorn/server.py", line 77, in _serve
    config.load()
File "/app/.venv/lib/python3.11/site-packages/uvicorn/config.py", line 435, in load
    self.loaded_app = import_from_string(self.app)
...
[Stack trace continues but app crashes]
```

**Pattern:** Build succeeds, pip installs complete, uvicorn starts but crashes during app initialization  

---

## Current Code State

### requirements.txt (Minimal)
```txt
fastapi==0.115.6
uvicorn[standard]==0.34.0
websockets==14.1
python-multipart==0.0.20
pydantic==2.10.4
numpy==2.2.1
httpx==0.28.1
python-dotenv==1.0.1
```

### Procfile
```
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

### runtime.txt
```
python-3.11.14
```

### Port Binding
Railway provides `PORT` environment variable, which should be used by uvicorn.  
Current Procfile uses `$PORT` correctly.

---

## Suspected Issues

### 1. Port Binding Problem
**Theory:** Railway expects the app to bind to a specific port, but something is misconfigured  
**Evidence:** 502 errors indicate proxy can't reach the app  
**Check:** Does FastAPI/uvicorn actually bind to `0.0.0.0:$PORT`?  

### 2. Missing Environment Variables
**Theory:** App crashes because required env vars aren't set  
**Evidence:** Config tries to load DEEPGRAM_API_KEY, TTS_API_KEY, etc.  
**Check:** Are all required env vars set in Railway dashboard?  

**Required Variables:**
- `DEEPGRAM_API_KEY` - For transcription
- `TTS_API_KEY` or `OPENAI_API_KEY` - For text-to-speech
- `PORT` - Should be auto-provided by Railway

### 3. Import Errors Still Present
**Theory:** There's still a module we're trying to import that doesn't exist  
**Evidence:** Previous attempts had hidden import errors  
**Check:** Do all services import cleanly? Any circular imports?  

### 4. Startup Timeout
**Theory:** App takes too long to initialize, Railway kills it  
**Evidence:** Vision service tries to load models (but marked optional)  
**Check:** Remove all heavy initialization from startup  

### 5. Working Directory Issues
**Theory:** App expects to run from a specific directory  
**Evidence:** Config tries to find `.env` file: `_project_root = Path(__file__).parent.parent`  
**Check:** Does Railway run from `/backend/` or `/vocalis-fork/`?  

---

## Key Files to Review

### main.py (Startup Logic)
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load configuration
    cfg = config.get_config()
    
    # Initialize transcription service (Deepgram API)
    logger.info("Initializing Deepgram API transcription")
    
    if not cfg.get("has_deepgram_key"):
        logger.error("⚠️  DEEPGRAM_API_KEY not set! Transcription will fail.")
    
    transcription_service = WhisperTranscriber(
        sample_rate=cfg["audio_sample_rate"]
    )
    # ... more initialization
```

**Potential Issue:** If `has_deepgram_key` is False, does initialization fail?  

### config.py (Environment Loading)
```python
from dotenv import load_dotenv

_project_root = Path(__file__).parent.parent
_env_path = _project_root / ".env"
load_dotenv(_env_path)
```

**Potential Issue:** `.env` file doesn't exist in Railway deployment - all vars should be set in dashboard  

### transcription.py (Deepgram API)
```python
def __init__(self, ...):
    self.api_key = os.getenv("DEEPGRAM_API_KEY")
    
    if not self.api_key:
        raise ValueError("DEEPGRAM_API_KEY environment variable is required")
```

**Potential Issue:** If DEEPGRAM_API_KEY isn't set, this raises an exception during startup  

---

## Recommended Debugging Steps

### Step 1: Test Locally
```bash
cd /root/clawd/projects/VoiceClaw/vocalis-fork/backend
export DEEPGRAM_API_KEY="test_key"
export TTS_API_KEY="test_key"
export PORT=8000
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

If it works locally, the issue is Railway-specific.

### Step 2: Check Railway Environment Variables
Verify these are set in Railway dashboard:
- DEEPGRAM_API_KEY
- TTS_API_KEY (or OPENAI_API_KEY)
- PORT should be auto-set by Railway

### Step 3: Make API Keys Optional for Startup
Change `transcription.py` to allow missing keys:
```python
if not self.api_key:
    logger.warning("DEEPGRAM_API_KEY not set - transcription will fail at runtime")
    # Don't raise exception, allow app to start
```

### Step 4: Add Health Check Endpoint
Ensure `/health` endpoint doesn't require services to be initialized:
```python
@app.get("/health")
async def health_check():
    return {"status": "ok"}  # Don't check services
```

### Step 5: Minimal Test Deploy
Create a bare-bones FastAPI app to confirm Railway works:
```python
from fastapi import FastAPI
app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}
```

If this works, incrementally add complexity.

---

## Latest Error Logs

From Railway (Feb 3, 2026 21:06:05 EST):
```
File "/app/.venv/lib/python3.11/site-packages/uvicorn/server.py", line 77, in _serve
    config.load()
File "/app/.venv/lib/python3.11/site-packages/uvicorn/config.py", line 435, in load
    self.loaded_app = import_from_string(self.app)
File "<frozen importlib._bootstrap>", line 1204, in _gcd_import
File "<frozen importlib._bootstrap>", line 1176, in _find_and_load
File "<frozen importlib._bootstrap>", line 1147, in _find_and_load_unlocked
File "<frozen importlib._bootstrap>", line 690, in _load_unlocked
File "<frozen importlib._bootstrap_external>", line 940, in exec_module
File "/app/main.py", line 19, in <module>
    from services.transcription_deepgram import DeepgramTranscriber

ModuleNotFoundError: No module named 'deepgram'
```

**Latest Fix Applied:** Changed main.py to import from `services.transcription` instead  

---

## Next Steps for Claude Code

1. **Review main.py startup logic** - Are there any imports or initializations that could fail?
2. **Check config.py** - Does it handle missing .env file gracefully?
3. **Review transcription.py** - Does it raise exceptions if API key is missing?
4. **Test port binding** - Is uvicorn actually binding to the PORT variable?
5. **Check for circular imports** - Do any modules import each other?
6. **Verify Railway setup** - Are all necessary env vars configured?

---

## Railway Configuration

**Project ID:** 8d594d2d-b197-4d06-a4e4-adb62734fd3d  
**Service ID:** 5bc6bf5a-2ec2-412b-a3ec-532942426d0c  
**Environment:** production (b233c983-b6b5-4d1c-a79a-68853b99809d)  
**Region:** us-west2  
**Runtime:** Python 3.11.14  
**Build Command:** Auto-detected (pip install)  
**Start Command:** From Procfile  

**GitHub Integration:** Auto-deploys from `main` branch  
**Repo:** https://github.com/carljeanlouis1/VoiceClaw  

---

## Contact

If you find the root cause, document it here and push the fix to GitHub. Railway will auto-deploy.

Good luck! 🚀
