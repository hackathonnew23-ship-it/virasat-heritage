"""Application services. The FastAPI layer is a thin wrapper over these functions, which keeps the
business logic framework-free and unit-testable."""
from . import db, geo, ocr
from .search import SearchIndex

_index = SearchIndex()


def startup(path=None):
    db.init(path)
    reindex(path)


def reindex(path=None):
    _index.build(db.search_corpus(path))


def sites(path=None):
    return db.list_sites(path)


def site(site_id, path=None):
    return db.get_site(site_id, path)


def search(q, category=None, k=10, path=None):
    by_id = {s["id"]: s for s in db.list_sites(path)}
    return [{**by_id[h["id"]], "score": h["score"]} for h in _index.query(q, k, category) if h["id"] in by_id]


def create_site(data, path=None):
    sid = db.add_site(data, path)
    reindex(path)
    return db.get_site(sid, path)


def add_note(site_id, body, author="explorer", photos=0, path=None):
    nid = db.add_note(site_id, body, author, photos, path)
    if nid is None:
        return None
    reindex(path)
    return db.get_site(site_id, path)


def digitise(image_bytes, filename="upload", site_id=None, path=None):
    gaz = [s["place"] for s in db.list_sites(path)] + [s["title"] for s in db.list_sites(path)]
    result = ocr.run_ocr(image_bytes, gaz)
    result["document_id"] = db.add_document(site_id, filename, result, path)
    reindex(path)
    return result


def geojson(path=None):
    return geo.to_geojson(db.list_sites(path))


def nearby(lat, lon, radius_km, path=None):
    return geo.nearby(db.list_sites(path), lat, lon, radius_km)


def journey(start_id=None, path=None):
    return geo.journey(db.list_sites(path), start_id)


def stats(path=None):
    s = db.list_sites(path)
    cats = {}
    for x in s:
        cats[x["category"]] = cats.get(x["category"], 0) + 1
    return {"sites": len(s), "photos": sum(x["photo_count"] for x in s), "categories": cats,
            "states": len({x["state"] for x in s if x["state"]})}
