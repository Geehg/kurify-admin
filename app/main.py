
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import json, os, uuid, requests, yt_dlp
import librosa, numpy as np

app = FastAPI()
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")
DB_PATH = "app/fingerprint_db.json"

def load_db():
    if os.path.exists(DB_PATH):
        with open(DB_PATH, "r") as f:
            return json.load(f)
    return {}

def save_db(db):
    with open(DB_PATH, "w") as f:
        json.dump(db, f, indent=2)

def download_youtube_audio(url):
    filename = "temp_audio.%(ext)s"
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": filename,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "wav",
            "preferredquality": "192",
        }],
        "quiet": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
    return "temp_audio.wav", info.get("title")

def extract_fingerprint(wav_path):
    y, sr = librosa.load(wav_path, sr=22050)
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
    return np.mean(mfcc, axis=1).tolist()

def fetch_itunes_meta(query):
    response = requests.get("https://itunes.apple.com/search", params={"term": query, "limit": 1})
    if response.status_code == 200:
        results = response.json().get("results", [])
        if results:
            r = results[0]
            return {
                "title": r.get("trackName", query),
                "artist": r.get("artistName", ""),
                "album": r.get("collectionName", ""),
                "cover": r.get("artworkUrl100", "").replace("100x100", "600x600"),
                "url": r.get("trackViewUrl", "")
            }
    return {"title": query, "artist": "", "album": "", "cover": "", "url": ""}

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    db = load_db()
    return templates.TemplateResponse("console.html", {"request": request, "active_tab": "home", "db": db})

@app.get("/results", response_class=HTMLResponse)
async def results(request: Request):
    db = load_db()
    return templates.TemplateResponse("console.html", {"request": request, "active_tab": "results", "db": db})

@app.get("/results.json", response_class=JSONResponse)
async def results_json():
    return load_db()

@app.post("/register")
async def register_track(request: Request, youtube_url: str = Form(...)):
    try:
        wav_path, yt_title = download_youtube_audio(youtube_url)
        fingerprint = extract_fingerprint(wav_path)
        os.remove(wav_path)
        meta = fetch_itunes_meta(yt_title)
        track_id = f"kurify_{uuid.uuid4().hex[:8]}"
        db = load_db()
        db[track_id] = {
            "title": meta["title"],
            "artist": meta["artist"],
            "album": meta["album"],
            "cover": meta["cover"],
            "url": meta["url"],
            "fingerprint": fingerprint
        }
        save_db(db)
        return RedirectResponse("/results", status_code=302)
    except Exception as e:
        return templates.TemplateResponse("console.html", {
            "request": request,
            "active_tab": "home",
            "error": str(e),
            "db": load_db()
        })
