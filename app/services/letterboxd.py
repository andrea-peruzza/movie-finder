import csv
import io
import re
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from curl_cffi import requests

def parse_letterboxd_csv(csv_content: str) -> List[Dict[str, Any]]:
    """
    Parses a Letterboxd watchlist.csv content.
    Standard Letterboxd CSV headers:
    Date, Name, Year, Letterboxd URI
    """
    movies = []
    f = io.StringIO(csv_content.strip())
    reader = csv.DictReader(f)
    
    # Handle possible BOM or case variation in headers
    fieldnames = [c.strip().lower() for c in (reader.fieldnames or [])]
    
    # Map column names
    date_col = next((c for c in reader.fieldnames if c.strip().lower() in ("date", "added")), None)
    name_col = next((c for c in reader.fieldnames if c.strip().lower() in ("name", "title")), None)
    year_col = next((c for c in reader.fieldnames if c.strip().lower() in ("year", "release year")), None)
    uri_col = next((c for c in reader.fieldnames if "uri" in c.strip().lower() or "url" in c.strip().lower() or "link" in c.strip().lower()), None)
    
    for row in reader:
        name = row.get(name_col, "").strip() if name_col else ""
        if not name:
            continue
            
        year_str = row.get(year_col, "").strip() if year_col else ""
        year = int(year_str) if year_str.isdigit() else None
        
        date_str = row.get(date_col, "").strip() if date_col else ""
        uri = row.get(uri_col, "").strip() if uri_col else ""
        
        # Determine slug
        if uri and "boxd.it" not in uri and "/film/" in uri:
            slug = uri.split("/film/")[-1].strip("/")
        elif uri:
            slug = re.sub(r'[^a-zA-Z0-9]+', '-', f"{name}-{year or ''}").strip('-').lower()
        else:
            slug = re.sub(r'[^a-zA-Z0-9]+', '-', f"{name}-{year or ''}").strip('-').lower()
            
        movies.append({
            "title": name,
            "release_year": year,
            "date_added": date_str,
            "letterboxd_uri": uri,
            "letterboxd_slug": slug
        })
        
    return movies

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
                    "date_added": None, # Letterboxd web doesn't show addition date on grid
                    "letterboxd_uri": uri,
                    "letterboxd_slug": slug
                })
                
            if on_page_callback:
                on_page_callback(current_page, total_pages, len(movies))
                
            current_page += 1
            
        except Exception as e:
            if current_page == 1:
                raise e
            break # stop on subsequent page errors
            
    return movies
