# VoiceClaw Research - Phase 1 Findings

## Executive Summary

**Good news:** The integration is *much simpler* than originally expected.

Clawdbot already has an OpenAI-compatible HTTP endpoint (`/v1/chat/completions`) that:
- Supports streaming (SSE)
- Routes to the same session as Telegram/WhatsApp
- Handles tool calls through the normal gateway flow

Vocalis already speaks OpenAI format. We just need to:
1. Enable Clawdbot's endpoint
2. Add auth header support to Vocalis
3. Add session routing headers for true continuity

## Key Discovery: Clawdbot's OpenAI-Compatible Endpoint

**Documentation:** `/usr/lib/node_modules/clawdbot/docs/gateway/openai-http-api.md`

### Endpoint Details
```
POST /v1/chat/completions
Host: localhost:18789
Authorization: Bearer <CLAWDBOT_GATEWAY_TOKEN>
Content-Type: application/json
x-clawdbot-agent-id: main
x-clawdbot-session-key: <session-key>  # Optional: for session routing
```

### Enabling It
Add to `~/.clawdbot/clawdbot.json`:
```json
{
  "gateway": {
    "http": {
      "endpoints": {
        "chatCompletions": { "enabled": true }
      }
    }
  }
}
```

### Session Behavior
- **Default:** Stateless (new session per request)
- **With `user` field:** Derives stable session key from user string
- **With `x-clawdbot-session-key` header:** Explicit session routing

For true continuity with Telegram, we use the session-key header.

## Vocalis Architecture Analysis

**Repo:** https://github.com/Lex-au/Vocalis

### Relevant Files
- `backend/config.py` — Configuration (endpoints, models)
- `backend/services/llm.py` — LLM client (OpenAI format)
- `backend/routes/websocket.py` — WebSocket handler

### Current LLM Integration
```python
# backend/services/llm.py
class LLMClient:
    def __init__(
        self,
        api_endpoint: str = "http://127.0.0.1:1234/v1/chat/completions",
        model: str = "default",
        ...
    ):
        self.api_endpoint = api_endpoint
        # Manages local conversation_history
```

### What's Missing for Clawdbot Integration
1. **No auth header support** — needs `Authorization: Bearer <token>`
2. **Local history management** — we want Clawdbot sessions as source of truth
3. **No session routing** — needs `x-clawdbot-session-key` header

## Integration Approaches

### Approach A: Minimal (Point & Auth)
**Changes:**
- Add `LLM_API_KEY` env var
- Modify `llm.py` to send auth header
- Point endpoint to Clawdbot

**Result:** Voice works through Clawdbot, but starts fresh session each time. No Telegram continuity.

### Approach B: Full Gateway Integration (Recommended)
**Changes:**
- Everything from Approach A
- Add session key configuration/header
- Optionally: disable Vocalis local history, let Clawdbot manage context
- Add session discovery (list available sessions, pick main)

**Result:** True "same brain" — voice conversations share context with Telegram.

### Approach C: Hybrid with Session Sync (Future Enhancement)
**Changes:**
- Full gateway integration
- Bidirectional sync: fetch session history on connect, push voice to session
- Real-time tool call display in UI

**Result:** Premium experience — see what your agent is doing.

## Clawdbot Gateway Protocol Reference

### WebSocket Protocol (Full Control)
For advanced features (tool call streaming, real-time events):
- Transport: WebSocket, JSON frames
- First frame: `connect` handshake
- Frames: `req`, `res`, `event`
- Docs: `/usr/lib/node_modules/clawdbot/docs/gateway/protocol.md`

### OpenResponses API (Alternative)
More powerful than chat completions, supports:
- Item-based inputs
- Client tool definitions
- Function call outputs
- File/image inputs
- Docs: `/usr/lib/node_modules/clawdbot/docs/gateway/openresponses-http-api.md`

## Technical Challenges

### 1. Session Key Discovery
How does voice client know which session to route to?
- **Option A:** Configure static session key
- **Option B:** List sessions via API, let user pick
- **Option C:** Use "main" agent session (most common case)

### 2. Tool Calls During Voice
When agent makes tool calls mid-conversation:
- Clawdbot handles this seamlessly
- Response streams, may pause during tool execution
- Need graceful handling in voice flow (don't cut off, show loading)

### 3. Barge-In + Tool Calls
What if user interrupts during a tool call?
- Tool call completes but response discarded
- Start new transcription → new request
- Agent may or may not know about interrupted context

### 4. STT/TTS Latency Budget
Voice flow timing:
- User speaks → Whisper transcribes (~200-500ms with Faster Whisper)
- Transcript → Clawdbot gateway → LLM → tool calls → response
- Response → TTS (~200-300ms for first chunk with streaming)

Total: ~1-2 seconds typical, more with tool calls.

## Implementation Plan

### Phase 1: Enable & Test (Current)
- [x] Research Clawdbot gateway protocol
- [x] Analyze Vocalis codebase
- [ ] Enable chat completions endpoint on Clawdbot
- [ ] Test with curl to verify endpoint works

### Phase 2: Minimal Integration
- [ ] Fork Vocalis
- [ ] Add auth header support to `llm.py`
- [ ] Test voice → Clawdbot flow

### Phase 3: Session Routing
- [ ] Add session key configuration
- [ ] Add `x-clawdbot-session-key` header
- [ ] Test session continuity with Telegram

### Phase 4: UX Polish
- [ ] Show "thinking" state during tool calls
- [ ] Display what tools are being called
- [ ] Session picker in UI

### Phase 5: Release
- [ ] Comprehensive README
- [ ] Setup guide
- [ ] Video walkthrough
- [ ] Community release

## Files Created

```
/root/clawd/projects/VoiceClaw/
├── README.md               # Project overview
├── docs/
│   └── RESEARCH.md         # This file
├── proxy/                  # (May not need)
├── vocalis-fork/           # Modified Vocalis
└── scripts/                # Utility scripts
```

## Next Steps

1. Enable Clawdbot's chat completions endpoint
2. Test with curl to confirm it works
3. Fork Vocalis and add auth header support
4. Test end-to-end voice flow

---
*Research completed: 2026-02-03*
*Phase 1 status: 90% complete (pending endpoint test)*
