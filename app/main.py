
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import json
import os

app = FastAPI()
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

DB_PATH = "app/fingerprint_db.json"

def load_db():
    if os.path.exists(DB_PATH):
        with open(DB_PATH, "r") as f:
            return json.load(f)
    return {}

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("console.html", {"request": request, "active_tab": "home", "db": load_db()})

@app.get("/results", response_class=HTMLResponse)
async def results(request: Request):
    return templates.TemplateResponse("console.html", {"request": request, "active_tab": "results", "db": load_db()})

@app.get("/results.json", response_class=JSONResponse)
async def results_json():
    return load_db()
