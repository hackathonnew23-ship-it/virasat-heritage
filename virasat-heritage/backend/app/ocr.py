"""OCR pipeline for scanned field-journal pages and inscriptions.

OpenCV clean-up -> Tesseract (Indic language packs) -> script detection -> entity extraction.
Translation is a pluggable hook (`translate`); the transformer OCR/translation models named in the
roadmap (TrOCR / IndicTrans2) slot in behind the same `run_ocr` interface.
"""
import re

import cv2
import numpy as np
import pytesseract

from . import config

SCRIPTS = {  # name -> (unicode range, language label)
    "Devanagari": ((0x0900, 0x097F), "Hindi/Sanskrit"),
    "Gujarati": ((0x0A80, 0x0AFF), "Gujarati"),
    "Odia": ((0x0B00, 0x0B7F), "Odia"),
    "Kannada": ((0x0C80, 0x0CFF), "Kannada"),
}
_DIGITS = str.maketrans("०१२३४५६७८९૦૧૨૩૪૫૬૭૮૯೦೧೨೩೪೫೬೭೮೯୦୧୨୩୪୫୬୭୮୯", "0123456789" * 4)


def available_langs():
    want = config.OCR_LANGS.split("+")
    try:
        have = set(pytesseract.get_languages(config=""))
    except Exception:
        have = {"eng"}
    use = [w for w in want if w in have] or ["eng"]
    return "+".join(use)


def preprocess(data: bytes):
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image")
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    if max(g.shape) < 1200:                      # upscale small scans: Tesseract likes ~300 dpi
        g = cv2.resize(g, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    g = cv2.fastNlMeansDenoising(g, None, 12, 7, 21)
    return cv2.adaptiveThreshold(g, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15)


def detect_script(text):
    counts = {name: 0 for name in SCRIPTS}
    latin = 0
    for ch in text:
        o = ord(ch)
        for name, ((lo, hi), _) in SCRIPTS.items():
            if lo <= o <= hi:
                counts[name] += 1
        if ch.isascii() and ch.isalpha():
            latin += 1
    best = max(counts, key=counts.get)
    if counts[best] > latin and counts[best] > 0:
        return best, SCRIPTS[best][1]
    return "Latin", "English"


DATE_PATTERNS = [
    (re.compile(r"(?:V\.?\s?S\.?|Samvat|संवत्?|सं\.?|સંવત)\s*(\d{3,4})", re.I), "samvat"),
    (re.compile(r"\b(\d{3,4})\s*(?:CE|C\.E\.|AD|A\.D\.|ई\.|ઈ\.સ\.)", re.I), "ce"),
    (re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)\s+c(?:entury|\.)", re.I), "century"),
]


def extract_entities(text, gazetteer=()):
    norm = text.translate(_DIGITS)
    ents = []
    for rx, kind in DATE_PATTERNS:
        for m in rx.finditer(norm):
            v = int(m.group(1))
            label = {"samvat": f"V.S. {v} (~{v - 57} CE)", "ce": f"{v} CE", "century": f"{v}th century CE"}[kind]
            ents.append({"type": "Date", "value": label})
    for name in gazetteer:
        if name and name.lower() in norm.lower():
            ents.append({"type": "Place", "value": name})
    for m in re.finditer(r"\b(\d[\d,]*)\s+(steps|wheels|shrines|pillars|levels|storeys|bastions)\b", norm, re.I):
        ents.append({"type": "Feature", "value": f"{m.group(1)} {m.group(2).lower()}"})
    seen, out = set(), []
    for e in ents:
        k = (e["type"], e["value"])
        if k not in seen:
            seen.add(k); out.append(e)
    return out


def translate(text, src_language):
    """Hook for IndicTrans2 / a translation API. Returns None until a provider is configured."""
    return None


def run_ocr(data: bytes, gazetteer=()):
    lang = available_langs()
    img = preprocess(data)
    d = pytesseract.image_to_data(img, lang=lang, config="--psm 6", output_type=pytesseract.Output.DICT)
    words = [(w, float(c)) for w, c in zip(d["text"], d["conf"]) if w.strip() and float(c) >= 0]
    text = pytesseract.image_to_string(img, lang=lang, config="--psm 6").strip()
    script, language = detect_script(text)
    conf = round(sum(c for _, c in words) / len(words), 1) if words else 0.0
    return {"text": text, "script": script, "language": language, "confidence": conf,
            "engine": f"tesseract[{lang}]", "translation": translate(text, language),
            "entities": extract_entities(text, gazetteer)}
