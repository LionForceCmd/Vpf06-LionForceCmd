"""Слой обращения к LLM: синхронный OpenAI-клиент + вызов из async-кода.

Если OPENAI_API_KEY не задан, включается offline-режим: бот отвечает заготовкой,
но память и логика запроса работают точно так же — удобно для демонстрации.
"""

from __future__ import annotations

import asyncio
import os
from typing import List, Optional

from memory import ChatMessage

_client = None


def get_client():
    """Ленивая инициализация OpenAI-клиента (создаётся один раз на процесс)."""
    global _client
    if _client is None:
        from openai import OpenAI

        _client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    return _client


def offline_reply(messages: List[ChatMessage]) -> str:
    """Заглушка без API: показывает, какие сообщения бот подставил в запрос."""
    history = messages[1:-1]  # без system-промпта и текущего реплики
    last_user = next((m["content"] for m in reversed(history) if m["role"] == "user"), "—")
    return (
        "[offline-режим: OPENAI_API_KEY не задан]\n"
        f"Текущий вопрос: {messages[-1]['content']}\n"
        f"Предыдущая реплика пользователя из памяти: {last_user}\n"
        f"В модель ушло сообщений из памяти: {len(history)}"
    )


async def generate_reply(messages: List[ChatMessage], model: Optional[str] = None) -> str:
    """Единственный вызов Chat Completions. Синхронный SDK не блокирует loop."""
    if not os.getenv("OPENAI_API_KEY"):
        return offline_reply(messages)

    def _call() -> str:
        completion = get_client().chat.completions.create(
            model=model or os.getenv("MODEL", "gpt-4o-mini"),
            messages=messages,
            temperature=0.7,
            max_tokens=500,
        )
        return completion.choices[0].message.content or ""

    return await asyncio.to_thread(_call)