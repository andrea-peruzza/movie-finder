import uvicorn
import webbrowser
import sys
import threading
import time

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

def open_browser(port):
    time.sleep(1.2)
    webbrowser.open(f"http://127.0.0.1:{port}")

if __name__ == "__main__":
    port = 8000
    print("==================================================================")
    print("🎬 Letterboxd & JustWatch Italia — Watchlist Streaming Finder")
    print("==================================================================")
    print(f"Avvio del server su: http://127.0.0.1:{port}")
    print("Premi Ctrl+C nel terminale per arrestare.")
    print("==================================================================")
    
    # Auto-open browser
    if "--no-browser" not in sys.argv:
        threading.Thread(target=open_browser, args=(port,), daemon=True).start()
        
    uvicorn.run("app.main:app", host="127.0.0.1", port=port, reload=False, log_level="info")
