-- Deploy busman:0001_init to pg

BEGIN;

CREATE TABLE module (
    id SERIAL PRIMARY KEY,
    mac macaddr NOT NULL,
    ip inet NOT NULL,
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    UNIQUE (name, version)
);
COMMIT;
