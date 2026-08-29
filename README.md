# service_sheet_sender

Ez egy kiegészítő script, a SEVENET s.r.o. digitális szervizlap bevezetésénél használt kiegészítő script.
Docuseal webhook eseményeket dolgoz fel, és az alapján végez műveleteket.
Pl.:    Az aláírás pillanatában szervizlap küldése a kliens számára,
        Az aláírás pillanatában szervizlap feltöltése a Splynx rendszerbe a kliens profiljához.

---

## 🚀 Telepítés és Beüzemelés

Kövesd az alábbi lépéseket a projekt helyi futtatásához egy `git clone` után.

### 1. Tároló klónozása
```bash
git clone https://github.com/arnoldx17/service_sheet_sender.git
cd service_sheet_sender
```

---

### 2. Virtuális környezet létrehozása és aktiválása

**Linux / macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

---

### 3. Függőségek telepítése
```bash
pip install -r requirements.txt
```

---

### 4. Környezeti változók beállítása

Hozz létre egy `.env` fájlt a `.env.example` alapján:

**Linux / macOS:**
```bash
cp .env.example .env
```

Nyisd meg a `.env` fájlt, és töltsd ki a szükséges értékeket (pl. API kulcsok, adatbázis hozzáférések).

---

## ▶️ Futtatás

A környezet aktiválása után az alkalmazást az alábbi paranccsal indíthatod el:

```bash
python app.py
```
