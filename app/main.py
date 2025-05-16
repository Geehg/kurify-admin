
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import librosa
import numpy as np
import uuid
import json
import os
import yt_dlp
import requests

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

def extract_fingerprint(wav_path):
    y, sr = librosa.load(wav_path, sr=22050)
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
    return np.mean(mfcc, axis=1).tolist()

def download_youtube_audio(youtube_url, output_path):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_path,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'wav',
            'preferredquality': '192',
        }],
        'quiet': True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([youtube_url])

def fetch_itunes_metadata(title, artist):
    query = f"{artist} {title}"
    resp = requests.get("https://itunes.apple.com/search", params={"term": query, "limit": 1})
    if resp.status_code == 200:
        results = resp.json().get("results", [])
        if results:
            return {
                "title": results[0].get("trackName", title),
                "artist": results[0].get("artistName", artist),
                "album": results[0].get("collectionName", ""),
                "cover": results[0].get("artworkUrl100", "").replace("100x100", "600x600"),
                "itunes_id": results[0].get("trackId", None),
                "url": results[0].get("trackViewUrl", "")
            }
    return {
        "title": title,
        "artist": artist,
        "album": "",
        "cover": "",
        "itunes_id": None,
        "url": ""
    }

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    db = load_db()
    return templates.TemplateResponse("index.html", {"request": request, "db": db})

@app.post("/register")
async def register_track(request: Request, title: str = Form(...), artist: str = Form(...), youtube_url: str = Form(...)):
    temp_path = "temp_audio.%(ext)s"
    wav_path = "temp_audio.wav"
    try:
        download_youtube_audio(youtube_url, temp_path)
        fingerprint = extract_fingerprint(wav_path)
        os.remove(wav_path)
        track_id = f"kurify_{uuid.uuid4().hex[:8]}"
        meta = fetch_itunes_metadata(title, artist)
        db = load_db()
        db[track_id] = {
            "title": meta["title"],
            "artist": meta["artist"],
            "album": meta["album"],
            "cover": meta["cover"],
            "itunes_id": meta["itunes_id"],
            "url": meta["url"],
            "fingerprint": fingerprint
        }
        save_db(db)
        return RedirectResponse("/", status_code=302)
    except Exception as e:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "error": str(e),
            "db": load_db()
        })

@app.get("/delete/{track_id}")
def delete_track(track_id: str):
    db = load_db()
    if track_id in db:
        del db[track_id]
        save_db(db)
    return RedirectResponse("/", status_code=302)
