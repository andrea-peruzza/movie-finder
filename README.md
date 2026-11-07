# Letterboxd & JustWatch Italia 🎬📡
> Trova velocemente tra i film della tua watchlist di Letterboxd quelli disponibili alla **visione immediata in streaming in Italia** (sui tuoi abbonamenti o gratis).

---

## Caratteristiche Principali

- **Integrazione Letterboxd & Gestione CSV Incrementale**:
  - **Importazione 1-Click via file `watchlist.csv`**: esportato da Letterboxd (*Settings > Import & Export > Export Your Data*).
  - **Unione e Deduplicazione Automatica**: ogni nuovo file CSV importato viene automaticamente unito al file `watchlist.csv` presente nella cartella. Se ci sono più righe dello stesso film uscito nello stesso anno, viene mantenuta **una sola riga**.
  - **Scansione Intelligente Selettiva**: la ricerca JustWatch viene avviata **esclusivamente per i film non presenti nella precedente importazione**, preservando i risultati e le offerte già verificate per tutti gli altri.
  - **Importazione via Username Letterboxd**: inserisci il tuo username per scaricare e unire automaticamente la tua watchlist pubblica.
  - **Aggiunta manuale rapida**: aggiungi al volo qualsiasi film per verificarne subito la disponibilità e registrarlo nel CSV.
- **Disponibilità JustWatch Italia**:
  - Interroga in tempo reale le offerte per l'Italia (`country: IT`).
  - Trova i link diretti per avviare la riproduzione del film sulle piattaforme.
  - Recupera locandine ad alta definizione, voto IMDb, anno di uscita e generi.
- **Supporto Piattaforme Italiane & Internazionali**:
  - **Gratuite in Italia (senza abbonamento)**: Rai Play, Mediaset Infinity, Pluto TV, Serially, Plex, Arte, Rakuten TV Free, ecc.
  - **Abbonamenti Principali**: Netflix, Amazon Prime Video, Disney+, Now TV / NOW, Timvision, Apple TV+, Paramount+, Infinity+, **HBO Max**.
  - **Cinema d'Autore & Canali Specializzati**: MUBI, Nexo Plus, MYmovies One, Discovery+, Crunchyroll, Lionsgate+, Sky Go, ecc.
- **Filtri Intelligenti**:
  - **Disponibili Subito**: mostra solo i film che puoi guardare adesso senza costi aggiuntivi (inclusi nei tuoi abbonamenti o gratis).
  - **Solo Gratis**: isola immediatamente i film fruibili gratuitamente (es. RaiPlay, Mediaset Infinity, Pluto TV).
  - **Tutti i Film**: include anche film al momento solo a noleggio/acquisto o non ancora in streaming.
  - **Non Disponibili**: per vedere cosa manca all'appello.
  - **Ricerca in tempo reale**: filtra istantaneamente per titolo.
  - **Filtro per Genere**: commedia, drammatico, animazione, thriller, ecc.
- **Ordinamento Flessibile**:
  - **Ordine di aggiunta nella Watchlist** (dal più recente o dal primo aggiunto).
  - **Anno di rilascio del film** (più recente / più vecchio).
  - **Voto IMDb** (dal migliore al peggiore).
  - **Titolo alfabetico** (A-Z).
- **Gestione Abbonamenti Persistente**:
  - Seleziona facilmente le piattaforme a cui sei abbonato tramite un comodo pannello con loghi. Le tue preferenze restano salvate!
- **Database Locale & Cache SQLite**:
  - Salva i dati localmente in `data/letterboxd_watch.db`. Le consultazioni successive sono **istantanee** (0 millisecondi) senza rieseguire chiamate di rete, con possibilità di sincronizzare/aggiornare in ogni momento con il pulsante "Sincronizza".
- **Interfaccia Web Moderna & Modalità CLI**:
  - Web UI elegante in Dark Mode, ottimizzata per desktop e mobile.
  - Script CLI per generare report o interrogazioni direttamente dal terminale.

---

## Avvio Rapido

L'ambiente virtuale (`.venv`) è già stato creato nella cartella del progetto con tutte le dipendenze installate.

### 1. Avviare l'Applicazione Web
Dalla cartella del progetto esegui:

```powershell
.\.venv\Scripts\python.exe run.py
```

L'applicazione aprirà automaticamente il tuo browser all'indirizzo:
**http://127.0.0.1:8000**

---

### 2. Utilizzo da Terminale (CLI)

Se preferisci usare il terminale per consultare o esportare i film, è disponibile lo script `cli.py`:

```powershell
# Esegui scansione dal file CSV della watchlist
.\.venv\Scripts\python.exe cli.py --csv sample_watchlist.csv

# Specifica i tuoi abbonamenti e ordina per anno di rilascio
.\.venv\Scripts\python.exe cli.py --csv sample_watchlist.csv --platforms "Netflix,Amazon Prime Video,Rai Play" --sort release_year

# Mostra solo i film gratuiti
.\.venv\Scripts\python.exe cli.py --filter free --no-scan

# Mostra tutti i film ordinati per data di aggiunta
.\.venv\Scripts\python.exe cli.py --filter all --no-scan
```

---

## Struttura del Progetto

```text
├── app/
│   ├── config.py             # Configurazione e metadata piattaforme italiane e internazionali
│   ├── database.py           # Gestione database SQLite e query con filtri e ordinamento
│   ├── main.py               # Applicazione FastAPI e lifespan
│   ├── routers/
│   │   ├── api.py            # Endpoints REST (import CSV/username, filtri, scan, platforms)
│   │   └── views.py          # Render della pagina HTML
│   ├── services/
│   │   ├── justwatch.py      # Client JustWatch GraphQL per disponibilità streaming in Italia
│   │   ├── letterboxd.py     # Parser CSV Letterboxd e scraper watchlist pubblica
│   │   └── scanner.py        # Servizio di scansione asincrona con barra di avanzamento
│   ├── static/
│   │   ├── css/styles.css    # Stili CSS responsive e Dark Theme curato
│   │   └── js/app.js         # Logica interattiva frontend
│   └── templates/
│       └── index.html        # Template interfaccia utente
├── data/
│   └── letterboxd_watch.db   # Database SQLite locale con cache film e preferenze
├── run.py                    # Script di avvio del server Web
├── cli.py                    # Interfaccia da linea di comando (CLI)
├── sample_watchlist.csv      # File CSV di esempio per test rapidi
└── requirements.txt          # Dipendenze Python
```

---

## Come ottenere il file CSV da Letterboxd
1. Accedi a [Letterboxd.com](https://letterboxd.com).
2. Vai su **Settings** > **Import & Export** (oppure direttamente su `https://letterboxd.com/settings/data/`).
3. Clicca su **"Export Your Data"**: verrà scaricato un file ZIP contenente i tuoi dati.
4. All'interno dello ZIP troverai il file `watchlist.csv`: trascinalo direttamente nella finestra dell'applicazione web!
