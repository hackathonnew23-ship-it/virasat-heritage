"""Virasat API (FastAPI). Run:  uvicorn app.main:app --reload   (from the backend/ directory)"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import config, services


@asynccontextmanager
async def lifespan(app):
    config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    services.startup()
    yield


app = FastAPI(title="Virasat Heritage API", version="1.0.0",
              description="Search, map, 3D-twin metadata and OCR for unstructured heritage archives.",
              lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class SiteIn(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    lat: float = Field(ge=6, le=38)
    lon: float = Field(ge=67, le=98)
    category: str = Field(pattern="^(Stepwell|Temple|Fort|Craft|Folklore)$")
    place: str = ""
    state: str = ""
    photo_count: int = Field(default=0, ge=0)
    native_name: str = ""
    model_type: str = "stepwell"
    description: str = ""


class NoteIn(BaseModel):
    body: str = Field(min_length=2, max_length=4000)
    author: str = "explorer"
    photos_added: int = Field(default=0, ge=0)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/sites")
def list_sites():
    return services.sites()


@app.get("/api/sites/{site_id}")
def get_site(site_id: int):
    s = services.site(site_id)
    if not s:
        raise HTTPException(404, "Site not found")
    return s


@app.post("/api/sites", status_code=201)
def create_site(body: SiteIn):
    return services.create_site(body.model_dump())


@app.post("/api/sites/{site_id}/notes", status_code=201)
def add_note(site_id: int, body: NoteIn):
    s = services.add_note(site_id, body.body, body.author, body.photos_added)
    if not s:
        raise HTTPException(404, "Site not found")
    return s


@app.get("/api/search")
def search(q: str = Query(min_length=1), category: str | None = None, limit: int = Query(10, ge=1, le=50)):
    return services.search(q, category, limit)


@app.get("/api/geojson")
def geojson():
    return services.geojson()


@app.get("/api/nearby")
def nearby(lat: float, lon: float, radius_km: float = Query(300, gt=0, le=3000)):
    return services.nearby(lat, lon, radius_km)


@app.get("/api/journey")
def journey(start_id: int | None = None):
    return services.journey(start_id)


@app.get("/api/stats")
def stats():
    return services.stats()


@app.post("/api/ocr")
async def ocr_upload(file: UploadFile = File(...), site_id: int | None = Form(None)):
    data = await file.read()
    if len(data) > config.MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(413, "File too large")
    if not (file.content_type or "").startswith("image/"):
        raise HTTPException(415, "Upload an image (png/jpg/tiff)")
    try:
        return services.digitise(data, file.filename or "upload", site_id)
    except ValueError as e:
        raise HTTPException(422, str(e))


if config.FRONTEND_DIR.exists():   # serve the web app from the same origin: http://localhost:8000/
    app.mount("/", StaticFiles(directory=config.FRONTEND_DIR, html=True), name="frontend")
