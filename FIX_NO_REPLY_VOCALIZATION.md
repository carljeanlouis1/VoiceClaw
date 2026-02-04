# Fix: NO_REPLY Vocalization Bug

**Issue:** When Atlas sends "NO_REPLY" to indicate silence, VoiceClaw vocalizes it as "no response from Clawdbot" instead of staying silent.

**Root Cause:** The WebSocket handler doesn't filter "NO_REPLY" before sending to TTS.

**Priority:** Medium (annoying but not breaking)

---

## Fix Location

**File:** `/root/clawd/projects/VoiceClaw/vocalis-fork/backend/main.py`

**Function:** WebSocket handler (around the conversation processing section)

---

## The Fix

### Find this section (approximately line 150-200):

```python
# After getting LLM response
response = await llm_service.chat_completion(messages)

# Send to TTS
audio = await tts_service.synthesize(response)
await websocket.send_json({
    "type": "audio",
    "audio": audio
})
```

### Replace with:

```python
# After getting LLM response
response = await llm_service.chat_completion(messages)

# Check for NO_REPLY marker
if response.strip() == "NO_REPLY":
    # Don't vocalize - just continue listening
    continue

# Send to TTS (only if not NO_REPLY)
audio = await tts_service.synthesize(response)
await websocket.send_json({
    "type": "audio",
    "audio": audio
})
```

---

## Alternative: More Robust Check

If "NO_REPLY" might have variations, use:

```python
# Check for NO_REPLY marker (case-insensitive, whitespace-tolerant)
if "NO_REPLY" in response.upper().replace(" ", ""):
    # Don't vocalize - just continue listening
    continue
```

---

## Testing

1. Start VoiceClaw
2. Say something
3. Go silent/mute for 30+ seconds
4. You should hear **nothing** (not "no response from Clawdbot")
5. Speak again - should respond normally

---

## What This Does

- Catches "NO_REPLY" before TTS processing
- Skips audio generation and transmission
- Continues listening for next user input
- Prevents unwanted vocalization

---

**Estimated fix time:** 2 minutes

**Impact:** Eliminates annoying "no response" vocalizations during silence
