from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from typing import List, Optional
from pydantic import BaseModel
import json

from app.database import (
    get_setting, save_setting, add_or_update_movie, get_movies,
    get_stats, clear_all_movies, get_connection
)
from app.config import KNOWN_PROVIDERS
from app.services.letterboxd import parse_letterboxd_csv, scrape_letterboxd_user_watchlist
from app.services.scanner import scanner_instance

router = APIRouter(prefix="/api")

class PlatformsUpdateRequest(BaseModel):
    platforms: List[str]

class AddMovieRequest(BaseModel):
    title: str
    year: Optional[int] = None

class UsernameImportRequest(BaseModel):
    username: str

@router.get("/platforms")
def get_platforms():
    active = get_setting("active_platforms", [
        "Netflix", "Amazon Prime Video", "Rai Play", "Mediaset Infinity",
        "Disney Plus", "Now TV", "Timvision", "Pluto TV"
    ])
    active_set = {p.lower() for p in active}
    
    providers_with_status = []
    for p in KNOWN_PROVIDERS:
        p_copy = dict(p)
        p_copy["is_active"] = p["name"].lower() in active_set
        providers_with_status.append(p_copy)
        
    return {
        "providers": providers_with_status,
        "active_platforms": active
    }

@router.post("/platforms")
def update_platforms(payload: PlatformsUpdateRequest):
    save_setting("active_platforms", payload.platforms)
    return {"status": "ok", "active_platforms": payload.platforms}

@router.get("/watchlist/stats")
def fetch_stats():
    active = get_setting("active_platforms", [])
    return get_stats(active_platforms=active)

@router.get("/watchlist/movies")
def list_movies(
    filter_mode: str = "available",
    sort_by: str = "date_added",
    sort_order: str = "desc",
    search: Optional[str] = None,
    genre: Optional[str] = None
):
    active = get_setting("active_platforms", [])
    movies = get_movies(
        filter_mode=filter_mode,
        active_platforms=active,
        sort_by=sort_by,
        sort_order=sort_order,
        search=search,
        genre=genre
    )
    return {"movies": movies, "count": len(movies)}

@router.post("/watchlist/import-csv")
async def import_csv(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    auto_scan: bool = Form(True)
):
    try:
        content = await file.read()
        csv_text = content.decode("utf-8-sig", errors="replace")
        parsed_movies = parse_letterboxd_csv(csv_text)
        
        if not parsed_movies:
            raise HTTPException(status_code=400, detail="Nessun film valido trovato nel file CSV. Assicurati che sia il file 'watchlist.csv' esportato da Letterboxd.")
            
        added_count = 0
        for m in parsed_movies:
            add_or_update_movie(
                letterboxd_slug=m["letterboxd_slug"],
                title=m["title"],
                release_year=m["release_year"],
                letterboxd_uri=m["letterboxd_uri"],
                date_added=m["date_added"]
            )
            added_count += 1
            
        if auto_scan and not scanner_instance.is_scanning:
            background_tasks.add_task(scanner_instance.scan_all_pending)
            
        return {
            "status": "success",
            "message": f"Importati con successo {added_count} film dalla watchlist Letterboxd!",
            "count": added_count,
            "auto_scan": auto_scan
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore durante l'importazione: {str(e)}")

@router.post("/watchlist/import-username")
async def import_username(
    payload: UsernameImportRequest,
    background_tasks: BackgroundTasks,
    auto_scan: bool = True
):
    username = payload.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="Username Letterboxd non valido.")
        
    try:
        # Run scraper in executor or synchronous thread
        movies = scrape_letterboxd_user_watchlist(username, max_pages=15)
        if not movies:
            return {
                "status": "warning",
                "message": f"Nessun film trovato nella watchlist di '{username}'. Assicurati che la watchlist sia pubblica.",
                "count": 0
            }
            
        added_count = 0
        for m in movies:
            add_or_update_movie(
                letterboxd_slug=m["letterboxd_slug"],
                title=m["title"],
                release_year=m["release_year"],
                letterboxd_uri=m["letterboxd_uri"],
                date_added=m["date_added"]
            )
            added_count += 1
            
        if auto_scan and not scanner_instance.is_scanning:
            background_tasks.add_task(scanner_instance.scan_all_pending)
            
        return {
            "status": "success",
            "message": f"Trovati e aggiunti {added_count} film dalla watchlist di @{username}!",
            "count": added_count,
            "auto_scan": auto_scan
        }
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore scraping: {str(e)}")

@router.post("/watchlist/add-movie")
async def add_single_movie(
    payload: AddMovieRequest,
    background_tasks: BackgroundTasks,
    auto_scan: bool = True
):
    title = payload.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="Il titolo del film è obbligatorio.")
        
    slug = f"{title.lower()}-{payload.year or ''}".strip("-")
    mid = add_or_update_movie(
        letterboxd_slug=slug,
        title=title,
        release_year=payload.year,
        date_added=None
    )
    
    if auto_scan and not scanner_instance.is_scanning:
        background_tasks.add_task(scanner_instance.scan_all_pending)
        
    return {"status": "ok", "message": f"Aggiunto film: {title}", "id": mid}

@router.delete("/watchlist/clear")
def clear_watchlist():
    clear_all_movies()
    return {"status": "ok", "message": "Watchlist svuotata."}

@router.post("/scan/start")
def start_scan(background_tasks: BackgroundTasks, force: bool = False):
    if scanner_instance.is_scanning:
        return {"status": "already_running", "message": "Una scansione è già in corso."}
        
    background_tasks.add_task(scanner_instance.scan_all_pending, force_refresh=force)
    return {"status": "started", "message": "Scansione avviata!"}

@router.post("/scan/cancel")
def stop_scan():
    scanner_instance.cancel()
    return {"status": "cancelling", "message": "Richiesta interruzione inviata."}

@router.get("/scan/progress")
def get_scan_progress():
    return scanner_instance.get_progress()
