# backend/tools/deepseek_client.py
import os
import httpx
import json
import uuid
from typing import Any, Dict

DEEPSEEK_KEY = os.environ.get("DEEPSEEK_API_KEY")  # put key in .env
DEEPSEEK_BASE = os.environ.get("DEEPSEEK_BASE", "https://api.deepseek.com/v1")

class DeepSeekClient:
    def __init__(self, api_key: str = None, model: str = "deepseek-r1:free"):
        self.api_key = api_key or DEEPSEEK_KEY
        self.model = model
        if not self.api_key:
            raise RuntimeError("DEEPSEEK_API_KEY not set in env")

    def with_model(self, provider: str, model_name: str):
        # keep chaining compatibility
        self.model = model_name
        return self

    async def send_message(self, user_message) -> str:
        """
        user_message can be any object with .text attribute (we use UserMessage in server).
        Returns the assistant text (string).
        """
        # Build a chat-style payload similar to OpenAI chat completions
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": getattr(user_message, "system_message", "")},
                {"role": "user", "content": getattr(user_message, "text", str(user_message))}
            ],
            "max_tokens": 1000,
            "temperature": 0.0
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{DEEPSEEK_BASE}/chat/completions", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        # DeepSeek responses may have different shape; try common fields:
        # Attempt to extract assistant message string in common locations.
        # Common shapes: {"choices":[{"message":{"content":"..."}}, ... ]} or {"output": "..."}
        if isinstance(data, dict):
            # choices -> message -> content
            choices = data.get("choices")
            if choices and isinstance(choices, list) and len(choices) > 0:
                first = choices[0]
                # handle both 'message' and 'text' possibilities
                if isinstance(first, dict):
                    msg = first.get("message") or first.get("text") or first.get("output")
                    if isinstance(msg, dict) and "content" in msg:
                        return msg["content"]
                    if isinstance(msg, str):
                        return msg
            # fallback to "output" or "text" top-level
            for key in ("output", "text", "content"):
                if key in data and isinstance(data[key], str):
                    return data[key]
        # final fallback: return json dump
        return json.dumps(data)
