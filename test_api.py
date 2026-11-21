"""HTTP-level smoke tests. Needs: pip install -r requirements.txt   Run: python -m unittest discover -s tests -v"""
import os, sys, tempfile, unittest

_tmp = tempfile.TemporaryDirectory()
os.environ["VIRASAT_DB"] = os.path.join(_tmp.name, "api.db")
os.environ["VIRASAT_UPLOADS"] = os.path.join(_tmp.name, "up")
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

try:
    from fastapi.testclient import TestClient
    from app.main import app
except Exception:  # FastAPI not installed -> skip
    app = None


@unittest.skipIf(app is None, "fastapi/httpx not installed")
class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cm = TestClient(app); cls.c = cls.cm.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.cm.__exit__(None, None, None)

    def test_health(self):
        self.assertEqual(self.c.get("/api/health").json(), {"status": "ok"})

    def test_sites_and_detail(self):
        self.assertGreaterEqual(len(self.c.get("/api/sites").json()), 14)
        self.assertEqual(self.c.get("/api/sites/13").json()["title"], "Mysore Palace")
        self.assertEqual(self.c.get("/api/sites/9999").status_code, 404)

    def test_search(self):
        r = self.c.get("/api/search", params={"q": "ancient water architecture"}).json()
        self.assertEqual(r[0]["category"], "Stepwell")

    def test_create_validation(self):
        bad = self.c.post("/api/sites", json={"title": "x", "lat": 99, "lon": 72, "category": "Stepwell"})
        self.assertEqual(bad.status_code, 422)
        ok = self.c.post("/api/sites", json={"title": "Dada Harir Vav", "lat": 23.07, "lon": 72.68, "category": "Stepwell"})
        self.assertEqual(ok.status_code, 201)

    def test_note(self):
        r = self.c.post("/api/sites/1/notes", json={"body": "Carvings still crisp on level five", "photos_added": 3})
        self.assertEqual(r.status_code, 201)

    def test_geo_endpoints(self):
        self.assertEqual(self.c.get("/api/geojson").json()["type"], "FeatureCollection")
        self.assertGreater(self.c.get("/api/journey").json()["total_km"], 1000)
        self.assertTrue(self.c.get("/api/nearby", params={"lat": 23.85, "lon": 72.1, "radius_km": 50}).json())

    def test_ocr_rejects_non_image(self):
        r = self.c.post("/api/ocr", files={"file": ("a.txt", b"hello", "text/plain")})
        self.assertEqual(r.status_code, 415)


if __name__ == "__main__":
    unittest.main()
