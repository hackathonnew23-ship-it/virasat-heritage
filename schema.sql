-- Virasat production schema: PostgreSQL 16 + PostGIS + pgvector + pg_trgm.
-- The running development build uses SQLite with the same logical tables (backend/app/db.py).
-- Tables marked [planned] back features described in the README roadmap (photo->3D jobs, contributors).

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TYPE site_category AS ENUM ('Stepwell', 'Temple', 'Fort', 'Craft', 'Folklore');

CREATE TABLE contributors (                 -- [planned] explorers / fellows who document sites
  id           BIGSERIAL PRIMARY KEY,
  name         TEXT NOT NULL,
  institution  TEXT,
  created_at   TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE sites (
  id           BIGSERIAL PRIMARY KEY,
  title        TEXT NOT NULL,
  native_name  TEXT DEFAULT '',
  place        TEXT, state TEXT,
  category     site_category NOT NULL,
  geom         geography(Point, 4326) NOT NULL,
  style        TEXT, built TEXT, material TEXT, highlight TEXT,
  model_type   TEXT DEFAULT 'stepwell',     -- which 3D template / reconstructed twin to load
  description  TEXT DEFAULT '',
  photo_count  INTEGER DEFAULT 0,
  embedding    vector(384),                  -- multilingual sentence embedding of the record text
  created_at   TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX sites_geom_gix   ON sites USING GIST (geom);
CREATE INDEX sites_trgm_idx   ON sites USING GIN ((title || ' ' || native_name || ' ' || description) gin_trgm_ops);
CREATE INDEX sites_embed_idx  ON sites USING hnsw (embedding vector_cosine_ops);
CREATE INDEX sites_category   ON sites (category);

CREATE TABLE notes (
  id            BIGSERIAL PRIMARY KEY,
  site_id       BIGINT NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
  contributor_id BIGINT REFERENCES contributors(id),
  body          TEXT NOT NULL,
  photos_added  INTEGER DEFAULT 0,
  embedding     vector(384),
  created_at    TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX notes_site ON notes (site_id);

CREATE TABLE documents (                    -- OCR'd scans: inscriptions, journals, regional-language text
  id           BIGSERIAL PRIMARY KEY,
  site_id      BIGINT REFERENCES sites(id) ON DELETE SET NULL,
  filename     TEXT, storage_url TEXT,
  script       TEXT, language TEXT, confidence REAL,
  text         TEXT, translation TEXT,
  entities     JSONB DEFAULT '[]',
  embedding    vector(384),
  created_at   TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX documents_site ON documents (site_id);
CREATE INDEX documents_entities ON documents USING GIN (entities);

CREATE TABLE photos (                       -- [planned] crowdsourced images that feed 3D reconstruction
  id           BIGSERIAL PRIMARY KEY,
  site_id      BIGINT NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
  contributor_id BIGINT REFERENCES contributors(id),
  storage_url  TEXT NOT NULL,
  exif         JSONB,
  taken_at     TIMESTAMPTZ,
  geom         geography(Point, 4326)
);
CREATE INDEX photos_site ON photos (site_id);

CREATE TABLE twin_jobs (                    -- [planned] async SfM/mesh jobs (COLMAP -> glTF)
  id           BIGSERIAL PRIMARY KEY,
  site_id      BIGINT NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
  status       TEXT NOT NULL DEFAULT 'queued',  -- queued | running | done | failed
  photo_count  INTEGER,
  gltf_url     TEXT,
  created_at   TIMESTAMPTZ DEFAULT now(),
  finished_at  TIMESTAMPTZ
);
