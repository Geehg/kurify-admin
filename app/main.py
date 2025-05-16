
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
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
    db = load_db()
    return templates.TemplateResponse("index.html", {"request": request, "db": db})

@app.get("/results", response_class=HTMLResponse)
async def view_results(request: Request):
    db = load_db()
    return templates.TemplateResponse("results.html", {"request": request, "db": db})

@app.get("/results.json", response_class=JSONResponse)
async def view_results_json():
    db = load_db()
    return db
