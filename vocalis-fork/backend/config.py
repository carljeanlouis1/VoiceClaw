"""
VoiceClaw Configuration Module

Loads and provides access to configuration settings from environment variables
and the .env file.

Extended from Vocalis to support Clawdbot/OpenClaw gateway integration.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Any, Optional

# Load environment variables from .env file
# Explicitly look for .env in the project root (parent of backend/)
_project_root = Path(__file__).parent.parent
_env_path = _project_root / ".env"
load_dotenv(_env_path)

# =============================================================================
# Clawdbot/OpenClaw Gateway Configuration
# =============================================================================

# Gateway endpoint (default: local Clawdbot gateway)
# Accept both CLAWDBOT_* and CLAWD_* for backward compatibility
# Check both env vars and log what we find
_clawdbot_url = os.getenv("CLAWDBOT_GATEWAY_URL")
_clawd_url = os.getenv("CLAWD_GATEWAY_URL")
print(f"🔍 DEBUG: CLAWDBOT_GATEWAY_URL={_clawdbot_url}")
print(f"🔍 DEBUG: CLAWD_GATEWAY_URL={_clawd_url}")
CLAWDBOT_GATEWAY_URL = _clawd_url or _clawdbot_url or "http://127.0.0.1:18789"
print(f"🔍 DEBUG: Using CLAWDBOT_GATEWAY_URL={CLAWDBOT_GATEWAY_URL}")

# Gateway auth token (required for authenticated gateways)
CLAWDBOT_GATEWAY_TOKEN = os.getenv("CLAWDBOT_GATEWAY_TOKEN") or os.getenv("CLAWD_API_KEY") or ""

# Agent ID to route requests to (default: main)
CLAWDBOT_AGENT_ID = os.getenv("CLAWDBOT_AGENT_ID") or os.getenv("CLAWD_AGENT_ID") or "main"

# Session key for continuity with other channels (optional)
# If set, voice conversations share context with Telegram/WhatsApp
# If empty, each voice session is independent
CLAWDBOT_SESSION_KEY = os.getenv("CLAWDBOT_SESSION_KEY") or os.getenv("CLAWD_SESSION_KEY") or ""

# Whether to use Clawdbot gateway (vs direct LLM API)
USE_CLAWDBOT = os.getenv("USE_CLAWDBOT", "true").lower() in ("true", "1", "yes")

# =============================================================================
# LLM API Configuration (fallback when not using Clawdbot)
# =============================================================================

# Direct LLM API endpoint (used when USE_CLAWDBOT=false)
LLM_API_ENDPOINT = os.getenv("LLM_API_ENDPOINT", "http://127.0.0.1:1234/v1/chat/completions")

# API key for direct LLM access (OpenAI, Anthropic, etc.)
LLM_API_KEY = os.getenv("LLM_API_KEY", "")

# Model to use for LLM (default: Sonnet 4.5 for Clawdbot)
LLM_MODEL = os.getenv("LLM_MODEL", "anthropic/claude-sonnet-4-5")

# Computed: actual endpoint to use
def get_llm_endpoint() -> str:
    """Get the LLM endpoint based on configuration."""
    if USE_CLAWDBOT:
        return f"{CLAWDBOT_GATEWAY_URL}/v1/chat/completions"
    return LLM_API_ENDPOINT

# =============================================================================
# TTS Configuration
# =============================================================================

# TTS endpoint (default: OpenAI API)
TTS_API_ENDPOINT = os.getenv("TTS_API_ENDPOINT", "https://api.openai.com/v1/audio/speech")

# TTS API key (for OpenAI or compatible service)
TTS_API_KEY = os.getenv("TTS_API_KEY", os.getenv("OPENAI_API_KEY", ""))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")  # Alias for compatibility

TTS_MODEL = os.getenv("TTS_MODEL", "tts-1")
TTS_VOICE = os.getenv("TTS_VOICE", "onyx")  # OpenAI voices: alloy, echo, fable, onyx, nova, shimmer
TTS_FORMAT = os.getenv("TTS_FORMAT", "mp3")

# =============================================================================
# STT Configuration (Deepgram Flux)
# =============================================================================

# Deepgram API Key
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "")

# Deepgram Flux Model Configuration
DEEPGRAM_MODEL = os.getenv("DEEPGRAM_MODEL", "flux-general-en")
DEEPGRAM_ENCODING = os.getenv("DEEPGRAM_ENCODING", "linear16")
DEEPGRAM_SAMPLE_RATE = int(os.getenv("DEEPGRAM_SAMPLE_RATE", "16000"))

# Flux End-of-Turn Detection Parameters
DEEPGRAM_EOT_THRESHOLD = float(os.getenv("DEEPGRAM_EOT_THRESHOLD", "0.7"))
DEEPGRAM_EAGER_EOT_THRESHOLD = float(os.getenv("DEEPGRAM_EAGER_EOT_THRESHOLD", "0")) if os.getenv("DEEPGRAM_EAGER_EOT_THRESHOLD") else None
DEEPGRAM_EOT_TIMEOUT_MS = int(os.getenv("DEEPGRAM_EOT_TIMEOUT_MS", "5000"))

# Legacy Whisper support (for fallback)
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")
USE_DEEPGRAM = os.getenv("USE_DEEPGRAM", "true").lower() in ("true", "1", "yes")

# =============================================================================
# WebSocket Server Configuration
# =============================================================================

WEBSOCKET_HOST = os.getenv("WEBSOCKET_HOST", "0.0.0.0")
WEBSOCKET_PORT = int(os.getenv("WEBSOCKET_PORT", 8000))

# =============================================================================
# Audio Processing
# =============================================================================

VAD_THRESHOLD = float(os.getenv("VAD_THRESHOLD", 0.5))
VAD_BUFFER_SIZE = int(os.getenv("VAD_BUFFER_SIZE", 30))
AUDIO_SAMPLE_RATE = int(os.getenv("AUDIO_SAMPLE_RATE", 48000))

# =============================================================================
# Configuration Export
# =============================================================================

def get_config() -> Dict[str, Any]:
    """
    Returns all configuration settings as a dictionary.
    
    Returns:
        Dict[str, Any]: Dictionary containing all configuration settings
    """
    return {
        # Clawdbot settings
        "use_clawdbot": USE_CLAWDBOT,
        "clawdbot_gateway_url": CLAWDBOT_GATEWAY_URL,
        "clawdbot_agent_id": CLAWDBOT_AGENT_ID,
        "clawdbot_session_key": CLAWDBOT_SESSION_KEY,
        "has_clawdbot_token": bool(CLAWDBOT_GATEWAY_TOKEN),
        
        # LLM settings
        "llm_api_endpoint": get_llm_endpoint(),
        
        # TTS settings
        "tts_api_endpoint": TTS_API_ENDPOINT,
        "tts_model": TTS_MODEL,
        "tts_voice": TTS_VOICE,
        "tts_format": TTS_FORMAT,
        
        # STT settings
        "use_deepgram": USE_DEEPGRAM,
        "deepgram_model": DEEPGRAM_MODEL,
        "deepgram_encoding": DEEPGRAM_ENCODING,
        "deepgram_sample_rate": DEEPGRAM_SAMPLE_RATE,
        "deepgram_eot_threshold": DEEPGRAM_EOT_THRESHOLD,
        "deepgram_eager_eot_threshold": DEEPGRAM_EAGER_EOT_THRESHOLD,
        "deepgram_eot_timeout_ms": DEEPGRAM_EOT_TIMEOUT_MS,
        "has_deepgram_key": bool(DEEPGRAM_API_KEY),
        "whisper_model": WHISPER_MODEL,  # Legacy
        
        # Server settings
        "websocket_host": WEBSOCKET_HOST,
        "websocket_port": WEBSOCKET_PORT,
        
        # Audio settings
        "vad_threshold": VAD_THRESHOLD,
        "vad_buffer_size": VAD_BUFFER_SIZE,
        "audio_sample_rate": AUDIO_SAMPLE_RATE,
    }


def get_clawdbot_headers() -> Dict[str, str]:
    """
    Get HTTP headers for Clawdbot gateway requests.
    
    Returns:
        Dict[str, str]: Headers dict with auth and routing headers
    """
    headers = {
        "Content-Type": "application/json",
        "x-clawdbot-agent-id": CLAWDBOT_AGENT_ID,
    }
    
    if CLAWDBOT_GATEWAY_TOKEN:
        headers["Authorization"] = f"Bearer {CLAWDBOT_GATEWAY_TOKEN}"
    
    if CLAWDBOT_SESSION_KEY:
        headers["x-clawdbot-session-key"] = CLAWDBOT_SESSION_KEY
    
    return headers


def get_tts_headers() -> Dict[str, str]:
    """
    Get HTTP headers for TTS API requests.
    
    Returns:
        Dict[str, str]: Headers dict with auth headers
    """
    headers = {
        "Content-Type": "application/json",
    }
    
    if TTS_API_KEY:
        headers["Authorization"] = f"Bearer {TTS_API_KEY}"
    
    return headers
