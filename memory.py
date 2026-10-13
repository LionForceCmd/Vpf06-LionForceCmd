"""Короткая память бота: последние N сообщений диалога для каждого пользователя.

Хранилище — обычный словарь в оперативной памяти процесса:
    user_id -> deque(maxlen=N)
deque с maxlen сам выкидывает самый старый элемент, когда добавляется новый,
поэтому «окно» в 10 сообщений поддерживается автоматически, без ручной обрезки.
"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Deque, Dict, List, TypedDict

MEMORY_LIMIT = 10  # столько последних сообщений (user + assistant) видит модель


class ChatMessage(TypedDict):
    role: str  # "system" | "user" | "assistant"
    content: str


class ShortMemory:
    """Окно диалога: последние MEMORY_LIMIT сообщений на пользователя."""

    def __init__(self, limit: int = MEMORY_LIMIT) -> None:
        self.limit = limit
        self._store: Dict[int, Deque[ChatMessage]] = defaultdict(
            lambda: deque(maxlen=limit)
        )

    def add(self, user_id: int, role: str, content: str) -> None:
        """Дописать сообщение в окно; при переполнении вытесняется самое старое."""
        if not content.strip():
            return
        self._store[user_id].append({"role": role, "content": content})

    def history(self, user_id: int) -> List[ChatMessage]:
        """Копия истории для отправки в модель (обрезка уже сделана deque)."""
        return list(self._store[user_id])

    def size(self, user_id: int) -> int:
        return len(self._store[user_id])

    def clear(self, user_id: int) -> None:
        """Забыть диалог — команда /reset."""
        self._store.pop(user_id, None)