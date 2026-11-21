"""Run from backend/:  python -m unittest discover -s tests -v"""
import io
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import geo, ocr, services  # noqa: E402


class CoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.TemporaryDirectory()
        cls.path = os.path.join(cls.dir.name, "t.db")
        services.startup(cls.path)

    @classmethod
    def tearDownClass(cls):
        cls.dir.cleanup()

    # --- database -------------------------------------------------------
    def test_seed_loaded(self):
        self.assertGreaterEqual(len(services.sites(self.path)), 14)  # tests share one DB; others may add rows

    def test_get_site_has_notes_and_docs(self):
        s = services.site(1, self.path)
        self.assertEqual(s["title"], "Rani ki Vav")
        self.assertIn("notes", s)
        self.assertIn("documents", s)

    # --- search ---------------------------------------------------------
    def test_semantic_water_query_returns_stepwells(self):
        hits = services.search("ancient water architecture", path=self.path)
        self.assertTrue(hits)
        self.assertEqual(hits[0]["category"], "Stepwell")

    def test_spelling_variant_baori(self):
        titles = [h["title"] for h in services.search("baori", path=self.path)]
        self.assertIn("Chand Baori", titles)

    def test_native_script_query(self):
        hits = services.search("वाव", path=self.path)
        self.assertEqual(hits[0]["title"], "Rani ki Vav")

    def test_gujarati_query(self):
        hits = services.search("અડાલજ", path=self.path)
        self.assertEqual(hits[0]["title"], "Adalaj Stepwell")

    def test_category_filter(self):
        hits = services.search("temple", category="Fort", path=self.path)
        self.assertTrue(all(h["category"] == "Fort" for h in hits))

    def test_empty_query(self):
        self.assertEqual(services.search("   ", path=self.path), [])

    # --- writes re-index search ----------------------------------------
    def test_note_is_searchable_and_adds_photos(self):
        before = services.site(2, self.path)["photo_count"]
        s = services.add_note(2, "Villagers narrate a legend of a hidden underground tunnel", photos=5, path=self.path)
        self.assertEqual(s["photo_count"], before + 5)
        hits = services.search("underground tunnel", path=self.path)
        self.assertEqual(hits[0]["id"], 2)

    def test_note_unknown_site(self):
        self.assertIsNone(services.add_note(999, "x", path=self.path))

    def test_create_site(self):
        s = services.create_site({"title": "Vav of Sarkhej", "lat": 22.98, "lon": 72.49, "category": "Stepwell",
                                  "description": "Sultanate-era tank complex"}, self.path)
        self.assertTrue(s["id"] > 14)
        self.assertEqual(services.search("Sarkhej", path=self.path)[0]["id"], s["id"])

    # --- geo -----------------------------------------------------------
    def test_haversine_delhi_mumbai(self):
        d = geo.haversine_km(28.61, 77.21, 19.07, 72.88)
        self.assertTrue(1100 < d < 1200)

    def test_geojson(self):
        g = services.geojson(self.path)
        self.assertEqual(g["type"], "FeatureCollection")
        self.assertEqual(g["features"][0]["geometry"]["type"], "Point")

    def test_nearby_patan(self):
        names = [s["title"] for s in services.nearby(23.85, 72.1, 60, self.path)]
        self.assertIn("Rani ki Vav", names)
        self.assertNotIn("Mysore Palace", names)

    def test_journey_visits_everything_once(self):
        j = services.journey(path=self.path)
        ids = [s["id"] for s in j["stops"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(ids), len(services.sites(self.path)))
        self.assertGreater(j["total_km"], 1000)

    # --- OCR -----------------------------------------------------------
    def test_entities_devanagari_digits(self):
        ents = ocr.extract_entities("सं. १०६३ में पाटण में बावली", ["पाटण"])
        vals = [e["value"] for e in ents]
        self.assertIn("V.S. 1063 (~1006 CE)", vals)
        self.assertIn("पाटण", vals)

    def test_entities_features(self):
        vals = [e["value"] for e in ocr.extract_entities("The well has 103 steps and 24 wheels")]
        self.assertIn("103 steps", vals)
        self.assertIn("24 wheels", vals)

    def test_script_detection(self):
        self.assertEqual(ocr.detect_script("રાણી કી વાવ")[0], "Gujarati")
        self.assertEqual(ocr.detect_script("रानी की वाव")[0], "Devanagari")
        self.assertEqual(ocr.detect_script("Rani ki Vav")[0], "Latin")

    def test_ocr_on_rendered_image(self):
        from PIL import Image, ImageDraw, ImageFont
        img = Image.new("RGB", (900, 220), "white")
        try:
            font = ImageFont.truetype("DejaVuSans.ttf", 44)
        except OSError:
            self.skipTest("DejaVuSans font not found")
        ImageDraw.Draw(img).text((20, 20), "Chand Baori Abhaneri", fill="black", font=font)
        ImageDraw.Draw(img).text((20, 100), "built in 800 CE with 3500 steps", fill="black", font=font)
        buf = io.BytesIO(); img.save(buf, "PNG")
        r = services.digitise(buf.getvalue(), "test.png", site_id=4, path=self.path)
        self.assertIn("Baori", r["text"])
        self.assertEqual(r["script"], "Latin")
        self.assertTrue(any(e["type"] == "Date" for e in r["entities"]))
        self.assertTrue(r["document_id"] > 0)
        self.assertEqual(services.search("Abhaneri", path=self.path)[0]["id"], 4)  # OCR'd text is searchable

    def test_ocr_rejects_garbage(self):
        with self.assertRaises(ValueError):
            ocr.preprocess(b"not an image")


if __name__ == "__main__":
    unittest.main()
