"""Проверки короткой памяти и сборки запроса. Запуск: python tests.py"""

from __future__ import annotations

from memory import ShortMemory
from bot import build_messages

PASSED = 0


def check(name: str, condition: bool) -> None:
    global PASSED
    assert condition, f"FAILED: {name}"
    PASSED += 1
    print(f"  ok — {name}")


def fill(mem: ShortMemory, user_id: int, pairs: int, start: int = 0) -> None:
    for i in range(start, start + pairs):
        mem.add(user_id, "user", f"вопрос {i}")
        mem.add(user_id, "assistant", f"ответ {i}")


def main() -> None:
    mem = ShortMemory(limit=10)

    fill(mem, 1, 3)
    check("окно растёт до лимита", mem.size(1) == 6)

    fill(mem, 1, 5, start=3)  # ещё 10 сообщений — всего 16, в окно попадут последние 10
    check("окно обрезано до 10 сообщений", mem.size(1) == 10)

    history = mem.history(1)
    check("первое сообщение вытеснено", history[0]["content"] == "вопрос 3")
    check("последнее сообщение сохранено", history[-1]["content"] == "ответ 7")
    check("роли чередуются", history[0]["role"] == "user" and history[1]["role"] == "assistant")

    fill(mem, 2, 1)
    check("у пользователей память раздельная", mem.size(2) == 2 and mem.size(1) == 10)

    mem.clear(1)
    check("reset очищает память", mem.size(1) == 0)

    mem.add(3, "user", "   ")
    check("пустые сообщения не сохраняются", mem.size(3) == 0)

    mem.add(3, "user", "Меня зовут Аня")
    mem.add(3, "assistant", "Привет, Аня!")
    mem.add(3, "user", "Как меня зовут?")
    messages = build_messages(3, mem)
    check("в запросе system + вся история", len(messages) == 4)
    check("system-промпт первый", messages[0]["role"] == "system")
    check("последним идёт текущий вопрос", messages[-1]["content"] == "Как меня зовут?")
    check("имя из памяти попало в запрос", any("Аня" in m["content"] for m in messages))

    print(f"\nВсе проверки пройдены: {PASSED}")


if __name__ == "__main__":
    main()