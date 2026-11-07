import os
import io
import csv
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from typing import List, Optional
from pydantic import BaseModel
import json

from app.database import (
    get_setting, save_setting, add_or_update_movie, get_movies,
    get_stats, clear_all_movies, get_connection
)
from app.config import KNOWN_PROVIDERS
from app.services.letterboxd import (
    parse_letterboxd_csv,
    scrape_letterboxd_user_watchlist,
    merge_and_save_master_csv
)
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
        "Disney Plus", "Now TV", "Timvision", "HBO Max", "Pluto TV"
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
        
        target_csv_path, truly_new_movies, combined_movies, duplicate_count = merge_and_save_master_csv(csv_text)
        
        if not combined_movies:
            raise HTTPException(
                status_code=400,
                detail="Nessun film valido trovato nel file CSV. Assicurati che sia il file 'watchlist.csv' esportato da Letterboxd."
            )
            
        newly_pending_count = 0
        already_present_count = 0
        
        for m in combined_movies:
            _, is_new = add_or_update_movie(
                letterboxd_slug=m["letterboxd_slug"],
                title=m["title"],
                release_year=m["release_year"],
                letterboxd_uri=m["letterboxd_uri"],
                date_added=m["date_added"]
            )
            if is_new:
                newly_pending_count += 1
            else:
                already_present_count += 1
                
        # Start JustWatch scan ONLY for films not present in the previous import
        if newly_pending_count > 0 and auto_scan and not scanner_instance.is_scanning:
            background_tasks.add_task(scanner_instance.scan_all_pending)
            
        csv_filename = os.path.basename(target_csv_path)
        if newly_pending_count > 0:
            msg = f"Watchlist aggiornata in '{csv_filename}': {newly_pending_count} nuovi film aggiunti e in scansione JustWatch ({already_present_count} film già verificati mantenuti)."
        else:
            msg = f"Nessun nuovo film da scansionare: tutti i {already_present_count} film sono già presenti in '{csv_filename}'."
            
        if duplicate_count > 0:
            msg += f" {duplicate_count} righe duplicate dello stesso film/anno escluse."
            
        return {
            "status": "success",
            "message": msg,
            "target_csv": csv_filename,
            "total_count": len(combined_movies),
            "new_count": newly_pending_count,
            "already_present_count": already_present_count,
            "duplicates_omitted": duplicate_count,
            "auto_scan": auto_scan and newly_pending_count > 0
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
        movies = scrape_letterboxd_user_watchlist(username, max_pages=15)
        if not movies:
            return {
                "status": "warning",
                "message": f"Nessun film trovato nella watchlist di '{username}'. Assicurati che la watchlist sia pubblica.",
                "count": 0
            }
            
        csv_buffer = io.StringIO()
        writer = csv.DictWriter(csv_buffer, fieldnames=["Date", "Name", "Year", "Letterboxd URI"])
        writer.writeheader()
        for m in movies:
            writer.writerow({
                "Date": m.get("date_added") or "",
                "Name": m.get("title") or "",
                "Year": m.get("release_year") or "",
                "Letterboxd URI": m.get("letterboxd_uri") or ""
            })
            
        target_csv_path, truly_new, combined, duplicate_count = merge_and_save_master_csv(csv_buffer.getvalue())
        
        newly_pending = 0
        for m in combined:
            _, is_new = add_or_update_movie(
                letterboxd_slug=m["letterboxd_slug"],
                title=m["title"],
                release_year=m["release_year"],
                letterboxd_uri=m["letterboxd_uri"],
                date_added=m["date_added"]
            )
            if is_new:
                newly_pending += 1
                
        if newly_pending > 0 and auto_scan and not scanner_instance.is_scanning:
            background_tasks.add_task(scanner_instance.scan_all_pending)
            
        csv_filename = os.path.basename(target_csv_path)
        return {
            "status": "success",
            "message": f"Watchlist di @{username} integrata in '{csv_filename}': {newly_pending} nuovi film aggiunti e in scansione JustWatch.",
            "count": len(combined),
            "new_count": newly_pending
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
    
    # Append to master CSV file
    csv_buffer = io.StringIO()
    writer = csv.DictWriter(csv_buffer, fieldnames=["Date", "Name", "Year", "Letterboxd URI"])
    writer.writeheader()
    writer.writerow({
        "Date": datetime.now().strftime("%Y-%m-%d"),
        "Name": title,
        "Year": payload.year or "",
        "Letterboxd URI": f"https://letterboxd.com/film/{slug}/"
    })
    merge_and_save_master_csv(csv_buffer.getvalue())
    
    mid, is_new = add_or_update_movie(
        letterboxd_slug=slug,
        title=title,
        release_year=payload.year,
        date_added=datetime.now().strftime("%Y-%m-%d")
    )
    
    if is_new and auto_scan and not scanner_instance.is_scanning:
        background_tasks.add_task(scanner_instance.scan_all_pending)
        
    return {
        "status": "ok",
        "message": f"Aggiunto film: {title}" if is_new else f"Film già presente: {title}",
        "id": mid,
        "is_new": is_new
    }

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
