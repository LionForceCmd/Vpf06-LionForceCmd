"""Telegram-бот с короткой памятью: помнит последние 10 сообщений диалога.

Логика одного запроса:
    1. реплика пользователя кладётся в окно памяти;
    2. в модель уходит [system] + последние 10 сообщений (окно уже содержит реплику);
    3. ответ модели кладётся в то же окно — следующий запрос будет с контекстом.

Запуск:
    python bot.py            # нужен .env с BOT_TOKEN и OPENAI_API_KEY
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import List

from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from dotenv import load_dotenv

from llm import generate_reply
from memory import ChatMessage, ShortMemory

load_dotenv()

log = logging.getLogger("vpf06")

SYSTEM_PROMPT = (
    "Ты — дружелюбный и лаконичный помощник в Telegram. "
    "Учитывай историю диалога: если пользователь ссылается на предыдущие реплики "
    "(\"прошлый вопрос\", \"ты только что сказал\"), отвечай по этой истории. "
    "Отвечай по делу, без воды."
)

memory = ShortMemory(limit=10)
router = Router()


def build_messages(user_id: int, mem: ShortMemory | None = None) -> List[ChatMessage]:
    """Собирает запрос к модели: системный промпт + окно памяти пользователя."""
    system: ChatMessage = {"role": "system", "content": SYSTEM_PROMPT}
    return [system, *(mem or memory).history(user_id)]


@router.message(CommandStart())
async def on_start(message: Message) -> None:
    await message.answer(
        "Привет! У меня есть короткая память — я помню последние 10 сообщений диалога.\n"
        "Просто пишите: задайте вопрос, а потом уточните его, не повторяя контекст.\n"
        "/memory — сколько сообщений я сейчас помню, /reset — забыть всё."
    )


@router.message(Command("memory"))
async def on_memory(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else 0
    history = memory.history(user_id)
    last = history[-1]["content"] if history else "—"
    await message.answer(
        f"В памяти {memory.size(user_id)} из 10 сообщений.\n"
        f"Последнее: {last[:200]}"
    )


@router.message(Command("reset"))
async def on_reset(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else 0
    memory.clear(user_id)
    await message.answer("Память очищена, начинаем с чистого листа.")


@router.message(F.text)
async def on_text(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else 0
    user_text = message.text or ""

    memory.add(user_id, "user", user_text)          # 1. новое сообщение в окно
    messages = build_messages(user_id)              # 2. system + до 10 сообщений

    try:
        reply = await generate_reply(messages)
    except Exception:
        log.exception("OpenAI error")
        await message.answer("Не удалось получить ответ от модели. Попробуйте ещё раз.")
        return

    await message.answer(reply)                     # 3. ответ тоже в память
    memory.add(user_id, "assistant", reply)


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("Нет переменной окружения BOT_TOKEN (см. .env.example)")

    bot = Bot(token=token, parse_mode=ParseMode.HTML)
    dp = Dispatcher()
    dp.include_router(router)

    log.info("Бот запущен. Окно памяти: %d сообщений.", memory.limit)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass