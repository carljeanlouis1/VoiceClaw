"""
Speech-to-Text Transcription Service using Deepgram Flux

Replaces Faster Whisper with Deepgram's Flux model for ultra-low latency
conversational AI transcription.
"""

import logging
import asyncio
from typing import Dict, Any, Optional, Callable
from deepgram import AsyncDeepgramClient
from deepgram.core.events import EventType
from deepgram.extensions.types.sockets import ListenV2SocketClientResponse
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DeepgramTranscriber:
    """
    Speech-to-Text service using Deepgram Flux.
    
    This class handles real-time transcription of speech audio using Deepgram's
    Flux model, which is optimized for conversational AI with ultra-low latency
    (~260ms end-of-turn detection) and built-in turn detection.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "flux-general-en",
        encoding: str = "linear16",
        sample_rate: int = 16000,
        eot_threshold: float = 0.7,
        eager_eot_threshold: Optional[float] = None,
        eot_timeout_ms: int = 5000
    ):
        """
        Initialize the Deepgram Flux transcription service.
        
        Args:
            api_key: Deepgram API key (or set DEEPGRAM_API_KEY env var)
            model: Deepgram model to use (flux-general-en recommended)
            encoding: Audio encoding (linear16, opus, etc.)
            sample_rate: Audio sample rate in Hz (16000 recommended for Flux)
            eot_threshold: End-of-turn detection confidence (0.5-0.9, default 0.7)
            eager_eot_threshold: Early turn detection for faster LLM responses (0.3-0.9, optional)
            eot_timeout_ms: Max silence before forcing end-of-turn (500-10000, default 5000)
        """
        self.api_key = api_key or os.getenv("DEEPGRAM_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Deepgram API key required. Set DEEPGRAM_API_KEY environment variable "
                "or pass api_key parameter."
            )
        
        self.model = model
        self.encoding = encoding
        self.sample_rate = sample_rate
        self.eot_threshold = eot_threshold
        self.eager_eot_threshold = eager_eot_threshold
        self.eot_timeout_ms = eot_timeout_ms
        
        # Initialize client
        self.client = AsyncDeepgramClient(api_key=self.api_key)
        
        # Connection state
        self.connection = None
        self.is_processing = False
        self._transcript_callback = None
        self._turn_complete_callback = None
        
        logger.info(
            f"Initialized Deepgram Flux Transcriber: model={model}, "
            f"encoding={encoding}, sample_rate={sample_rate}Hz, "
            f"eot_threshold={eot_threshold}"
        )
    
    async def connect(
        self,
        on_transcript: Optional[Callable] = None,
        on_turn_complete: Optional[Callable] = None
    ):
        """
        Establish WebSocket connection to Deepgram Flux.
        
        Args:
            on_transcript: Callback function for partial transcripts
            on_turn_complete: Callback function for complete turns
        """
        self._transcript_callback = on_transcript
        self._turn_complete_callback = on_turn_complete
        
        try:
            # Build connection options
            options = {
                "model": self.model,
                "encoding": self.encoding,
                "sample_rate": str(self.sample_rate),
                "eot_threshold": str(self.eot_threshold),
                "eot_timeout_ms": str(self.eot_timeout_ms),
            }
            
            if self.eager_eot_threshold:
                options["eager_eot_threshold"] = str(self.eager_eot_threshold)
            
            # Connect to Flux via v2 endpoint
            self.connection = await self.client.listen.v2.connect(**options)
            
            # Set up event handlers
            self.connection.on(EventType.OPEN, self._on_open)
            self.connection.on(EventType.MESSAGE, self._on_message)
            self.connection.on(EventType.CLOSE, self._on_close)
            self.connection.on(EventType.ERROR, self._on_error)
            
            # Start listening
            await self.connection.start_listening()
            
            self.is_processing = True
            logger.info("✅ Connected to Deepgram Flux")
            
        except Exception as e:
            logger.error(f"Failed to connect to Deepgram: {e}")
            raise
    
    async def send_audio(self, audio_chunk: bytes):
        """
        Send audio data to Deepgram for transcription.
        
        Args:
            audio_chunk: Raw audio bytes (linear16 PCM format)
        """
        if not self.connection:
            raise RuntimeError("Not connected. Call connect() first.")
        
        try:
            await self.connection._send(audio_chunk)
        except Exception as e:
            logger.error(f"Error sending audio: {e}")
            raise
    
    async def disconnect(self):
        """Close the Deepgram connection."""
        if self.connection:
            try:
                await self.connection.finish()
                self.is_processing = False
                logger.info("Disconnected from Deepgram Flux")
            except Exception as e:
                logger.error(f"Error disconnecting: {e}")
    
    def _on_open(self, _):
        """Handle connection open event."""
        logger.debug("WebSocket connection opened")
    
    def _on_message(self, message: ListenV2SocketClientResponse):
        """
        Handle incoming transcription messages from Deepgram.
        
        Args:
            message: Deepgram message object
        """
        try:
            msg_type = getattr(message, "type", "Unknown")
            
            # Handle transcript messages
            if hasattr(message, 'transcript') and message.transcript:
                transcript_text = message.transcript
                
                # Extract metadata
                metadata = {
                    "type": msg_type,
                    "is_final": getattr(message, "is_final", False),
                    "speech_final": getattr(message, "speech_final", False),
                }
                
                # Add word-level confidence if available
                if hasattr(message, 'words') and message.words:
                    words_data = []
                    for word in message.words:
                        words_data.append({
                            "word": word.word,
                            "confidence": word.confidence,
                            "start": getattr(word, "start", 0),
                            "end": getattr(word, "end", 0)
                        })
                    metadata["words"] = words_data
                    
                    # Calculate average confidence
                    avg_confidence = sum(w["confidence"] for w in words_data) / len(words_data)
                    metadata["confidence"] = avg_confidence
                
                # Call transcript callback
                if self._transcript_callback:
                    self._transcript_callback(transcript_text, metadata)
                
                # If this is a final/complete turn, call turn complete callback
                if metadata.get("speech_final") and self._turn_complete_callback:
                    self._turn_complete_callback(transcript_text, metadata)
                
                logger.debug(f"Transcript [{msg_type}]: {transcript_text[:50]}...")
            
            # Handle end-of-turn events
            elif msg_type in ("EndOfTurn", "EagerEndOfTurn"):
                logger.debug(f"Turn event: {msg_type}")
                if self._turn_complete_callback:
                    self._turn_complete_callback("", {"type": msg_type, "event_only": True})
            
            # Handle TurnResumed (user continued speaking after eager EOT)
            elif msg_type == "TurnResumed":
                logger.debug("Turn resumed - user still speaking")
                # Could signal to cancel draft LLM response here
        
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    def _on_close(self, _):
        """Handle connection close event."""
        logger.debug("WebSocket connection closed")
        self.is_processing = False
    
    def _on_error(self, error):
        """Handle connection error event."""
        logger.error(f"WebSocket error: {error}")
    
    def get_config(self) -> Dict[str, Any]:
        """
        Get the current configuration.
        
        Returns:
            Dict containing the current configuration
        """
        return {
            "model": self.model,
            "encoding": self.encoding,
            "sample_rate": self.sample_rate,
            "eot_threshold": self.eot_threshold,
            "eager_eot_threshold": self.eager_eot_threshold,
            "eot_timeout_ms": self.eot_timeout_ms,
            "is_processing": self.is_processing,
            "provider": "deepgram_flux"
        }
    
    # Legacy compatibility methods (for drop-in replacement of WhisperTranscriber)
    
    def transcribe(self, audio: bytes) -> tuple[str, Dict[str, Any]]:
        """
        Synchronous transcription method (for compatibility with existing code).
        
        Args:
            audio: Audio data as bytes or numpy array
            
        Returns:
            Tuple of (transcript_text, metadata)
        """
        import asyncio
        
        # Convert numpy array to bytes if needed
        if hasattr(audio, 'tobytes'):
            audio = audio.tobytes()
        
        # Run async transcription in event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self.transcribe_async(audio))
    
    async def transcribe_async(self, audio: bytes) -> tuple[str, Dict[str, Any]]:
        """
        Async transcription method for compatibility.
        
        Note: Flux is designed for streaming, not batch processing.
        For one-shot transcription, consider using Deepgram's Nova model instead.
        
        Args:
            audio: Audio data as bytes
            
        Returns:
            Tuple of (transcript_text, metadata)
        """
        logger.warning(
            "Using Flux for batch transcription. Consider using streaming mode or Nova model."
        )
        
        # For batch mode, we'll connect, send all audio, wait for result, disconnect
        result_text = ""
        result_metadata = {}
        result_event = asyncio.Event()
        
        def on_final(text, metadata):
            nonlocal result_text, result_metadata
            if metadata.get("speech_final"):
                result_text = text
                result_metadata = metadata
                result_event.set()
        
        await self.connect(on_transcript=None, on_turn_complete=on_final)
        await self.send_audio(audio)
        
        # Wait for final result (with timeout)
        try:
            await asyncio.wait_for(result_event.wait(), timeout=10.0)
        except asyncio.TimeoutError:
            logger.warning("Transcription timeout")
        
        await self.disconnect()
        
        return result_text, result_metadata
