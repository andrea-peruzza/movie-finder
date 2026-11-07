import argparse
import asyncio
import sys
import os
from typing import List

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Ensure app package is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import init_db, add_or_update_movie, update_movie_justwatch_data, get_movies
from app.services.letterboxd import (
    parse_letterboxd_csv,
    scrape_letterboxd_user_watchlist,
    merge_and_save_master_csv
)
from app.services.justwatch import search_justwatch

async def process_films(movies_data: List[dict]):
    import httpx
    # Pre-check how many are new
    to_scan = []
    already_done = 0
    for m in movies_data:
        title = m["title"]
        year = m.get("release_year")
        mid, is_new = add_or_update_movie(
            letterboxd_slug=m["letterboxd_slug"],
            title=title,
            release_year=year,
            letterboxd_uri=m.get("letterboxd_uri"),
            date_added=m.get("date_added")
        )
        if is_new:
            to_scan.append((mid, m))
        else:
            already_done += 1
            
    if not to_scan:
        print(f"⚡ Tutti i {already_done} film sono già stati verificati in precedenza. Nessuna nuova ricerca JustWatch necessaria.")
        return

    print(f"\n🔍 Ricerca su JustWatch Italia in corso per {len(to_scan)} nuovi film ({already_done} già presenti e saltati)...")
    async with httpx.AsyncClient(timeout=12.0) as client:
        for idx, (mid, m) in enumerate(to_scan, 1):
            title = m["title"]
            year = m.get("release_year")
            print(f"[{idx}/{len(to_scan)}] Verifico: {title} ({year or 'N/A'})...", end=" ", flush=True)
            res = await search_justwatch(title, year, client=client)
            if res:
                update_movie_justwatch_data(
                    movie_id=mid,
                    status="matched",
                    jw_id=res["jw_id"],
                    jw_title=res["jw_title"],
                    jw_year=res["jw_year"],
                    poster_url=res["poster_url"],
                    imdb_score=res["imdb_score"],
                    genres=res["genres"],
                    overview=res["overview"],
                    offers=res["offers"]
                )
                avail = [o["provider_name"] for o in res["offers"] if o["monetization_type"] in ("FLATRATE", "FREE", "ADS")]
                if avail:
                    print(f"✅ Trovato su: {', '.join(set(avail))}")
                else:
                    print("⚠️ Solo noleggio/acquisto o non in streaming")
            else:
                update_movie_justwatch_data(movie_id=mid, status="not_found")
                print("❌ Non trovato su JustWatch")
            await asyncio.sleep(0.18)

def print_results(filter_mode: str, platforms: List[str], sort_by: str, sort_order: str):
    movies = get_movies(
        filter_mode=filter_mode,
        active_platforms=platforms,
        sort_by=sort_by,
        sort_order=sort_order
    )
    
    print("\n" + "=" * 80)
    print(f"🎬 RISULTATI ({len(movies)} FILM TROVATI)")
    print(f"   Filtro: {filter_mode} | Ordinamento: {sort_by} ({sort_order})")
    print(f"   Piattaforme attive: {', '.join(platforms)}")
    print("=" * 80)
    
    if not movies:
        print("Nessun film corrispondente ai criteri selezionati.")
        return
        
    for m in movies:
        title = m.get("jw_title") or m.get("title")
        year = m.get("release_year") or m.get("jw_year") or "N/A"
        imdb = f"⭐ {m.get('imdb_score'):.1f}" if m.get("imdb_score") else ""
        date_add = f"(Aggiunto: {m.get('date_added')})" if m.get("date_added") else ""
        
        print(f"\n🎥 {title} ({year}) {imdb} {date_add}")
        
        # User flatrate
        if m.get("flatrate_user_offers"):
            subs = [f"{o['provider_name']} [Abbonamento]" for o in m["flatrate_user_offers"]]
            print(f"   🍿 Tuoi Abbonamenti: {', '.join(subs)}")
            
        # Free
        if m.get("free_offers"):
            frees = [f"{o['provider_name']} [GRATIS]" for o in m["free_offers"]]
            print(f"   🆓 Gratis: {', '.join(frees)}")
            
        # Other flatrate
        if m.get("flatrate_other_offers") and not m.get("is_available_now"):
            others = [o['provider_name'] for o in m["flatrate_other_offers"]]
            print(f"   🔒 Altri abbonamenti non attivi: {', '.join(set(others))}")
            
        if not m.get("is_available_now") and m.get("rent_buy_offers"):
            print(f"   💳 Solo Noleggio/Acquisto ({len(m['rent_buy_offers'])} piattaforme)")
            
    print("\n" + "=" * 80)

def main():
    parser = argparse.ArgumentParser(description="Letterboxd & JustWatch Italia — Watchlist Streaming Finder")
    parser.add_argument("--csv", type=str, help="Percorso del file watchlist.csv esportato da Letterboxd")
    parser.add_argument("--username", type=str, help="Username Letterboxd per scraping pubblico")
    parser.add_argument(
        "--platforms",
        type=str,
        default="Netflix,Amazon Prime Video,Rai Play,Mediaset Infinity,Disney Plus,Now TV,Timvision,HBO Max,Pluto TV",
        help="Piattaforme a cui sei iscritto (separate da virgola)"
    )
    parser.add_argument("--filter", type=str, choices=["available", "free", "all", "not_available"], default="available", help="Filtro disponibilità")
    parser.add_argument("--sort", type=str, choices=["date_added", "release_year", "imdb_score", "title"], default="date_added", help="Campo di ordinamento")
    parser.add_argument("--order", type=str, choices=["asc", "desc"], default="desc", help="Direzione ordinamento")
    parser.add_argument("--no-scan", action="store_true", help="Non interrogare JustWatch, usa solo il database locale")
    
    args = parser.parse_args()
    init_db()
    
    platforms_list = [p.strip() for p in args.platforms.split(",") if p.strip()]
    
    if args.csv:
        if not os.path.exists(args.csv):
            print(f"Errore: File '{args.csv}' non trovato.")
            sys.exit(1)
        with open(args.csv, "r", encoding="utf-8-sig") as f:
            content = f.read()
        target_path, truly_new, combined, dups = merge_and_save_master_csv(content)
        print(f"Aggiornato file master '{os.path.basename(target_path)}' ({len(combined)} film totali, {len(truly_new)} nuovi, {dups} duplicati esclusi).")
        if not args.no_scan:
            asyncio.run(process_films(combined))
    elif args.username:
        print(f"Scaricamento della watchlist di @{args.username} da Letterboxd...")
        try:
            movies = scrape_letterboxd_user_watchlist(args.username)
            print(f"Trovati {len(movies)} film per l'utente @{args.username}.")
            if not args.no_scan:
                asyncio.run(process_films(movies))
        except Exception as e:
            print(f"Errore durante lo scaricamento: {e}")
            sys.exit(1)
            
    print_results(args.filter, platforms_list, args.sort, args.order)

if __name__ == "__main__":
    main()
