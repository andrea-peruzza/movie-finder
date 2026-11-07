import asyncio
import httpx
from typing import Dict, Any, List, Optional, Callable
from app.database import get_connection, update_movie_justwatch_data
from app.services.justwatch import search_justwatch

class ScannerService:
    def __init__(self):
        self.is_scanning = False
        self.current_index = 0
        self.total_movies = 0
        self.current_movie_title = ""
        self.last_status = "idle"
        self.listeners: List[Callable[[Dict[str, Any]], Any]] = []
        self._cancel_requested = False

    def get_progress(self) -> Dict[str, Any]:
        return {
            "is_scanning": self.is_scanning,
            "current": self.current_index,
            "total": self.total_movies,
            "percentage": round((self.current_index / self.total_movies * 100), 1) if self.total_movies > 0 else 0,
            "current_title": self.current_movie_title,
            "status": self.last_status
        }

    def cancel(self):
        self._cancel_requested = True

    async def scan_all_pending(self, force_refresh: bool = False):
        if self.is_scanning:
            return

        self.is_scanning = True
        self._cancel_requested = False
        self.last_status = "Iniziando scansione JustWatch..."

        conn = get_connection()
        cursor = conn.cursor()
        if force_refresh:
            cursor.execute("SELECT id, title, release_year, letterboxd_slug FROM movies")
        else:
            cursor.execute("SELECT id, title, release_year, letterboxd_slug FROM movies WHERE status = 'pending'")
        rows = cursor.fetchall()
        conn.close()

        movies_to_scan = [dict(r) for r in rows]
        self.total_movies = len(movies_to_scan)
        self.current_index = 0

        if not movies_to_scan:
            self.is_scanning = False
            self.last_status = "Tutti i film sono già stati sincronizzati."
            return

        async with httpx.AsyncClient(timeout=12.0) as client:
            for item in movies_to_scan:
                if self._cancel_requested:
                    self.last_status = "Scansione interrotta dall'utente."
                    break

                movie_id = item["id"]
                title = item["title"]
                year = item["release_year"]
                self.current_movie_title = f"{title} ({year})" if year else title
                self.current_index += 1
                self.last_status = f"Cercando su JustWatch ({self.current_index}/{self.total_movies}): {self.current_movie_title}"

                try:
                    result = await search_justwatch(title, year, client=client)
                    if result:
                        update_movie_justwatch_data(
                            movie_id=movie_id,
                            status="matched",
                            jw_id=result["jw_id"],
                            jw_title=result["jw_title"],
                            jw_year=result["jw_year"],
                            poster_url=result["poster_url"],
                            imdb_score=result["imdb_score"],
                            genres=result["genres"],
                            overview=result["overview"],
                            offers=result["offers"]
                        )
                    else:
                        update_movie_justwatch_data(
                            movie_id=movie_id,
                            status="not_found"
                        )
                except Exception as e:
                    print(f"Error scanning movie {title}: {e}")
                    update_movie_justwatch_data(movie_id=movie_id, status="error")

                # Small delay to respect JustWatch servers
                await asyncio.sleep(0.18)

        self.is_scanning = False
        self.last_status = "Scansione completata!"

scanner_instance = ScannerService()
