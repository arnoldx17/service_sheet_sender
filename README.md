# service_sheet_sender

A `service_sheet_sender` a SEVENET s.r.o. digitális szervizlap-folyamatának kiegészítő szolgáltatása. DocuSeal webhook eseményeket fogad a `POST /webhook` végponton.

Az alkalmazás a következő eseményeket dolgozza fel:

- `submission.completed`: letölti az aláírt PDF-et, szükség esetén feltölti a Splynx ügyfélprofiljához, majd e-mailben elküldi azt a megadott címzettnek;
- `submission.created`: Nextcloud Talk üzenetet küld az újonnan létrehozott szervizlapról.

## Követelmények

- Python 3;
- `wget` – az aláírt PDF letöltéséhez;
- `curl` – a Nextcloud Talk üzenet elküldéséhez.

Production környezetben a Gunicorn is szükséges (lásd lentebb).

## Helyi telepítés és futtatás

### 1. A repository klónozása

```bash
git clone https://github.com/arnoldx17/service_sheet_sender.git
cd service_sheet_sender
```

### 2. Virtuális környezet létrehozása

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Függőségek telepítése

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 4. Környezeti változók beállítása

Másold le a példafájlt, majd töltsd ki a valódi értékekkel:

```bash
cp .env.example .env
```

A `.env` fájl által támogatott változói:

| Változó | Rendeltetés |
| --- | --- |
| `DOCUSEAL_KEY` | DocuSeal API-kulcs |
| `DOCUSEAL_URL` | DocuSeal API URL-je |
| `SMTP_SERVER` | SMTP-kiszolgáló címe |
| `SMTP_PORT` | SMTP-port |
| `IMAP_SERVER` | IMAP-kiszolgáló címe |
| `IMAP_PORT` | IMAP-port |
| `SENDER_EMAIL` | Feladó e-mail-címe |
| `SENDER_PASSWORD` | Az e-mail-fiók jelszava |
| `SPLYNX_HOST` | Splynx hosztnév |
| `SPLYNX_AUTH` | Splynx `Authorization` fejléc értéke |
| `NEXTCLOUD_USER` | Nextcloud felhasználónév |
| `NEXTCLOUD_PASS` | Nextcloud jelszó |
| `NEXTCLOUD_CHAT_LINK` | Nextcloud Talk OCS API végpontja |

Az `.env` titkos adatokat tartalmaz; ne kerüljön verziókövetésbe.

### 5. Fejlesztői indítás

```bash
python app.py
```

Az alkalmazás a `0.0.0.0:5000` címen indul, a webhook végpont elérési útja: `POST /webhook`.

## Production futtatás Gunicornnal és systemd-vel

Az alkalmazás WSGI belépési pontja `app:app`: az `app.py` fájlban lévő Flask `app` objektum. A Flask beépített fejlesztői szerverét production környezetben ne használd.

### 1. Telepítés a szerverre

A választott telepítési könyvtárban klónozd a repository-t, majd hozd létre a virtuális környezetet. Az alábbi parancsokban a `<telepítési-könyvtár>` a szerveren választott abszolút útvonal; ezt a repository nem rögzíti.

```bash
git clone https://github.com/arnoldx17/service_sheet_sender.git <telepítési-könyvtár>
cd <telepítési-könyvtár>
python3 -m venv venv
./venv/bin/python -m pip install --upgrade pip
./venv/bin/python -m pip install -r requirements.txt
./venv/bin/python -m pip install gunicorn
cp .env.example .env
```

Töltsd ki a `<telepítési-könyvtár>/.env` fájlt a fenti táblázat szerint. A szolgáltatás `WorkingDirectory` beállítása miatt a `logs/` és `tmp/` könyvtárak itt jönnek majd létre.

### 2. Gunicorn próbaindítás

Az alkalmazásból indulva:

```bash
./venv/bin/gunicorn --bind 127.0.0.1:5000 app:app
```

A példa csak a helyi gépről teszi elérhetővé az alkalmazást. Külső webhook esetén egy fordított proxy (például Nginx) továbbíthatja a HTTPS kéréseket erre a portra. A publikus URL-en a végpont útvonala továbbra is `/webhook`.

### 3. systemd szolgáltatás

Hozd létre a `/etc/systemd/system/service_sheet_sender.service` fájlt az alábbi tartalommal. A `<felhasználó>` és `<telepítési-könyvtár>` értékét a szerver tényleges, dedikált szolgáltatási felhasználójára, illetve a fenti telepítési útvonalra cseréld.

```ini
[Unit]
Description=service_sheet_sender DocuSeal webhook listener
After=network.target

[Service]
Type=simple
User=<felhasználó>
Group=<felhasználó>
WorkingDirectory=<telepítési-könyvtár>
Environment=PYTHONUNBUFFERED=1
ExecStart=<telepítési-könyvtár>/venv/bin/gunicorn --workers 2 --bind 127.0.0.1:5000 app:app
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Indítsd el és állítsd be automatikus indításra:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now service_sheet_sender
sudo systemctl status service_sheet_sender
```

Naplók megtekintése:

```bash
sudo journalctl -u service_sheet_sender -f
```

Az alkalmazás saját, forgatott naplófájlja a `<telepítési-könyvtár>/logs/service_sheet_sender.log` lesz.

### 4. Frissítés

```bash
cd <telepítési-könyvtár>
git pull
./venv/bin/python -m pip install -r requirements.txt
sudo systemctl restart service_sheet_sender
```

## Ellenőrzési lista

- A szerveren telepítve van a `wget` és a `curl`.
- A `.env` minden értéke ki van töltve, és a szolgáltatási felhasználó olvasni tudja.
- A választott `<telepítési-könyvtár>` írható a szolgáltatási felhasználó számára, mert az alkalmazás `logs/` és `tmp/` alkönyvtárakat hoz létre.
- A fordított proxy a `POST /webhook` kéréseket a Gunicorn `127.0.0.1:5000` címére továbbítja.
- A DocuSeal webhook URL a publikusan elérhető HTTPS címet és a `/webhook` útvonalat használja.
