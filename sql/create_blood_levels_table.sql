-- Blood-reserve levels ("semáforo de necesidades") scraped from donarsangre.org.
-- Run this once by hand in Supabase before the ETL appends to it.
--
-- Unlike the other ETL tables, this one is append-only: every run inserts a
-- fresh snapshot (8 rows, one per blood type) so we keep a history of reserve
-- levels over time. The app reads only the most recent snapshot.

CREATE TABLE IF NOT EXISTS blood_levels (
    id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    region     text        NOT NULL,             -- Comunidad Autónoma, e.g. 'Comunidad de Madrid'
    blood_type text        NOT NULL,             -- '0-', '0+', 'A-', ... 'AB+'
    status     text        NOT NULL,             -- 'urgent' | 'soon' | 'stable'
    level      smallint    NOT NULL,             -- 1 = most urgent ... 3 = stable
    label      text,                             -- original Spanish phrase, e.g. 'Dona hoy'
    source     text        NOT NULL,             -- 'donarsangre.org'
    updated_at timestamptz NOT NULL              -- scrape time (one value per run)
);

-- Fast "latest snapshot per region" and per-type history lookups.
CREATE INDEX IF NOT EXISTS blood_levels_region_updated_at_idx
    ON blood_levels (region, updated_at DESC);
CREATE INDEX IF NOT EXISTS blood_levels_region_blood_type_updated_at_idx
    ON blood_levels (region, blood_type, updated_at DESC);

-- Latest snapshot for the app:
--   SELECT DISTINCT ON (region, blood_type)
--          region, blood_type, status, level, label, updated_at
--   FROM blood_levels
--   WHERE region = 'Comunidad de Madrid'
--   ORDER BY region, blood_type, updated_at DESC;
