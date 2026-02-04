"""
LLM Service

Handles communication with the LLM API endpoint.
Extended for Clawdbot/OpenClaw gateway integration.
Now with streaming support for lower latency.
"""

import json
import requests
import httpx
import logging
import time
from typing import Dict, Any, List, Optional, AsyncGenerator

from config import (
    USE_CLAWDBOT,
    get_llm_endpoint,
    get_clawdbot_headers,
    LLM_API_KEY,
    CLAWDBOT_SESSION_KEY,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self, api_endpoint=None, model="default", temperature=0.7, max_tokens=2048, timeout=60):
        self.api_endpoint = api_endpoint or get_llm_endpoint()
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.is_processing = False
        self.conversation_history = []
        self.use_clawdbot = USE_CLAWDBOT
        logger.info(f"Initialized LLM Client: endpoint={self.api_endpoint}, use_clawdbot={self.use_clawdbot}")

    def _get_headers(self):
        if self.use_clawdbot:
            return get_clawdbot_headers()
        headers = {"Content-Type": "application/json"}
        if LLM_API_KEY:
            headers["Authorization"] = f"Bearer {LLM_API_KEY}"
        return headers

    def add_to_history(self, role, content):
        self.conversation_history.append({"role": role, "content": content})
        if len(self.conversation_history) > 50:
            if self.conversation_history[0]["role"] == "system":
                self.conversation_history = [self.conversation_history[0]] + self.conversation_history[-49:]
            else:
                self.conversation_history = self.conversation_history[-50:]

    async def stream_response(self, user_input, system_prompt=None, add_to_history=True, temperature=None):
        """Stream LLM response token by token for lower latency."""
        self.is_processing = True
        full_response = ""
        start_time = time.time()
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            if user_input.strip() and add_to_history:
                self.add_to_history("user", user_input)
            messages.extend(self.conversation_history)
            if user_input.strip() and not add_to_history:
                messages.append({"role": "user", "content": user_input})
            payload = {"messages": messages, "temperature": temperature or self.temperature, "max_tokens": self.max_tokens, "stream": True}
            if self.model != "default" and not self.use_clawdbot:
                payload["model"] = self.model
            elif self.use_clawdbot:
                payload["model"] = "clawdbot"
            logger.info(f"Starting streaming LLM request with {len(messages)} messages")
            headers = self._get_headers()
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream("POST", self.api_endpoint, json=payload, headers=headers) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            chunk = line[6:]
                            if chunk == "[DONE]":
                                break
                            try:
                                data = json.loads(chunk)
                                if "choices" in data and len(data["choices"]) > 0:
                                    delta = data["choices"][0].get("delta", {})
                                    if "content" in delta:
                                        token = delta["content"]
                                        full_response += token
                                        yield token
                            except json.JSONDecodeError:
                                continue
            if full_response and add_to_history:
                self.add_to_history("assistant", full_response)
            logger.info(f"Streaming complete after {time.time() - start_time:.2f}s, {len(full_response)} chars")
        except httpx.HTTPStatusError as e:
            logger.error(f"LLM API streaming error: {e}")
            yield f"I'm sorry, I encountered a problem connecting to my language model. {str(e)}"
        except Exception as e:
            logger.error(f"LLM streaming error: {e}")
            yield "I'm sorry, I encountered an unexpected error. Please try again."
        finally:
            self.is_processing = False

    def get_response(self, user_input, system_prompt=None, add_to_history=True, temperature=None):
        """Get a response from the LLM (non-streaming, for compatibility)."""
        self.is_processing = True
        start_time = time.time()
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            if user_input.strip() and add_to_history:
                self.add_to_history("user", user_input)
            messages.extend(self.conversation_history)
            if user_input.strip() and not add_to_history:
                messages.append({"role": "user", "content": user_input})
            payload = {"messages": messages, "temperature": temperature or self.temperature, "max_tokens": self.max_tokens}
            if self.model != "default" and not self.use_clawdbot:
                payload["model"] = self.model
            elif self.use_clawdbot:
                payload["model"] = "clawdbot"
            logger.info(f"Sending request to LLM API with {len(messages)} messages")
            headers = self._get_headers()
            response = requests.post(self.api_endpoint, json=payload, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            result = response.json()
            assistant_message = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            if assistant_message and add_to_history:
                self.add_to_history("assistant", assistant_message)
            processing_time = time.time() - start_time
            logger.info(f"Received response from LLM API after {processing_time:.2f}s")
            return {"text": assistant_message, "processing_time": processing_time, "via_clawdbot": self.use_clawdbot}
        except requests.RequestException as e:
            logger.error(f"LLM API request error: {e}")
            error_response = f"I'm sorry, I encountered a problem connecting to my language model. {str(e)}"
            if add_to_history:
                self.add_to_history("assistant", error_response)
            return {"text": error_response, "error": str(e), "via_clawdbot": self.use_clawdbot}
        except Exception as e:
            logger.error(f"LLM processing error: {e}")
            error_response = "I'm sorry, I encountered an unexpected error. Please try again."
            self.add_to_history("assistant", error_response)
            return {"text": error_response, "error": str(e), "via_clawdbot": self.use_clawdbot}
        finally:
            self.is_processing = False

    def clear_history(self, keep_system_prompt=True):
        if keep_system_prompt and self.conversation_history and self.conversation_history[0]["role"] == "system":
            self.conversation_history = [self.conversation_history[0]]
        else:
            self.conversation_history = []

    def get_config(self):
        return {
            "api_endpoint": self.api_endpoint,
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "timeout": self.timeout,
            "is_processing": self.is_processing,
            "history_length": len(self.conversation_history),
            "use_clawdbot": self.use_clawdbot
        }
