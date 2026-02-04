# VoiceClaw Final Debug - For Claude Code

**Date:** February 3, 2026, 10:14 PM EST  
**Issue:** VoiceClaw keeps connecting to `https://openclaw.ai/v1/chat/completions` instead of `https://clawd.bot/v1/chat/completions`

---

## Current Situation

**What Works:**
- ✅ Backend deploys successfully to Railway
- ✅ Deepgram transcription works (speech-to-text)
- ✅ OpenAI TTS works (text-to-speech)
- ✅ Health endpoint reports `gateway_url: "https://clawd.bot"`
- ✅ Frontend connects via WebSocket
- ✅ Audio playback works

**What Doesn't Work:**
- ❌ LLM requests fail with: `404 Client Error: Not Found for url: https://openclaw.ai/v1/chat/completions`
- ❌ User hears error message: "I'm sorry, I encountered a problem connecting to my language model 404 client error not found for URL openclaw.ai/v1/completions"

---

## What We've Tried (8 attempts over 3 hours)

1. ✅ Fixed variable name mismatch (CLAWD_* vs CLAWDBOT_*)
2. ✅ Updated config.py to accept both variable names
3. ✅ Prioritized CLAWD_GATEWAY_URL over CLAWDBOT_GATEWAY_URL
4. ✅ Added debug logging to see which URL is loaded
5. ✅ Removed `.env` file from repo (was hardcoded with old values)
6. ✅ Multiple redeployments to pick up new env vars
7. ❌ Still connecting to openclaw.ai somehow

---

## Your Mission

You have access to Carl's Chrome browser with Railway dashboard open. Your job is to find WHERE the `openclaw.ai` URL is coming from and fix it.

---

## Step 1: Check ALL Railway Environment Variables

**Action:** Go to Railway → VoiceClaw service → Variables tab

**Look for ANY variable containing:**
- `openclaw`
- `GATEWAY`
- `URL`
- `ENDPOINT`

**Document:**
```
Variable Name          | Value
-----------------------|------------------
CLAWD_GATEWAY_URL      | ???
CLAWDBOT_GATEWAY_URL   | ??? (should not exist)
LLM_API_ENDPOINT       | ??? (should not exist)
USE_CLAWDBOT           | ???
(any others)           | ???
```

**Expected Values:**
- `CLAWD_GATEWAY_URL` = `https://clawd.bot` (must include `https://`)
- `USE_CLAWDBOT` = `true`
- No other GATEWAY or ENDPOINT variables should exist

---

## Step 2: Check Railway Deployment Logs

**Action:** Railway → VoiceClaw → Logs → Deploy Logs (not Deploy Logs, the runtime logs)

**Search for:**
1. `🔍 DEBUG: CLAWDBOT_GATEWAY_URL=`
2. `🔍 DEBUG: CLAWD_GATEWAY_URL=`
3. `🔍 DEBUG: Using CLAWDBOT_GATEWAY_URL=`

These debug lines were added in the latest deployment. They should appear when the app starts.

**What to document:**
```
DEBUG: CLAWDBOT_GATEWAY_URL=???
DEBUG: CLAWD_GATEWAY_URL=???
DEBUG: Using CLAWDBOT_GATEWAY_URL=???
```

If these lines DON'T appear, the debug code didn't deploy or the print statements aren't being captured.

---

## Step 3: Check for Hidden Variables

Railway might have variables set at different levels:
- **Service variables** (what we've been checking)
- **Shared variables** (project-wide)
- **Environment variables** (production vs preview)

**Action:**
1. Check if there are "Shared Variables" in Railway
2. Check if "production" environment has different variables than what's shown
3. Look for any variable source that says "inherited" or "shared"

---

## Step 4: Verify Latest Deployment

**Action:** Railway → VoiceClaw → Deployments tab

**Check:**
- Is the LATEST deployment the one titled "Remove .env file from repo - use Railway env vars only"?
- Is it showing "Active" status?
- When was it deployed? (should be 1-2 minutes ago)

If it's not active yet, wait for it to finish deploying.

---

## Step 5: Test the Health Endpoint

**Action:** Open a new tab and go to:
```
https://voiceclaw-production.up.railway.app/health
```

**Check the JSON response:**
```json
{
  "clawdbot": {
    "gateway_url": "???"  <-- What is this?
  }
}
```

If it says `"https://clawd.bot"` but the runtime logs still show `openclaw.ai`, there's a caching issue.

---

## Step 6: Check Runtime Logs for LLM Errors

**Action:** Railway → Logs (runtime, not build logs)

**Filter or search for:** `ERROR:services.llm`

**Find the most recent error:**
```
ERROR:services.llm:LLM API request error: 404 Client Error: Not Found for url: https://???
```

**Document:** What URL is shown in the error?

---

## Step 7: Inspect the LLM Service Code

**Files to check:**
- `/root/clawd/projects/VoiceClaw/vocalis-fork/backend/config.py` (lines 27-32)
- `/root/clawd/projects/VoiceClaw/vocalis-fork/backend/services/llm.py` (initialization)

**Look for:**
1. Is `CLAWDBOT_GATEWAY_URL` being set correctly in config.py?
2. Is `get_llm_endpoint()` returning the right URL?
3. Is `LLMClient.__init__()` caching the old URL somehow?

---

## Possible Root Causes

### Theory 1: Railway Variable Not Actually Set
**Symptom:** CLAWD_GATEWAY_URL is visible in dashboard but not actually being passed to the app  
**Fix:** Delete and re-create the variable, redeploy

### Theory 2: Variable Has Wrong Format
**Symptom:** Value is `clawd.bot` instead of `https://clawd.bot`  
**Fix:** Add `https://` protocol to the value

### Theory 3: Old Deployment Still Active
**Symptom:** Latest code deployed but old process still running  
**Fix:** Manually restart the service or delete old deployments

### Theory 4: Shared/Inherited Variable Override
**Symptom:** CLAWDBOT_GATEWAY_URL exists at a higher level (shared variables)  
**Fix:** Find and delete the shared variable

### Theory 5: Code Not Reading Env Vars
**Symptom:** Debug print statements don't appear in logs  
**Fix:** Check if `print()` statements are being captured, or use `logger.info()` instead

---

## Recommended Fix Steps

If you find that `CLAWD_GATEWAY_URL` is set correctly in Railway but still not working:

**Option A: Force Environment Variable Priority**

Edit `/root/clawd/projects/VoiceClaw/vocalis-fork/backend/config.py`:

```python
# Line 27-32: Replace with this
import sys
_clawd_url = os.getenv("CLAWD_GATEWAY_URL")
print(f"🔍 CLAWD_GATEWAY_URL from env: {_clawd_url}", file=sys.stderr, flush=True)

if not _clawd_url:
    raise ValueError("CLAWD_GATEWAY_URL environment variable is required but not set!")

CLAWDBOT_GATEWAY_URL = _clawd_url
print(f"🔍 FINAL URL: {CLAWDBOT_GATEWAY_URL}", file=sys.stderr, flush=True)
```

This will:
1. Force the app to crash if CLAWD_GATEWAY_URL isn't set
2. Print debug info to stderr (more reliable than stdout)
3. Ignore CLAWDBOT_GATEWAY_URL entirely

**Option B: Hardcode for Testing**

Temporarily hardcode the URL to verify the code works:

```python
# Line 32 in config.py
CLAWDBOT_GATEWAY_URL = "https://clawd.bot"  # TEMPORARY HARDCODE FOR TESTING
```

If this works, the problem is definitely the environment variable not being read.

**Option C: Check dotenv Override**

Even though we deleted `.env`, check if Railway is somehow loading it from a cached layer:

1. In Railway, go to Settings → Clear Build Cache
2. Trigger a fresh deploy
3. Verify `.env` is not present in the deployed files

---

## Success Criteria

You'll know it's fixed when:

1. ✅ Railway logs show: `DEBUG: Using CLAWDBOT_GATEWAY_URL=https://clawd.bot`
2. ✅ No more 404 errors mentioning `openclaw.ai`
3. ✅ User can talk to VoiceClaw and get LLM responses (not error messages)
4. ✅ Frontend shows successful conversation flow

---

## If All Else Fails

**Last Resort:** Set EVERY possible variable in Railway:

```
CLAWD_GATEWAY_URL=https://clawd.bot
CLAWDBOT_GATEWAY_URL=https://clawd.bot
LLM_API_ENDPOINT=https://clawd.bot/v1/chat/completions
USE_CLAWDBOT=true
```

Then redeploy. One of them will work.

---

## Contact Atlas When Done

Report back with:
1. What you found in Railway variables
2. What the debug logs showed
3. What you changed
4. Whether it works now

Good luck! 🔍🔧
