"""
Speech-to-Text Transcription Service

Uses Deepgram API for transcription.
"""

import numpy as np
import logging
import io
import os
import httpx
from typing import Dict, Any, List, Optional, Tuple
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WhisperTranscriber:
    """
    Speech-to-Text service using Deepgram API.
    
    Kept the class name for backward compatibility.
    """
    
    def __init__(
        self,
        model_size: str = "base",
        device: str = None,
        compute_type: str = None,
        beam_size: int = 2,
        sample_rate: int = 44100
    ):
        """
        Initialize the transcription service.
        
        Args are kept for backward compatibility but not used.
        Deepgram API handles model selection automatically.
        """
        self.sample_rate = sample_rate
        self.api_key = os.getenv("DEEPGRAM_API_KEY")
        
        if not self.api_key:
            raise ValueError("DEEPGRAM_API_KEY environment variable is required")
        
        # State tracking
        self.is_processing = False
        
        logger.info("Initialized Deepgram Transcriber")
    
    def transcribe(self, audio: np.ndarray) -> Tuple[str, Dict[str, Any]]:
        """
        Transcribe audio data to text using Deepgram API.
        
        Args:
            audio: Audio data as numpy array or WAV bytes
            
        Returns:
            Tuple[str, Dict[str, Any]]: 
                - Transcribed text
                - Dictionary with additional information
        """
        start_time = time.time()
        self.is_processing = True
        
        try:
            # Convert audio to bytes if it's a numpy array
            if isinstance(audio, np.ndarray):
                if audio.dtype == np.uint8:
                    # Already WAV bytes
                    audio_bytes = bytes(audio)
                else:
                    # Convert float32 to int16 WAV
                    audio = np.clip(audio * 32767, -32768, 32767).astype(np.int16)
                    
                    # Create WAV file in memory
                    import wave
                    wav_buffer = io.BytesIO()
                    with wave.open(wav_buffer, 'wb') as wav_file:
                        wav_file.setnchannels(1)
                        wav_file.setsampwidth(2)  # 16-bit
                        wav_file.setframerate(self.sample_rate)
                        wav_file.writeframes(audio.tobytes())
                    
                    audio_bytes = wav_buffer.getvalue()
            else:
                audio_bytes = audio
            
            # Call Deepgram API
            url = "https://api.deepgram.com/v1/listen"
            params = {
                "model": "nova-2",
                "language": "en",
                "punctuate": True,
                "smart_format": True
            }
            
            headers = {
                "Authorization": f"Token {self.api_key}",
                "Content-Type": "audio/wav"
            }
            
            with httpx.Client(timeout=30.0) as client:
                response = client.post(url, params=params, headers=headers, content=audio_bytes)
                response.raise_for_status()
                result = response.json()
            
            # Extract transcription
            transcript = result.get("results", {}).get("channels", [{}])[0].get("alternatives", [{}])[0].get("transcript", "")
            confidence = result.get("results", {}).get("channels", [{}])[0].get("alternatives", [{}])[0].get("confidence", 0)
            
            processing_time = time.time() - start_time
            logger.info(f"Transcription completed in {processing_time:.2f}s: {transcript[:50]}...")
            
            metadata = {
                "confidence": confidence,
                "language": "en",
                "processing_time": processing_time,
                "model": "deepgram-nova-2"
            }
            
            return transcript, metadata
            
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return "", {"error": str(e)}
        finally:
            self.is_processing = False
    
    def transcribe_streaming(self, audio_generator):
        """
        Stream transcription results from an audio generator.
        
        Note: Deepgram has WebSocket streaming but for simplicity
        this batches the audio and transcribes it.
        """
        self.is_processing = True
        
        try:
            # Collect audio chunks
            audio_chunks = []
            for chunk in audio_generator:
                audio_chunks.append(chunk)
            
            # Combine and transcribe
            full_audio = np.concatenate(audio_chunks)
            text, metadata = self.transcribe(full_audio)
            
            yield {
                "text": text,
                "confidence": metadata.get("confidence", 0)
            }
                
        except Exception as e:
            logger.error(f"Streaming transcription error: {e}")
            yield {"error": str(e)}
        finally:
            self.is_processing = False
    
    def get_config(self) -> Dict[str, Any]:
        """
        Get the current configuration.
        
        Returns:
            Dict containing the current configuration
        """
        return {
            "model": "deepgram-nova-2",
            "sample_rate": self.sample_rate,
            "is_processing": self.is_processing
        }
