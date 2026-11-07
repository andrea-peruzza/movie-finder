import csv
import io
import os
import re
from typing import List, Dict, Any, Optional, Tuple
from bs4 import BeautifulSoup
from curl_cffi import requests

def clean_film_key(name: str, year: Any) -> Tuple[str, Optional[int]]:
    """
    Returns a normalized key (clean_title, year) used to identify a movie.
    """
    clean_name = re.sub(r'\s+', ' ', (name or "").strip().lower())
    clean_year = None
    if year is not None:
        y_str = str(year).strip()
        if y_str.isdigit():
            clean_year = int(y_str)
    return (clean_name, clean_year)

def get_project_root_dir() -> str:
    # app/services/letterboxd.py -> parent x 3 is project root
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_master_csv_path() -> str:
    """
    Finds the master CSV file in the project folder.
    Prioritizes watchlist.csv, then any existing .csv in root (e.g. sample_watchlist.csv).
    """
    root_dir = get_project_root_dir()
    primary = os.path.join(root_dir, "watchlist.csv")
    if os.path.exists(primary):
        return primary
        
    for f in os.listdir(root_dir):
        if f.endswith(".csv") and not f.startswith("."):
            return os.path.join(root_dir, f)
            
    return primary

def parse_letterboxd_csv_raw(csv_content: str) -> List[Dict[str, str]]:
    """
    Parses Letterboxd CSV content into standardized raw records:
    {"Date": ..., "Name": ..., "Year": ..., "Letterboxd URI": ...}
    """
    records = []
    if not csv_content or not csv_content.strip():
        return records
        
    f = io.StringIO(csv_content.strip())
    reader = csv.DictReader(f)
    if not reader.fieldnames:
        return records

    date_col = next((c for c in reader.fieldnames if c.strip().lower() in ("date", "added")), None)
    name_col = next((c for c in reader.fieldnames if c.strip().lower() in ("name", "title")), None)
    year_col = next((c for c in reader.fieldnames if c.strip().lower() in ("year", "release year")), None)
    uri_col = next((c for c in reader.fieldnames if any(k in c.strip().lower() for k in ("uri", "url", "link"))), None)

    for row in reader:
        name = row.get(name_col, "").strip() if name_col else ""
        if not name:
            continue
        year_str = row.get(year_col, "").strip() if year_col else ""
        date_str = row.get(date_col, "").strip() if date_col else ""
        uri = row.get(uri_col, "").strip() if uri_col else ""

        records.append({
            "Date": date_str,
            "Name": name,
            "Year": year_str,
            "Letterboxd URI": uri
        })
    return records

def raw_record_to_movie_dict(rec: Dict[str, str]) -> Dict[str, Any]:
    name = rec.get("Name", "").strip()
    year_str = rec.get("Year", "").strip()
    year = int(year_str) if year_str.isdigit() else None
    date_str = rec.get("Date", "").strip()
    uri = rec.get("Letterboxd URI", "").strip()

    if uri and "boxd.it" not in uri and "/film/" in uri:
        slug = uri.split("/film/")[-1].strip("/")
    elif uri:
        slug = re.sub(r'[^a-zA-Z0-9]+', '-', f"{name}-{year or ''}").strip('-').lower()
    else:
        slug = re.sub(r'[^a-zA-Z0-9]+', '-', f"{name}-{year or ''}").strip('-').lower()

    return {
        "title": name,
        "release_year": year,
        "date_added": date_str or None,
        "letterboxd_uri": uri or None,
        "letterboxd_slug": slug
    }

def parse_letterboxd_csv(csv_content: str) -> List[Dict[str, Any]]:
    """
    Parses a Letterboxd watchlist.csv content into structured movie dicts.
    """
    raw_records = parse_letterboxd_csv_raw(csv_content)
    return [raw_record_to_movie_dict(r) for r in raw_records]

def merge_and_save_master_csv(
    new_csv_content: str,
    target_csv_path: Optional[str] = None
) -> Tuple[str, List[Dict[str, Any]], List[Dict[str, Any]], int]:
    """
    Merges newly imported CSV rows into the master CSV file already present in the folder.
    Deduplication rule: Keeps only one row if multiple rows present the same movie
    released in the same year (title + release year).

    Returns:
    (target_csv_path, truly_new_movies, combined_movies, duplicate_count)
    """
    if not target_csv_path:
        target_csv_path = get_master_csv_path()

    existing_records = []
    if os.path.exists(target_csv_path):
        try:
            with open(target_csv_path, "r", encoding="utf-8-sig") as f:
                existing_records = parse_letterboxd_csv_raw(f.read())
        except Exception as e:
            print(f"Warning reading existing CSV {target_csv_path}: {e}")

    new_records = parse_letterboxd_csv_raw(new_csv_content)

    seen_keys = set()
    combined_records = []

    # 1. Add existing records, deduplicating any duplicate within the existing file
    for r in existing_records:
        k = clean_film_key(r.get("Name", ""), r.get("Year", ""))
        if not k[0]:
            continue
        if k not in seen_keys:
            seen_keys.add(k)
            combined_records.append(r)

    # 2. Append new records only if (title, year) was not already present
    truly_new_records = []
    duplicate_count = 0

    for r in new_records:
        k = clean_film_key(r.get("Name", ""), r.get("Year", ""))
        if not k[0]:
            continue
        if k in seen_keys:
            duplicate_count += 1
        else:
            seen_keys.add(k)
            combined_records.append(r)
            truly_new_records.append(r)

    # 3. Write back the merged, deduplicated CSV file
    os.makedirs(os.path.dirname(os.path.abspath(target_csv_path)), exist_ok=True)
    with open(target_csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["Date", "Name", "Year", "Letterboxd URI"])
        writer.writeheader()
        for r in combined_records:
            writer.writerow({
                "Date": r.get("Date") or "",
                "Name": r.get("Name") or "",
                "Year": r.get("Year") or "",
                "Letterboxd URI": r.get("Letterboxd URI") or ""
            })

    # Also keep root watchlist.csv updated if target was a different name
    root_watchlist = os.path.join(get_project_root_dir(), "watchlist.csv")
    if os.path.abspath(target_csv_path) != os.path.abspath(root_watchlist):
        try:
            with open(root_watchlist, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["Date", "Name", "Year", "Letterboxd URI"])
                writer.writeheader()
                for r in combined_records:
                    writer.writerow({
                        "Date": r.get("Date") or "",
                        "Name": r.get("Name") or "",
                        "Year": r.get("Year") or "",
                        "Letterboxd URI": r.get("Letterboxd URI") or ""
                    })
        except Exception as e:
            print(f"Warning syncing root watchlist.csv: {e}")

    truly_new_movies = [raw_record_to_movie_dict(r) for r in truly_new_records]
    combined_movies = [raw_record_to_movie_dict(r) for r in combined_records]

    return target_csv_path, truly_new_movies, combined_movies, duplicate_count

def scrape_letterboxd_user_watchlist(
    username: str,
    max_pages: int = 15,
    on_page_callback = None
) -> List[Dict[str, Any]]:
    """
    Scrapes a user's public watchlist from Letterboxd.
    Supports multi-page watchlists and reports progress.
    """
    username = username.strip().lower()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    
    movies = []
    seen_slugs = set()
    current_page = 1
    total_pages = 1
    
    session = requests.Session()
    
    while current_page <= total_pages and current_page <= max_pages:
        url = f"https://letterboxd.com/{username}/watchlist/page/{current_page}/"
        try:
            resp = session.get(url, headers=headers, impersonate="safari15_5", timeout=15)
            if resp.status_code == 404:
                raise ValueError(f"Watchlist non trovata o utente '{username}' inesistente.")
            if resp.status_code == 403:
                raise PermissionError("Accesso bloccato da protezione web Letterboxd. Ti consigliamo di importare il file watchlist.csv esportato da Letterboxd!")
            if resp.status_code != 200:
                raise ValueError(f"Errore Letterboxd (HTTP {resp.status_code})")
                
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Detect total pages on first page
            if current_page == 1:
                paginate = soup.select(".paginate-pages a, .pagination a")
                page_nums = []
                for a in paginate:
                    txt = a.text.strip()
                    if txt.isdigit():
                        page_nums.append(int(txt))
                if page_nums:
                    total_pages = max(page_nums)
                    
            # Parse poster items
            posters = soup.select("li.poster-container, ul.poster-list li")
            for p in posters:
                film_div = p.find("div", class_="film-poster") or p.find(attrs={"data-film-slug": True})
                if not film_div:
                    continue
                    
                slug = film_div.get("data-film-slug") or film_div.get("data-target-link", "").replace("/film/", "").strip("/")
                if not slug or slug in seen_slugs:
                    continue
                seen_slugs.add(slug)
                
                # Title & Year
                img = film_div.find("img")
                title = film_div.get("data-film-name") or (img.get("alt") if img else "") or slug.replace("-", " ").title()
                year_str = film_div.get("data-film-release-year")
                year = int(year_str) if year_str and year_str.isdigit() else None
                
                uri = f"https://letterboxd.com/film/{slug}/"
                
                movies.append({
                    "title": title,
                    "release_year": year,
                    "date_added": None,
                    "letterboxd_uri": uri,
                    "letterboxd_slug": slug
                })
                
            if on_page_callback:
                on_page_callback(current_page, total_pages, len(movies))
                
            current_page += 1
            
        except Exception as e:
            if current_page == 1:
                raise e
            break
            
    return movies
