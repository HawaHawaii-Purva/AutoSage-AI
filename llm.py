"""LLM adapter: local Ollama for development, Hugging Face Inference for deployment."""
from __future__ import annotations

import os
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()


def _ollama_chat(messages: list[dict[str, str]], temperature: float = 0.2) -> str:
    base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    model = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": temperature},
    }
    response = requests.post(f"{base}/api/chat", json=payload, timeout=120)
    response.raise_for_status()
    data = response.json()
    return data["message"]["content"]


def _hf_chat(messages: list[dict[str, str]], temperature: float = 0.2) -> str:
    from huggingface_hub import InferenceClient

    token = os.getenv("HF_TOKEN")
    if not token:
        raise RuntimeError("HF_TOKEN is missing. Add it to Streamlit secrets or switch to local Ollama.")
    model = os.getenv("HF_MODEL", "Qwen/Qwen2.5-7B-Instruct")
    client = InferenceClient(api_key=token)
    result = client.chat_completion(
        messages=messages,
        model=model,
        max_tokens=900,
        temperature=temperature,
    )
    return result.choices[0].message.content or ""


def chat(messages: list[dict[str, str]], temperature: float = 0.2) -> str:
    provider = os.getenv("LLM_PROVIDER", "ollama").lower().strip()
    if provider == "hf":
        return _hf_chat(messages, temperature)
    return _ollama_chat(messages, temperature)
