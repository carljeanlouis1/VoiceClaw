# VoiceClaw URGENT FIX - Claude Code Checklist

**Problem:** Backend keeps connecting to `openclaw.ai` instead of `clawd.bot`

**You have:** Chrome browser access to Railway dashboard

---

## DO THESE STEPS IN ORDER (5 minutes max)

### Step 1: Check Railway Variables (1 min)
Railway → VoiceClaw → Variables tab

**Look for these EXACT variable names:**
- [ ] `CLAWD_GATEWAY_URL` - what is the value? _________________
- [ ] `CLAWDBOT_GATEWAY_URL` - does this exist? YES/NO: _____
- [ ] `LLM_API_ENDPOINT` - does this exist? YES/NO: _____

**CRITICAL:** If `CLAWD_GATEWAY_URL` value is NOT exactly `https://clawd.bot` (with https://), that's the bug!

### Step 2: Check Latest Deployment (30 sec)
Railway → VoiceClaw → Deployments tab

- [ ] Is "Remove .env file from repo" deployment ACTIVE?
- [ ] Deployed time: _____________ (should be last 5 min)

### Step 3: Check Startup Logs (1 min)
Railway → Logs → Search for "DEBUG"

**Find these lines:**
```
🔍 DEBUG: CLAWD_GATEWAY_URL=???
🔍 DEBUG: Using CLAWDBOT_GATEWAY_URL=???
```

**What do they say?**
- DEBUG: CLAWD_GATEWAY_URL= _________________
- DEBUG: Using CLAWDBOT_GATEWAY_URL= _________________

**If you DON'T see these lines:** The debug code didn't deploy. Force redeploy.

### Step 4: Check Error Logs (30 sec)
Railway → Logs → Search for "ERROR:services.llm"

**Most recent error says:**
```
ERROR:services.llm:LLM API request error: 404 Client Error: Not Found for url: https://___________
```

Fill in the URL: _________________

---

## FIXES (try in order)

### Fix A: Wrong URL Format
**IF:** `CLAWD_GATEWAY_URL` is set to `clawd.bot` (no https://)  
**THEN:** 
1. Edit the variable to: `https://clawd.bot`
2. Click "Deploy" button
3. Wait 60 seconds
4. Test VoiceClaw

### Fix B: Variable Not Being Read
**IF:** Debug logs show `CLAWD_GATEWAY_URL=None` or blank  
**THEN:**
1. Delete `CLAWD_GATEWAY_URL` variable completely
2. Re-create it with value: `https://clawd.bot`
3. Click "Deploy" button
4. Wait 60 seconds
5. Test VoiceClaw

### Fix C: Wrong Variable Name
**IF:** You found `CLAWDBOT_GATEWAY_URL` exists in Railway  
**THEN:**
1. Change its value to: `https://clawd.bot`
2. Make sure `CLAWD_GATEWAY_URL` also = `https://clawd.bot`
3. Click "Deploy" button
4. Wait 60 seconds
5. Test VoiceClaw

### Fix D: Hardcode for Testing
**IF:** Nothing above worked  
**THEN:**
1. Edit `/root/clawd/projects/VoiceClaw/vocalis-fork/backend/config.py`
2. Find line ~32: `CLAWDBOT_GATEWAY_URL = _clawd_url or _clawdbot_url or...`
3. Replace entire line with: `CLAWDBOT_GATEWAY_URL = "https://clawd.bot"`
4. Save, commit, push to GitHub
5. Wait 60 seconds for Railway to deploy
6. Test VoiceClaw

---

## SUCCESS CHECK

VoiceClaw is fixed when:
- ✅ No more "openclaw.ai" in error logs
- ✅ User can speak and get REAL responses (not error messages)
- ✅ Logs show: `Initialized LLM Client: endpoint=https://clawd.bot/v1/chat/completions`

---

## Report Back

Tell Carl:
1. What variable values you found in Railway
2. Which fix you applied
3. Whether it works now

**MOST LIKELY FIX:** Variable value is missing `https://` or variable isn't being read at all.
