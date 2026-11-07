import sqlite3
import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "letterboxd_watch.db")

def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS movies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        letterboxd_slug TEXT UNIQUE,
        letterboxd_uri TEXT,
        title TEXT NOT NULL,
        release_year INTEGER,
        date_added TEXT,
        status TEXT DEFAULT 'pending',
        jw_id TEXT,
        jw_title TEXT,
        jw_year INTEGER,
        poster_url TEXT,
        imdb_score REAL,
        genres TEXT,
        overview TEXT,
        updated_at TEXT
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS offers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        movie_id INTEGER NOT NULL,
        provider_name TEXT NOT NULL,
        provider_short_name TEXT,
        provider_id INTEGER,
        provider_icon TEXT,
        monetization_type TEXT NOT NULL,
        web_url TEXT,
        presentation_type TEXT,
        FOREIGN KEY (movie_id) REFERENCES movies(id) ON DELETE CASCADE
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    """)
    
    # Default settings if not already present
    default_platforms = [
        "Netflix",
        "Amazon Prime Video",
        "Rai Play",
        "Mediaset Infinity",
        "Disney Plus",
        "Now TV",
        "Timvision",
        "Pluto TV"
    ]
    cursor.execute("SELECT value FROM user_settings WHERE key = 'active_platforms'")
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO user_settings (key, value) VALUES (?, ?)",
            ("active_platforms", json.dumps(default_platforms))
        )
    
    conn.commit()
    conn.close()

def save_setting(key: str, value: Any):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO user_settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, json.dumps(value) if not isinstance(value, str) else value)
    )
    conn.commit()
    conn.close()

def get_setting(key: str, default: Any = None) -> Any:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM user_settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return default
    try:
        return json.loads(row["value"])
    except Exception:
        return row["value"]

def add_or_update_movie(
    letterboxd_slug: str,
    title: str,
    release_year: Optional[int] = None,
    letterboxd_uri: Optional[str] = None,
    date_added: Optional[str] = None
) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.now().isoformat()
    
    cursor.execute(
        """
        INSERT INTO movies (letterboxd_slug, letterboxd_uri, title, release_year, date_added, status, updated_at)
        VALUES (?, ?, ?, ?, ?, 'pending', ?)
        ON CONFLICT(letterboxd_slug) DO UPDATE SET
            title = excluded.title,
            release_year = COALESCE(excluded.release_year, movies.release_year),
            letterboxd_uri = COALESCE(excluded.letterboxd_uri, movies.letterboxd_uri),
            date_added = COALESCE(excluded.date_added, movies.date_added)
        """,
        (letterboxd_slug, letterboxd_uri, title, release_year, date_added, now_str)
    )
    conn.commit()
    cursor.execute("SELECT id FROM movies WHERE letterboxd_slug = ?", (letterboxd_slug,))
    movie_id = cursor.fetchone()["id"]
    conn.close()
    return movie_id

def update_movie_justwatch_data(
    movie_id: int,
    status: str,
    jw_id: Optional[str] = None,
    jw_title: Optional[str] = None,
    jw_year: Optional[int] = None,
    poster_url: Optional[str] = None,
    imdb_score: Optional[float] = None,
    genres: Optional[List[str]] = None,
    overview: Optional[str] = None,
    offers: Optional[List[Dict[str, Any]]] = None
):
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.now().isoformat()
    
    genres_json = json.dumps(genres or [], ensure_ascii=False)
    
    cursor.execute(
        """
        UPDATE movies
        SET status = ?,
            jw_id = ?,
            jw_title = ?,
            jw_year = ?,
            poster_url = ?,
            imdb_score = ?,
            genres = ?,
            overview = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (status, jw_id, jw_title, jw_year, poster_url, imdb_score, genres_json, overview, now_str, movie_id)
    )
    
    # Replace offers
    cursor.execute("DELETE FROM offers WHERE movie_id = ?", (movie_id,))
    if offers:
        for off in offers:
            cursor.execute(
                """
                INSERT INTO offers (
                    movie_id, provider_name, provider_short_name, provider_id,
                    provider_icon, monetization_type, web_url, presentation_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    movie_id,
                    off.get("provider_name"),
                    off.get("provider_short_name"),
                    off.get("provider_id"),
                    off.get("provider_icon"),
                    off.get("monetization_type"),
                    off.get("web_url"),
                    off.get("presentation_type")
                )
            )
            
    conn.commit()
    conn.close()

def get_movies(
    filter_mode: str = "available",  # 'all', 'available', 'free', 'not_available'
    active_platforms: Optional[List[str]] = None,
    sort_by: str = "date_added",     # 'date_added', 'release_year', 'imdb_score', 'title'
    sort_order: str = "desc",        # 'asc', 'desc'
    search: Optional[str] = None,
    genre: Optional[str] = None
) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    
    # Fetch all movies
    cursor.execute("SELECT * FROM movies")
    movies_rows = cursor.fetchall()
    
    # Fetch all offers
    cursor.execute("SELECT * FROM offers")
    offers_rows = cursor.fetchall()
    conn.close()
    
    # Map offers to movies
    offers_by_movie = {}
    for o in offers_rows:
        mid = o["movie_id"]
        if mid not in offers_by_movie:
            offers_by_movie[mid] = []
        offers_by_movie[mid].append(dict(o))
        
    results = []
    
    user_platforms_lower = [p.lower().strip() for p in (active_platforms or [])]
    
    for m in movies_rows:
        movie = dict(m)
        mid = movie["id"]
        movie_offers = offers_by_movie.get(mid, [])
        
        # Deduplicate offers by provider and monetization
        unique_offers = []
        seen_keys = set()
        for off in movie_offers:
            key = (off["provider_name"].lower(), off["monetization_type"])
            if key not in seen_keys:
                seen_keys.add(key)
                unique_offers.append(off)
                
        movie["offers"] = unique_offers
        try:
            movie["genres"] = json.loads(movie["genres"]) if movie["genres"] else []
        except Exception:
            movie["genres"] = []
            
        # Group offers into categories
        flatrate_user = []
        flatrate_other = []
        free_offers = []
        rent_buy_offers = []
        
        for off in unique_offers:
            pname = off["provider_name"]
            mtype = off["monetization_type"]
            is_user_platform = any(up in pname.lower() or pname.lower() in up for up in user_platforms_lower)
            
            if mtype in ("FREE", "ADS"):
                free_offers.append(off)
            elif mtype == "FLATRATE":
                if is_user_platform:
                    flatrate_user.append(off)
                else:
                    flatrate_other.append(off)
            elif mtype in ("RENT", "BUY"):
                rent_buy_offers.append(off)
                
        movie["flatrate_user_offers"] = flatrate_user
        movie["flatrate_other_offers"] = flatrate_other
        movie["free_offers"] = free_offers
        movie["rent_buy_offers"] = rent_buy_offers
        
        movie["is_available_now"] = (len(flatrate_user) > 0 or len(free_offers) > 0)
        movie["has_free"] = (len(free_offers) > 0)
        
        # Apply filters
        if filter_mode == "available" and not movie["is_available_now"]:
            continue
        elif filter_mode == "free" and not movie["has_free"]:
            continue
        elif filter_mode == "not_available" and movie["is_available_now"]:
            continue
            
        if search:
            query = search.lower().strip()
            title_match = (query in (movie["title"] or "").lower()) or (query in (movie["jw_title"] or "").lower())
            if not title_match:
                continue
                
        if genre and genre != "all":
            if not any(genre.lower() == g.lower() for g in movie["genres"]):
                continue
                
        results.append(movie)
        
    # Sort
    def get_sort_key(item):
        if sort_by == "release_year":
            val = item.get("release_year") or item.get("jw_year") or 0
            return (val if val is not None else 0)
        elif sort_by == "imdb_score":
            val = item.get("imdb_score")
            return (val if val is not None else 0.0)
        elif sort_by == "title":
            return (item.get("title") or "").lower()
        else: # date_added (or default)
            val = item.get("date_added") or ""
            return val
            
    reverse = (sort_order.lower() == "desc")
    results.sort(key=get_sort_key, reverse=reverse)
    return results

def get_stats(active_platforms: Optional[List[str]] = None) -> Dict[str, Any]:
    all_movies = get_movies(filter_mode="all", active_platforms=active_platforms)
    total = len(all_movies)
    available_now = sum(1 for m in all_movies if m["is_available_now"])
    free_count = sum(1 for m in all_movies if m["has_free"])
    sub_count = sum(1 for m in all_movies if len(m["flatrate_user_offers"]) > 0 and not m["has_free"])
    pending = sum(1 for m in all_movies if m["status"] == "pending")
    
    # Collect all available genres
    genres_set = set()
    for m in all_movies:
        for g in m.get("genres", []):
            if g:
                genres_set.add(g)
                
    return {
        "total": total,
        "available_now": available_now,
        "free_count": free_count,
        "sub_count": sub_count,
        "not_available": total - available_now,
        "pending": pending,
        "genres": sorted(list(genres_set))
    }

def clear_all_movies():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM offers")
    cursor.execute("DELETE FROM movies")
    conn.commit()
    conn.close()
