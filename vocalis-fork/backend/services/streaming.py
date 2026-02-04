"""
Streaming helper functions for VoiceClaw.
Add these to websocket.py for sentence-buffered streaming.
"""

import re
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Sentence-ending patterns
SENTENCE_END_PATTERN = re.compile(r'[.!?]\s*$|[.!?]\"?\s*$')


def is_sentence_complete(text):
    """Check if the text ends with a complete sentence."""
    return bool(SENTENCE_END_PATTERN.search(text.strip()))


async def stream_speech_with_buffering(websocket, llm_client, tts_client, transcript, system_prompt, MessageType):
    """
    Stream LLM response with sentence buffering for lower latency TTS.

    Instead of waiting for the full LLM response, this:
    1. Streams tokens from the LLM
    2. Buffers until a complete sentence is detected
    3. Sends each sentence to TTS immediately
    4. Streams audio chunks to the frontend as they're ready

    This reduces perceived latency from 3-5s to ~1-1.5s.
    """
    buffer = ""
    full_response = ""
    sentence_count = 0
    first_audio_sent = False

    try:
        # Signal TTS start
        await websocket.send_json({
            "type": MessageType.TTS_START,
            "timestamp": datetime.now().isoformat()
        })

        # Stream tokens from LLM
        async for token in llm_client.stream_response(transcript, system_prompt):
            buffer += token
            full_response += token
            
            # Check if NO_REPLY is detected in the response so far
            if "NO_REPLY" in full_response.upper().replace(" ", ""):
                logger.info("Detected NO_REPLY in streaming response, aborting TTS")
                # Send TTS_END without any audio
                await websocket.send_json({
                    "type": MessageType.TTS_END,
                    "timestamp": datetime.now().isoformat()
                })
                # Send the LLM response (for logging, won't be vocalized)
                await websocket.send_json({
                    "type": MessageType.LLM_RESPONSE,
                    "text": full_response,
                    "metadata": {"no_reply": True},
                    "timestamp": datetime.now().isoformat()
                })
                return full_response

            # Check if we have a complete sentence
            if is_sentence_complete(buffer) and len(buffer.strip()) > 10:
                sentence = buffer.strip()
                buffer = ""
                sentence_count += 1

                logger.info(f"Sentence {sentence_count} ready: {sentence[:50]}...")

                # Generate TTS for this sentence (non-blocking)
                try:
                    audio_data = await tts_client.async_text_to_speech(sentence)

                    if not first_audio_sent:
                        first_audio_sent = True
                        logger.info("First audio chunk ready - sending to client")

                    # Send audio chunk
                    import base64
                    encoded_audio = base64.b64encode(audio_data).decode("utf-8")
                    await websocket.send_json({
                        "type": MessageType.TTS_CHUNK,
                        "audio_chunk": encoded_audio,
                        "format": tts_client.output_format,
                        "sentence_num": sentence_count,
                        "timestamp": datetime.now().isoformat()
                    })
                except Exception as e:
                    logger.error(f"TTS error for sentence {sentence_count}: {e}")

        # Handle any remaining text in buffer
        if buffer.strip():
            sentence_count += 1
            logger.info(f"Final sentence: {buffer[:50]}...")

            try:
                audio_data = await tts_client.async_text_to_speech(buffer.strip())
                import base64
                encoded_audio = base64.b64encode(audio_data).decode("utf-8")
                await websocket.send_json({
                    "type": MessageType.TTS_CHUNK,
                    "audio_chunk": encoded_audio,
                    "format": tts_client.output_format,
                    "sentence_num": sentence_count,
                    "is_final": True,
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
                logger.error(f"TTS error for final sentence: {e}")

        # Signal TTS end
        await websocket.send_json({
            "type": MessageType.TTS_END,
            "total_sentences": sentence_count,
            "timestamp": datetime.now().isoformat()
        })

        # Send full LLM response for display
        await websocket.send_json({
            "type": MessageType.LLM_RESPONSE,
            "text": full_response,
            "metadata": {"streaming": True, "sentences": sentence_count},
            "timestamp": datetime.now().isoformat()
        })

        return full_response

    except Exception as e:
        logger.error(f"Streaming error: {e}")
        raise
