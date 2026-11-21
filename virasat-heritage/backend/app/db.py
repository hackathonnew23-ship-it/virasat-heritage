"""Data layer. SQLite for zero-setup development; db/schema.sql is the PostgreSQL + pgvector + PostGIS
production schema that mirrors these tables."""
import json
import sqlite3
from contextlib import contextmanager

from . import config
from .seed_data import SITES

SCHEMA = """
CREATE TABLE IF NOT EXISTS sites (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL, place TEXT, state TEXT,
  lat REAL NOT NULL, lon REAL NOT NULL,
  category TEXT NOT NULL, photo_count INTEGER DEFAULT 0,
  native_name TEXT DEFAULT '', model_type TEXT DEFAULT 'stepwell',
  style TEXT DEFAULT '', built TEXT DEFAULT '', material TEXT DEFAULT '', highlight TEXT DEFAULT '',
  description TEXT DEFAULT '',
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS notes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  site_id INTEGER NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
  author TEXT DEFAULT 'explorer', body TEXT NOT NULL, photos_added INTEGER DEFAULT 0,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS documents (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  site_id INTEGER REFERENCES sites(id) ON DELETE SET NULL,
  filename TEXT, script TEXT, language TEXT, confidence REAL,
  text TEXT, translation TEXT, entities TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_sites_category ON sites(category);
CREATE INDEX IF NOT EXISTS idx_notes_site ON notes(site_id);
"""

COLS = ["title", "place", "state", "lat", "lon", "category", "photo_count", "native_name",
        "model_type", "style", "built", "material", "highlight", "description"]
DEFAULTS = {"place": "", "state": "", "photo_count": 0, "native_name": "", "model_type": "stepwell",
            "style": "", "built": "", "material": "", "highlight": "", "description": ""}


@contextmanager
def conn(path=None):
    c = sqlite3.connect(path or config.DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    try:
        yield c
        c.commit()
    finally:
        c.close()


def init(path=None, seed=True):
    with conn(path) as c:
        c.executescript(SCHEMA)
        if seed and c.execute("SELECT COUNT(*) FROM sites").fetchone()[0] == 0:
            c.executemany(f"INSERT INTO sites ({','.join(COLS)}) VALUES ({','.join('?' * len(COLS))})", SITES)


def list_sites(path=None):
    with conn(path) as c:
        return [dict(r) for r in c.execute("SELECT * FROM sites ORDER BY id")]


def get_site(site_id, path=None):
    with conn(path) as c:
        r = c.execute("SELECT * FROM sites WHERE id=?", (site_id,)).fetchone()
        if not r:
            return None
        d = dict(r)
        d["notes"] = [dict(n) for n in c.execute("SELECT * FROM notes WHERE site_id=? ORDER BY id", (site_id,))]
        d["documents"] = [dict(n) for n in c.execute("SELECT * FROM documents WHERE site_id=? ORDER BY id", (site_id,))]
        return d


def add_site(data, path=None):
    row = {k: data.get(k) for k in COLS}
    for k, default in DEFAULTS.items():
        if row[k] is None:
            row[k] = default
    with conn(path) as c:
        cur = c.execute(f"INSERT INTO sites ({','.join(COLS)}) VALUES ({','.join('?' * len(COLS))})",
                        [row[k] for k in COLS])
        return cur.lastrowid


def add_note(site_id, body, author="explorer", photos=0, path=None):
    with conn(path) as c:
        if not c.execute("SELECT 1 FROM sites WHERE id=?", (site_id,)).fetchone():
            return None
        cur = c.execute("INSERT INTO notes (site_id, author, body, photos_added) VALUES (?,?,?,?)",
                        (site_id, author, body, photos))
        c.execute("UPDATE sites SET photo_count = photo_count + ? WHERE id=?", (photos, site_id))
        return cur.lastrowid


def add_document(site_id, filename, result, path=None):
    with conn(path) as c:
        cur = c.execute(
            "INSERT INTO documents (site_id, filename, script, language, confidence, text, translation, entities)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (site_id, filename, result["script"], result["language"], result["confidence"],
             result["text"], result.get("translation"), json.dumps(result["entities"], ensure_ascii=False)))
        return cur.lastrowid


def search_corpus(path=None):
    """One searchable text blob per site: record fields + field notes + OCR'd documents."""
    with conn(path) as c:
        out = []
        for r in c.execute("SELECT * FROM sites ORDER BY id"):
            notes = " ".join(n["body"] for n in c.execute("SELECT body FROM notes WHERE site_id=?", (r["id"],)))
            docs = " ".join((d["text"] or "") + " " + (d["translation"] or "")
                            for d in c.execute("SELECT text, translation FROM documents WHERE site_id=?", (r["id"],)))
            text = " ".join([r["title"], r["native_name"], r["place"] or "", r["state"] or "", r["category"],
                             r["style"], r["material"], r["highlight"], r["description"], notes, docs])
            out.append((r["id"], r["category"], text))
        return out
