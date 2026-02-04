# VoiceClaw Performance Optimization Guide

**Current latency:** 3-5 seconds  
**Target:** < 1 second perceived latency  
**For:** Claude Code to implement

---

## Problem Analysis

**Current flow (blocking):**
1. User speaks → Deepgram STT (300-500ms)
2. Text → Railway backend → Cloudflare tunnel → Clawdbot (100-200ms)
3. **WAIT for complete LLM response** ⚠️ (2-4 seconds)
4. Full response → OpenAI TTS (500-800ms)
5. **WAIT for complete audio** ⚠️ (200-400ms)
6. Play audio

**Total:** 3.1-6.9 seconds

---

## Solution: Streaming Pipeline

### 1. Stream LLM Tokens (Highest Impact)

**Current:** Backend waits for full completion from Clawdbot  
**New:** Stream tokens as they arrive

**Implementation in `backend/services/llm.py`:**

```python
async def stream_chat_completion(self, messages: List[Dict]) -> AsyncGenerator[str, None]:
    """Stream LLM response token by token"""
    payload = {
        "model": self.model_name,
        "messages": messages,
        "stream": True  # Enable streaming
    }
    
    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            f"{self.api_endpoint}",
            json=payload,
            headers=self.headers,
            timeout=30.0
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    chunk = line[6:]  # Remove "data: " prefix
                    if chunk == "[DONE]":
                        break
                    try:
                        data = json.loads(chunk)
                        if "choices" in data:
                            delta = data["choices"][0].get("delta", {})
                            if "content" in delta:
                                yield delta["content"]
                    except json.JSONDecodeError:
                        continue
```

### 2. Sentence Buffering (Send to TTS Early)

**Don't wait for full response** — send complete sentences to TTS immediately.

**Implementation in `backend/main.py`:**

```python
async def handle_conversation_stream(text_input: str):
    """Stream LLM response and convert to audio in chunks"""
    buffer = ""
    audio_chunks = []
    
    async for token in llm_service.stream_chat_completion(messages):
        buffer += token
        
        # Check if we have a complete sentence
        if buffer.endswith(('.', '!', '?', '\n')):
            sentence = buffer.strip()
            if sentence:
                # Send to TTS immediately (non-blocking)
                audio_chunk = await tts_service.synthesize(sentence)
                audio_chunks.append(audio_chunk)
                yield audio_chunk  # Stream to frontend
            buffer = ""
    
    # Handle any remaining text
    if buffer.strip():
        audio_chunk = await tts_service.synthesize(buffer)
        yield audio_chunk
```

### 3. Frontend Audio Streaming

**Current:** Wait for full audio file  
**New:** Play chunks as they arrive

**Update `frontend/src/lib/audio.js`:**

```javascript
class StreamingAudioPlayer {
  constructor() {
    this.audioContext = new AudioContext();
    this.queue = [];
    this.isPlaying = false;
  }

  async addChunk(base64Audio) {
    // Decode base64 to ArrayBuffer
    const binaryString = atob(base64Audio);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }
    
    // Decode audio
    const audioBuffer = await this.audioContext.decodeAudioData(bytes.buffer);
    this.queue.push(audioBuffer);
    
    // Start playing if not already
    if (!this.isPlaying) {
      this.playNext();
    }
  }

  playNext() {
    if (this.queue.length === 0) {
      this.isPlaying = false;
      return;
    }

    this.isPlaying = true;
    const buffer = this.queue.shift();
    const source = this.audioContext.createBufferSource();
    source.buffer = buffer;
    source.connect(this.audioContext.destination);
    
    // Play next chunk when this one ends
    source.onended = () => this.playNext();
    source.start();
  }
}

// Usage in WebSocket handler
const player = new StreamingAudioPlayer();

websocket.on('audio_chunk', (chunk) => {
  player.addChunk(chunk.audio);
});
```

### 4. WebSocket Protocol Update

**Current:** Single response message  
**New:** Chunked streaming

**Backend WebSocket handler:**

```python
@app.websocket("/ws/voice")
async def websocket_voice(websocket: WebSocket):
    await websocket.accept()
    
    try:
        while True:
            data = await websocket.receive_json()
            
            if data["type"] == "audio":
                # Transcribe
                text = await stt_service.transcribe(data["audio"])
                
                # Stream response
                async for audio_chunk in handle_conversation_stream(text):
                    await websocket.send_json({
                        "type": "audio_chunk",
                        "audio": audio_chunk,
                        "done": False
                    })
                
                # Signal completion
                await websocket.send_json({
                    "type": "audio_chunk",
                    "done": True
                })
                
    except WebSocketDisconnect:
        logger.info("Client disconnected")
```

---

## Optimization Priorities

### Phase 1: Quick Wins (30 min implementation)
1. ✅ Enable streaming on Clawdbot API call
2. ✅ Add sentence buffering
3. ✅ Send first sentence to TTS ASAP

**Expected improvement:** 3-5s → 1-2s perceived latency

### Phase 2: Full Streaming (2 hours)
1. ✅ Implement chunked audio streaming
2. ✅ Update WebSocket protocol
3. ✅ Frontend progressive playback

**Expected improvement:** 1-2s → 0.5-1s perceived latency

### Phase 3: Advanced (if needed)
1. Parallel TTS (multiple sentences at once)
2. Prefetch audio (predict likely responses)
3. Local TTS model (eliminate API call)

---

## Additional Optimizations

### A. Reduce Token Count
**Current system prompt is probably huge** (SOUL.md + AGENTS.md + USER.md + TOOLS.md).

For voice mode, use a **minimal system prompt:**

```python
VOICE_MODE_SYSTEM_PROMPT = """You are Atlas, Carl's AI assistant.
Keep responses conversational and concise for voice.
You have access to his projects, calendar, and tools."""
```

**Expected improvement:** 200-500ms faster LLM response

### B. Use Faster Model for Voice
Switch to `claude-sonnet-4-5` instead of `opus` for voice interactions:

```python
if interaction_mode == "voice":
    model = "claude-sonnet-4-5"  # Faster, still excellent
else:
    model = "claude-opus-4-5"  # Deep thinking
```

**Expected improvement:** 300-800ms faster

### C. Optimize Cloudflare Tunnel
**Temporary tunnel:** High latency, random routing  
**Permanent tunnel:** Optimized routing, persistent connection

```bash
# Create permanent tunnel
cloudflared tunnel create voiceclaw-gateway
cloudflared tunnel route dns voiceclaw-gateway gateway.carlclaw.dev
cloudflared tunnel run voiceclaw-gateway
```

**Expected improvement:** 100-300ms faster

### D. Parallel Processing
Run STT, LLM, and TTS in parallel where possible:

```python
async def handle_audio_input(audio):
    # Start transcription
    text_task = asyncio.create_task(stt_service.transcribe(audio))
    
    # While transcribing, prepare context (if needed)
    context = await get_recent_context()
    
    # Wait for transcription
    text = await text_task
    
    # Stream LLM + TTS in parallel
    async for audio_chunk in stream_response(text, context):
        yield audio_chunk
```

---

## Testing Latency

Add timing logs to measure each step:

```python
import time

async def handle_conversation(text):
    t0 = time.time()
    
    # LLM call
    t1 = time.time()
    response = await llm.chat_completion(messages)
    logger.info(f"LLM took: {time.time() - t1:.2f}s")
    
    # TTS
    t2 = time.time()
    audio = await tts.synthesize(response)
    logger.info(f"TTS took: {time.time() - t2:.2f}s")
    
    logger.info(f"Total latency: {time.time() - t0:.2f}s")
    return audio
```

---

## Expected Results

**Current (no streaming):**
- User stops speaking: 0s
- Transcription complete: +0.5s
- LLM response complete: +3.5s
- TTS complete: +4.5s
- **User hears first word: 4.5s**

**After Phase 1 (sentence streaming):**
- User stops speaking: 0s
- Transcription complete: +0.5s
- First sentence generated: +1.2s
- First sentence TTS: +1.5s
- **User hears first word: 1.5s** ⚡️

**After Phase 2 (full streaming):**
- User stops speaking: 0s
- Transcription complete: +0.5s
- First tokens arrive: +0.8s
- First audio chunk: +1.0s
- **User hears first word: 1.0s** ⚡️⚡️

---

## Implementation Order for Claude Code

1. **Start here:** Add streaming to LLM client (`services/llm.py`)
2. **Then:** Implement sentence buffering in conversation handler
3. **Test:** Verify first sentence plays faster
4. **Next:** Add WebSocket chunking
5. **Finally:** Update frontend for progressive playback

**Estimated total time:** 2-3 hours for full implementation

---

## Questions for Carl

1. Is the Cloudflare tunnel temporary or permanent?
2. What model is Clawdbot using? (Sonnet vs Opus)
3. Do you want to prioritize speed over response quality for voice?
4. Should we switch to a local TTS model (faster but lower quality)?

---

Good luck, Claude Code! This will make VoiceClaw feel MUCH snappier. 🚀
