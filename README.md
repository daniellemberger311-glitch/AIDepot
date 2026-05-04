# AIDepot

Persönliche, lokal betriebene App zur Analyse von US-Aktien und Optionsscheinen.  
Erkennt Aktien im Pre-Breakout-Aufbau (VCP-Muster) frühzeitig und begleitet Optionsschein-Positionen täglich bis zum Exit.

**Stack:** Python 3.11 · FastAPI · SQLite · React 18 · TypeScript · Vite · Tailwind CSS

---

## Funktionsübersicht

- **Scanner** – täglich ~850 US-Aktien mit 3-Ebenen-Scoring (Fundamental · Technisch · Sentiment)
- **4-Zonen-Watchlist** – Zone 1 (≥76) bis Zone 4 (<41), mit automatischer Optionsschein-Empfehlung für Zone 1
- **Portfolio-Tracking** – offene Positionen mit KO-Abstand, Restlaufzeit und Exit-Signalen
- **Backtesting** – historische Score-Simulation für beliebige Ticker und Zeiträume
- **Telegram-Benachrichtigungen** – Zonenwechsel, Δ-Spikes, Exit-Signale (optional)

---

## Voraussetzungen

| Software | Mindestversion | Download |
|----------|---------------|----------|
| Python | 3.11 | https://python.org |
| Node.js | 18 | https://nodejs.org |
| Git | beliebig | https://git-scm.com |
| sqlite3 | beliebig | vorinstalliert auf Ubuntu/Debian |

---

## Installation

### 1. Repository klonen

```bash
git clone https://github.com/daniellemberger311-glitch/aidepot.git
cd aidepot
```

### 2. Python-Umgebung einrichten

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

### 3. API-Keys eintragen

```bash
cp .env.example .env
nano .env   # oder ein beliebiger Texteditor
```

| Variable | Dienst | Limit (Free) | Registrierung |
|----------|--------|-------------|---------------|
| `ALPHA_VANTAGE_API_KEY` | Alpha Vantage | 25 Req/Tag | https://alphavantage.co |
| `ALPHA_VANTAGE_API_KEY_2` | Alpha Vantage (2. Key) | +25 Req/Tag | zweiter kostenloser Account |
| `FINNHUB_API_KEY` | Finnhub | 60 Req/Min | https://finnhub.io |
| `MARKETAUX_API_KEY` | Marketaux | 100 News/Tag | https://marketaux.com |
| `SIMFIN_API_KEY` | SimFin | unbegrenzt | https://simfin.com |
| `TELEGRAM_BOT_TOKEN` | Telegram | kostenlos | optional – siehe unten |
| `TELEGRAM_CHAT_ID` | Telegram | – | optional – siehe unten |

> Alle 5 Daten-API-Keys sind kostenlos erhältlich. Ohne Telegram funktioniert die App vollständig.

### 4. Datenbank initialisieren

```bash
python scripts/init_db.py
```

Erstellt `data/aidepot.db` mit allen Tabellen und lädt das Ticker-Universum (~850 Aktien).

### 5. API-Verbindungen testen (optional)

```bash
python scripts/test_fetchers.py
```

### 6. Frontend bauen

```bash
cd frontend
npm install
npm run build   # erzeugt frontend/dist/ – wird vom Backend ausgeliefert
cd ..
```

---

## Als Heimserver-Dienst einrichten (empfohlen)

Läuft dauerhaft im Hintergrund, startet automatisch beim Hochfahren,  
erreichbar von jedem Gerät im Heimnetz.

### Firewall freischalten

```bash
sudo ufw allow 8000/tcp
sudo ufw reload
```

### Systemd-Dienst installieren

```bash
# Service-Datei kopieren
sudo cp aidepot.service /etc/systemd/system/

# DEINNUTZER durch deinen Linux-Nutzernamen ersetzen (2× in der Datei)
sudo nano /etc/systemd/system/aidepot.service

# Aktivieren und starten
sudo systemctl daemon-reload
sudo systemctl enable aidepot
sudo systemctl start aidepot

# Status prüfen
sudo systemctl status aidepot
```

### Automatisches Datenbank-Backup einrichten

Sichert die Datenbank täglich um 03:00 Uhr, behält die letzten 7 Kopien in `data/backups/`.

```bash
chmod +x scripts/backup.sh

sudo cp aidepot-backup.service /etc/systemd/system/
sudo cp aidepot-backup.timer   /etc/systemd/system/

# DEINNUTZER in der Service-Datei anpassen
sudo nano /etc/systemd/system/aidepot-backup.service

sudo systemctl daemon-reload
sudo systemctl enable --now aidepot-backup.timer

# Timer-Status prüfen
sudo systemctl list-timers aidepot-backup.timer
```

### IP-Adresse des Servers herausfinden

```bash
ip addr show | grep "inet " | grep -v 127.0.0.1
# Beispiel: inet 192.168.1.50/24
```

**Zugriff von anderen Geräten im Heimnetz:**
```
http://192.168.1.50:8000
```

> **Tipp:** Dem Server im Router eine feste IP zuweisen (DHCP-Reservierung nach MAC-Adresse),  
> damit sich die Adresse nie ändert. In der Fritzbox: *Heimnetz → Netzwerk → Netzwerkverbindungen*.

---

## Updates einspielen

```bash
bash update.sh
```

Das Script zieht den neuesten Stand von GitHub, aktualisiert Python-Pakete,  
baut das Frontend neu und startet den Dienst automatisch neu.

---

## Lokale Entwicklung (ohne Dienst)

Zwei Terminals öffnen:

```bash
# Terminal 1 – Backend
source .venv/bin/activate
uvicorn backend.main:app --reload --port 8000

# Terminal 2 – Frontend (mit Hot Reload)
cd frontend && npm run dev
```

App: **http://localhost:5173** · API-Doku: **http://localhost:8000/docs**

---

## Erster Scan

Nach dem Start auf dem Dashboard oben rechts **„Scan starten"** klicken.  
Der Scanner durchläuft eine erste Auswahl an Aktien und befüllt die Watchlist.  
Dauer: ca. 5–15 Minuten (abhängig von Rate-Limits der Free-APIs).

Der automatische Tagesscan läuft täglich um **06:00 UTC**.

---

## Logs anschauen

```bash
# Live-Logs des Dienstes
sudo journalctl -u aidepot -f

# Letzte 100 Zeilen
sudo journalctl -u aidepot -n 100

# Backup-Log
sudo journalctl -u aidepot-backup
```

---

## Telegram einrichten (optional)

1. In Telegram `@BotFather` anschreiben → `/newbot` → Token kopieren → in `.env` als `TELEGRAM_BOT_TOKEN`
2. Den Bot einmal selbst anschreiben (beliebige Nachricht)
3. Aufrufen: `https://api.telegram.org/bot<TOKEN>/getUpdates`
4. `"chat": {"id": ...}` kopieren → in `.env` als `TELEGRAM_CHAT_ID`
5. Dienst neu starten: `sudo systemctl restart aidepot`

---

## Projektstruktur

```
AIDepot/
├── backend/
│   ├── main.py              # FastAPI-App (Port 8000)
│   ├── api/                 # 40 REST-Endpunkte
│   ├── scoring/             # 3-Ebenen-Scoring-Engine
│   ├── fetchers/            # 8 Datenquellen-Adapter
│   ├── backtesting/         # Historische Simulation
│   ├── scheduler/           # APScheduler-Jobs
│   └── notifications/       # Telegram-Bot
├── frontend/
│   └── src/
│       ├── pages/           # 7 Seiten (Dashboard, Watchlist, …)
│       ├── components/      # Wiederverwendbare UI-Komponenten
│       └── api/client.ts    # Axios-API-Client
├── scripts/
│   ├── init_db.py           # DB einmalig initialisieren
│   ├── test_fetchers.py     # API-Keys testen
│   └── backup.sh            # Manuelles Backup
├── data/
│   ├── aidepot.db           # SQLite-Datenbank (wird angelegt)
│   └── backups/             # Tägliche DB-Backups (wird angelegt)
├── aidepot.service          # systemd Hauptdienst
├── aidepot-backup.service   # systemd Backup-Dienst
├── aidepot-backup.timer     # systemd Backup-Timer (täglich 03:00)
├── update.sh                # Update auf neueste Version
├── .env.example             # API-Keys Vorlage
└── docs/                    # Technische Dokumentation
```

---

## Seiten

| URL | Beschreibung |
|-----|-------------|
| `/` | Dashboard – KPIs, Top-Signale, Exit-Warnungen |
| `/watchlist` | 4-Zonen-Tabelle aller Aktien, sortierbar |
| `/signal/:ticker` | Score-Aufschlüsselung, 30-Tage-Chart, OS-Empfehlung |
| `/portfolio` | Offene Positionen, Kauf/Verkauf, Exit-Signale |
| `/history` | Trade-Archiv, P&L-Statistik, Signalqualität |
| `/backtest` | Historische Score-Simulation mit Chart |
| `/config` | Universum, API-Status, Gewichtungen, Scan-Einstellungen |
