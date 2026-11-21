"""Runtime configuration, read from environment variables (see .env.example)."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = os.getenv("VIRASAT_DB", str(BASE_DIR / "virasat.db"))
UPLOAD_DIR = Path(os.getenv("VIRASAT_UPLOADS", str(BASE_DIR / "uploads")))
FRONTEND_DIR = Path(os.getenv("VIRASAT_FRONTEND", str(BASE_DIR.parent / "frontend")))
# Languages we would like Tesseract to use; the ones actually installed are picked at runtime.
OCR_LANGS = os.getenv("VIRASAT_OCR_LANGS", "hin+guj+kan+ori+san+eng")
MAX_UPLOAD_MB = int(os.getenv("VIRASAT_MAX_UPLOAD_MB", "10"))
