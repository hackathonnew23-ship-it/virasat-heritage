#!/usr/bin/env bash
# Usage: ./push_to_github.sh https://github.com/<you>/<repo>.git
# Records the project as a series of logical commits, then pushes.
# (Commit timestamps are the moment you run it - never back-dated.)
set -e
URL="${1:?Pass your empty GitHub repo URL}"
git init -b main
git add .gitignore LICENSE NOTICE && git commit -m "chore: add license, notice and gitignore"
git add db/schema.sql && git commit -m "feat(db): PostgreSQL + PostGIS + pgvector production schema"
git add backend/requirements.txt backend/app/__init__.py backend/app/config.py backend/app/seed_data.py backend/app/db.py \
  && git commit -m "feat(backend): config, SQLite data layer and seed heritage records"
git add backend/app/search.py && git commit -m "feat(search): hybrid TF-IDF + char n-gram search with Indic-script support"
git add backend/app/ocr.py && git commit -m "feat(ocr): OpenCV + Tesseract pipeline, script detection, entity extraction"
git add backend/app/geo.py backend/app/services.py && git commit -m "feat(geo): GeoJSON, radius search, explorer journey; service layer"
git add backend/app/main.py && git commit -m "feat(api): FastAPI routes for sites, notes, search, OCR, geo"
git add backend/tests && git commit -m "test: service-layer and HTTP tests"
git add frontend && git commit -m "feat(frontend): interactive map, 3D twins, OCR, contribute; API bridge"
git add backend/Dockerfile docker-compose.yml .env.example .github && git commit -m "ci: Docker, compose and GitHub Actions test workflow"
git add README.md && git commit -m "docs: README with architecture diagrams and setup"
git add -A && (git diff --cached --quiet || git commit -m "chore: remaining files")
git remote add origin "$URL"
git push -u origin main
