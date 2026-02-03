"""
VoiceClaw Configuration Module

Loads and provides access to configuration settings from environment variables
and the .env file.

Extended from Vocalis to support Clawdbot/OpenClaw gateway integration.
"""

import os
from dotenv import load_dotenv
from typing import Dict, Any, Optional

# Load environment variables from .env file
load_dotenv()

# =============================================================================
# Clawdbot/OpenClaw Gateway Configuration
# =============================================================================

# Gateway endpoint (default: local Clawdbot gateway)
CLAWDBOT_GATEWAY_URL = os.getenv("CLAWDBOT_GATEWAY_URL", "http://127.0.0.1:18789")

# Gateway auth token (required for authenticated gateways)
CLAWDBOT_GATEWAY_TOKEN = os.getenv("CLAWDBOT_GATEWAY_TOKEN", "")

# Agent ID to route requests to (default: main)
CLAWDBOT_AGENT_ID = os.getenv("CLAWDBOT_AGENT_ID", "main")

# Session key for continuity with other channels (optional)
# If set, voice conversations share context with Telegram/WhatsApp
# If empty, each voice session is independent
CLAWDBOT_SESSION_KEY = os.getenv("CLAWDBOT_SESSION_KEY", "")

# Whether to use Clawdbot gateway (vs direct LLM API)
USE_CLAWDBOT = os.getenv("USE_CLAWDBOT", "true").lower() in ("true", "1", "yes")

# =============================================================================
# LLM API Configuration (fallback when not using Clawdbot)
# =============================================================================

# Direct LLM API endpoint (used when USE_CLAWDBOT=false)
LLM_API_ENDPOINT = os.getenv("LLM_API_ENDPOINT", "http://127.0.0.1:1234/v1/chat/completions")

# API key for direct LLM access (OpenAI, Anthropic, etc.)
LLM_API_KEY = os.getenv("LLM_API_KEY", "")

# Computed: actual endpoint to use
def get_llm_endpoint() -> str:
    """Get the LLM endpoint based on configuration."""
    if USE_CLAWDBOT:
        return f"{CLAWDBOT_GATEWAY_URL}/v1/chat/completions"
    return LLM_API_ENDPOINT

# =============================================================================
# TTS Configuration
# =============================================================================

TTS_API_ENDPOINT = os.getenv("TTS_API_ENDPOINT", "http://localhost:5005/v1/audio/speech")
TTS_MODEL = os.getenv("TTS_MODEL", "tts-1")
TTS_VOICE = os.getenv("TTS_VOICE", "tara")
TTS_FORMAT = os.getenv("TTS_FORMAT", "wav")

# =============================================================================
# Whisper STT Configuration
# =============================================================================

WHISPER_MODEL = os.getenv("WHISPER_MODEL", "tiny.en")

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
        "whisper_model": WHISPER_MODEL,
        
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
