CREATE TABLE magic_castles(
    hostname TEXT PRIMARY KEY NOT NULL,
    status TEXT NOT NULL,
    plan_type TEXT NOT NULL,
    owner TEXT,
    created TIMESTAMP NOT NULL DEFAULT (datetime('now', 'localtime')),
    expiration_date TEXT
)