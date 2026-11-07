# Movie Finder
> Quickly find which movies from your Letterboxd watchlist are available for **immediate streaming in Italy** (on your subscription services or for free).

---

## Main Features

- **Letterboxd Integration & Incremental CSV Management**:
  - **1-Click Import via `watchlist.csv` file**: exported from Letterboxd (*Settings > Import & Export > Export Your Data*).
  - **Automatic Merge and Deduplication**: each newly imported CSV file is automatically merged with the `watchlist.csv` file present in the folder. If there are multiple rows for the same movie released in the same year, only **one row** is kept.
  - **Smart Selective Scan**: the JustWatch search is launched **exclusively for movies not present in the previous import**, preserving the results and offers already verified for all the others.
  - **Import via Letterboxd Username**: enter your username to automatically download and merge your public watchlist.
  - **Quick manual addition**: add any movie on the fly to immediately check its availability and record it in the CSV.
- **JustWatch Italy Availability**:
  - Queries real-time offers for Italy (`country: IT`).
  - Finds direct links to start playing the movie on the platforms.
  - Retrieves high-definition posters, IMDb rating, release year, and genres.
- **Support for Italian & International Platforms**:
  - **Free in Italy (no subscription)**: Rai Play, Mediaset Infinity, Pluto TV, Serially, Plex, Arte, Rakuten TV Free, etc.
  - **Main Subscriptions**: Netflix, Amazon Prime Video, Disney+, Now TV / NOW, Timvision, Apple TV+, Paramount+, Infinity+, **HBO Max**.
  - **Art-house Cinema & Specialized Channels**: MUBI, Nexo Plus, MYmovies One, Discovery+, Crunchyroll, Lionsgate+, Sky Go, etc.
- **Smart Filters**:
  - **Available Now**: shows only movies you can watch right now at no extra cost (included in your subscriptions or free).
  - **Free Only**: instantly isolates movies available for free (e.g., RaiPlay, Mediaset Infinity, Pluto TV).
  - **All Movies**: also includes movies currently only available for rent/purchase or not yet streaming.
  - **Not Available**: to see what is missing.
  - **Real-time search**: instantly filters by title.
  - **Genre Filter**: comedy, drama, animation, thriller, etc.
- **Flexible Sorting**:
  - **Order of addition to the Watchlist** (from newest or oldest added).
  - **Movie release year** (newest / oldest).
  - **IMDb Rating** (best to worst).
  - **Alphabetical title** (A-Z).
- **Persistent Subscriptions Management**:
  - Easily select the platforms you are subscribed to via a convenient panel with logos. Your preferences are saved!
- **Local Database & SQLite Cache**:
  - Saves data locally in `data/letterboxd_watch.db`. Subsequent queries are **instantaneous** (0 milliseconds) without re-running network calls, with the ability to synchronize/update at any time using the "Sync" button.
- **Modern Web Interface & CLI Mode**:
  - Elegant Web UI in Dark Mode, optimized for desktop and mobile.
  - CLI scripts to generate reports or queries directly from the terminal.

---

## Quick Start

The virtual environment (`.venv`) has already been created in the project folder with all dependencies installed.

### 1. Start the Web Application
From the project folder, run:

```powershell
.\.venv\Scripts\python.exe run.py
```

The application will automatically open your browser at:
**http://127.0.0.1:8000**

---

### 2. Terminal Usage (CLI)

If you prefer to use the terminal to consult or export movies, the `cli.py` script is available:

```powershell
# Run scan from the watchlist CSV file
.\.venv\Scripts\python.exe cli.py --csv sample_watchlist.csv

# Specify your subscriptions and sort by release year
.\.venv\Scripts\python.exe cli.py --csv sample_watchlist.csv --platforms "Netflix,Amazon Prime Video,Rai Play" --sort release_year

# Show only free movies
.\.venv\Scripts\python.exe cli.py --filter free --no-scan

# Show all movies sorted by date added
.\.venv\Scripts\python.exe cli.py --filter all --no-scan
```

---

## Project Structure

```text
├── app/
│   ├── config.py             # Configuration and metadata for Italian and international platforms
│   ├── database.py           # SQLite database management and queries with filters and sorting
│   ├── main.py               # FastAPI application and lifespan
│   ├── routers/
│   │   ├── api.py            # REST Endpoints (CSV/username import, filters, scan, platforms)
│   │   └── views.py          # HTML page rendering
│   ├── services/
│   │   ├── justwatch.py      # JustWatch GraphQL client for streaming availability in Italy
│   │   ├── letterboxd.py     # Letterboxd CSV parser and public watchlist scraper
│   │   └── scanner.py        # Asynchronous scanning service with progress bar
│   ├── static/
│   │   ├── css/styles.css    # Responsive CSS styles and curated Dark Theme
│   │   └── js/app.js         # Interactive frontend logic
│   └── templates/
│       └── index.html        # User interface template
├── data/
│   └── letterboxd_watch.db   # Local SQLite database with movie cache and preferences
├── run.py                    # Web server startup script
├── cli.py                    # Command Line Interface (CLI)
├── sample_watchlist.csv      # Sample CSV file for quick testing
└── requirements.txt          # Python dependencies
```

---

## How to get the CSV file from Letterboxd
1. Log in to [Letterboxd.com](https://letterboxd.com).
2. Go to **Settings** > **Import & Export** (or directly to `https://letterboxd.com/settings/data/`).
3. Click on **"Export Your Data"**: a ZIP file containing your data will be downloaded.
4. Inside the ZIP you will find the `watchlist.csv` file: drag it directly into the web application window!