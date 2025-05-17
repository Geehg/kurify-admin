
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

@app.get("/manage", response_class=HTMLResponse)
async def manage(request: Request):
    db = load_db()
    return templates.TemplateResponse("manage.html", {"request": request, "db": db})

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

@app.post("/delete/{track_id}")
async def delete_track(track_id: str):
    db = load_db()
    if track_id in db:
        del db[track_id]
        save_db(db)
    return RedirectResponse("/manage", status_code=302)

@app.get("/search", response_class=HTMLResponse)
async def search(request: Request):
    db = load_db()
    return templates.TemplateResponse("search.html", {"request": request, "db": db})

from collections import Counter

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    db = load_db()
    total = len(db)
    artist_counter = Counter()
    for item in db.values():
        artist_counter[item.get("artist", "Unknown")] += 1
    top_artists = artist_counter.most_common(5)
    max_count = top_artists[0][1] if top_artists else 1
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "total": total,
        "top_artists": top_artists,
        "max_count": max_count
    })


@app.post("/api/register")
async def api_register(youtube_url: str = Form(...)):
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
        return {"status": "success", "track_id": track_id, "meta": meta}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/track/{track_id}", response_class=JSONResponse)
async def api_get_track(track_id: str):
    db = load_db()
    if track_id in db:
        return db[track_id]
    return JSONResponse(content={"error": "track not found"}, status_code=404)


from fastapi import UploadFile
import tempfile

@app.post("/api/upload")
async def upload_file(file: UploadFile):
    try:
        suffix = "." + file.filename.split(".")[-1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name

        fingerprint = extract_fingerprint(tmp_path)
        os.remove(tmp_path)

        track_id = f"kurify_{uuid.uuid4().hex[:8]}"
        db = load_db()
        db[track_id] = {
            "title": "Unknown Title",
            "artist": "Unknown Artist",
            "album": "",
            "cover": "",
            "url": "",
            "fingerprint": fingerprint
        }
        save_db(db)
        return {"status": "success", "track_id": track_id}
    except Exception as e:
        return {"status": "error", "message": str(e)}
